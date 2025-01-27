"""Useful operations for unit tests

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# defer importing pkconfig
from pykern import pkcompat
from pykern import pkconst
from pykern import pkinspect
from pykern import pkio
import contextlib
import importlib
import inspect
import json
import os
import py
import pykern.pkconst
import pykern.util
import pytest
import re
import subprocess
import sys
import traceback

#: Environment var set by pykern.pkcli.test for each module under test
TEST_FILE_ENV = "PYKERN_PKUNIT_TEST_FILE"

#: Environment var set by pykern.pkcli.test if the test is restartable
RESTARTABLE = "PYKERN_PKUNIT_RESTARTABLE"

#: Where persistent input files are stored (test_base_name_data)
DATA_DIR_SUFFIX = "_data"

#: Used to create test servers
LOCALHOST_IP = pkconst.LOCALHOST_IP

#: Where to write temporary files (test_base_name_work)
WORK_DIR_SUFFIX = "_work"

#: Where `ExceptToFile` writes exception
PKEXCEPT_PATH = "pkexcept"

#: Where `ExceptToFile` writes stack
PKSTACK_PATH = "pkstack"

#: INTERNAL: Set to the most recent test module by `_test_file`
module_under_test = None

#: Type of a regular expression
_RE_TYPE = type(re.compile(""))

#: used by case_dirs for comparing sheets
_CSV_SHEET_ID = re.compile(r"(.+)#(\d)$")

#: _test_file initialized?
_init_test_file = False

#: module being run by `pykern.pkcli.test`
__test_file = None


class PKFail(AssertionError):
    pass


class ExceptToFile:
    """Writes exception or None to `PKEXCEPT_PATH`

    Used for deviance testing with `case_dirs`.

    If there is an exception, writes that to the file. Otherwise, writes "None"

    If there is an exception, will write `PKSTACK_PATH`. Otherwise, no
    file exists. Used for diagnostics only.

    Usage::
        for d in case_dirs():
            with ExceptToFile():
                command to test

    Returns:
        None: just for context manager
    """

    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            r = str(None)
        else:
            r = re.sub(
                pkio.py_path().dirname + r"\S*/", "", str(exc_val), flags=re.IGNORECASE
            )
            with open(PKSTACK_PATH, "wt") as f:
                traceback.print_exception(exc_type, exc_val, exc_tb, file=f)
        pkio.write_text(PKEXCEPT_PATH, r + "\n")
        return True


def assert_object_with_json(
    basename,
    actual,
):
    """Converts actual to JSON and compares with data_dir/basename.json

    Reads data_dir/basename.json and compares with actual
    converted to json. Trailing newline is managed properly. The
    keys are sorted and indentation is 4. actual written to work_dir.

    Args:
        expected_basename (str): file to be found in data_dir with json suffix
        actual (object): to be serialized as json
    """
    from pykern.pkdebug import pkdpretty

    actual = pkdpretty(actual)
    fn = "{}.json".format(basename)
    a = work_dir().join(fn)
    pkio.write_text(a, actual)
    e = data_dir().join(fn)
    expect = pkio.read_text(e)
    pkeq(expect, actual, "diff {} {}", e, a)


def case_dirs(group_prefix="", **kwargs):
    """Sets up `work_dir` by iterating ``*.in`` in `data_dir`

    Every ``<case-name>.in`` is copied recursively to ``<case-name>`` in
    `work_dir`. This function then yields that directory. The test can
    then run the function to be tested.

    When test yields to the generator, this function looks for all
    files in `data_dir` in the sub-directory ``<case-name>.out``. Each
    of these expect files is copmared to the corresponding `work_dir`
    actual file using `file_eq`.

    If you want to only use cases from some specific `<case-name>.in`
    subdir, and not all `*.in` subdirs, you can pass a `group_prefix`
    default parameter value ('' by default) to `case_dirs()`. This will
    perform the regular operations but only on `<case-name>.in`.

    Excel spreadsheets are supported. If you want to automatically
    compare xlsx files, you need to install ``pandas``, which will be
    used to convert Excel files as follows. If the name of the expect
    (out) file is ``foo.csv``, then the first sheet (sheet 0) in the
    corresponding work_dir xlsx will be converted to ``foo.csv``
    before comparison.  If the expect (out) file has a ``#<digit>``,
    e.g. ``foo#3.csv``, then the fourth sheet will be extracted from
    the actual xlsx to ``foo#3.csv`` in the work_dir.

    If ExceptToFile in the body of a case_dirs loop, the exception
    will be output if a file is not found.

    Args:
        group_prefix (string): target subdir ['']
        j2_ctx (dict): passed to `pykern.pkjinja.render_file`
        ignore_lines (iterable): `POSIX standard regular expressions <https://www.gnu.org/software/findutils/manual/html_node/find_html/posix_002dbasic-regular-expression-syntax.html>`_ to be passed to `diff`
        is_bytes (bool): do a binary comparison [False]

    Returns:
        py.path.local: case directory created in work_dir (also PWD)

    """
    import shutil

    def _compare(in_d, work_d):
        o = in_d.new(ext="out")
        for e in pkio.walk_tree(o):
            if e.basename.endswith("~"):
                continue
            a = work_d.join(o.bestrelpath(e))
            file_eq(
                expect_path=e,
                actual_path=a,
                **kwargs,
            )

    d = work_dir()
    n = 0
    for i in pkio.sorted_glob(data_dir().join(group_prefix + "*.in")):
        w = d.join(i.purebasename)
        shutil.copytree(str(i), str(w))
        n += 1
        with pkio.save_chdir(w):
            _pkdlog("case_dir={}", i.basename)
            yield w
        try:
            _compare(i, w)
            continue
        except Exception as e:
            # Not found indicates expected output not found.
            # It might have been caused by an exception which was
            # caught by ExceptToFile.
            if not pkio.exception_is_not_found(e):
                raise
            f = w.join(PKSTACK_PATH)
            if not f.exists():
                raise
            _pkdlog("Exception in case_dir={}\n{}", w, f.read())
        # This avoids confusing "during handling of above exception"
        pkfail("See stack above")
    if n == 0:
        pkfail(f"No files found for group_prefix={group_prefix}")


def data_dir():
    """Compute the data directory based on the test name

    The test data directory is always ``<test>_data``, where ``<test>``
    is the name of the test's python module with the ``_test`` or
    ``test_`` removed.  For example, if the test file is
    ``setup_test.py`` then the directory will be ``setup_data``.

    Returns:
        py.path.local: data directory

    """
    return _base_dir(DATA_DIR_SUFFIX)


def data_yaml(base_name):
    """Load base_name.yml from data_dir

    Args:
        base_name (str): name of YAML file with ``.yml`` extension

    Returns:
        object: YAML data structure, usually dict or array
    """
    from pykern import pkyaml

    return pkyaml.load_file(data_dir().join(base_name) + ".yml")


def empty_work_dir():
    """Remove `work_dir` if it exists and create.

    All contents of the test directory will be removed.

    Returns:
        py.path.local: empty work directory

    """
    d = work_dir()
    if os.path.exists(str(d)):
        # doesn't ignore "not found" errors
        d.remove(rec=1, ignore_errors=True)
    return d.ensure(dir=True)


def file_eq(expect_path, *args, **kwargs):
    """If actual is not expect_path, throw assertion with calling context.

    `expect_path` and `actual_path` both exist, they will be compared as plain text.

    If `actual_path` does not exist, it will be created from `actual`.

    If `expect_path` ends in ``.json`` and `actual_path` does not exist,
    `pkjson` will be used to load `expect_path` and a data structure comparison
    will be used with `actual` (and `actual_path` will be written.
    This allows easy testing of complex results.

    If `expect_path` ends with ``.jinja``, it will be rendered
    with `pykern.pkjina.render_file`, and you must supply `j2_ctx`
    in kwargs.

    Args:
        expect_path (str or py.path): text file to be read; if str, then joined with `data_dir`
        actual (object): string or json data structure; if missing, read `actual_path` (may be positional)
        actual_path (py.path or str): where to write results; if str, then joined with `work_dir`; if None, ``work_dir().join(expect_path.relto(data_dir()))``
        j2_ctx (dict): passed to `pykern.pkjinja.render_file`
        ignore_lines (iterable): `POSIX standard regular expressions <https://www.gnu.org/software/findutils/manual/html_node/find_html/posix_002dbasic-regular-expression-syntax.html>`_ to be passed to `diff`
        is_bytes (bool): do a binary comparison [False]
    """
    _FileEq(expect_path, *args, **kwargs)


def is_test_run():
    """Running in a test?

    Returns:
        bool: whether this is running in a test
    """
    return bool(_test_file())


def import_module_from_data_dir(module_name):
    """Add `data_dir` to sys.path and import module_name.

    Note that `module_name` with be removed from the sys.modules cache
    before loading in case the module was loaded by another test.

    Args:
        module_name (str): module relative to `data_dir` to import.

    Returns:
        module: imported module
    """
    d = str(data_dir())
    prev_path = sys.path
    try:
        sys.path = [d]
        try:
            del sys.modules[module_name]
        except KeyError:
            pass
        m = importlib.import_module(module_name)
        return m
    finally:
        sys.path = prev_path


def pkeq(expect, actual, *args, **kwargs):
    """If actual is not expect, throw assertion with calling context.

    Opposite of `pkne`.

    Args:
        expect (object): what to test for
        actual (object): run-time value
        args (tuple): passed to pkfail()
        kwargs (dict): passed to pkfail()
    """
    if expect != actual:
        _fail(("expect={} != actual={}", expect, actual), *args, **kwargs)


@contextlib.contextmanager
def pkexcept(exc_or_re, *args, **kwargs):
    """Expect an exception to be thrown and match or output msg

    Examples::

        # Expect an exception (or its subclass)
        with pkexcept(AssertionError, 'did not expect this'):
            assert 0

        # Expect exception to contain a specific message
        with pkexcept('match this', 'problem with matching'):
            assert 0, 'some string with "match this" in it'

        # Use a default output message
        with pkexcept(KeyError):
            something['key will not be found']

    Args:
        exc_or_re (object): BaseException, re, or str; if str, compiled with `re.IGNORECASE`
        args (tuple): passed to format
        kwargs (dict): passed to format

    Yields:
        None: just for context manager
    """
    try:
        yield None
    except BaseException as e:
        from pykern.pkdebug import pkdexc

        e_str = "{} {}".format(type(e), e)
        if isinstance(exc_or_re, type) and issubclass(exc_or_re, BaseException):
            if isinstance(e, exc_or_re):
                return
            m = (
                "{}: an exception was raised, but expected it to be {}; stack={}",
                e_str,
                exc_or_re,
                pkdexc(),
            )
        else:
            if not isinstance(exc_or_re, _RE_TYPE):
                exc_or_re = re.compile(exc_or_re, flags=re.IGNORECASE)
            if exc_or_re.search(e_str):
                return
            m = (
                '{}: an exception was raised, but did not match "{}"; stack={}',
                e_str,
                exc_or_re.pattern,
                pkdexc(),
            )
    else:
        m = ("Exception was not raised: expecting={}", exc_or_re)
    _fail(m, *args, **kwargs)


def pkfail(fmt, *args, **kwargs):
    """Format message and raise PKFail.

    Args:
        fmt (str): to be passed to `string.format`
        args (tuple): passed to format
        kwargs (dict): passed to format
    """
    msg = fmt.format(*args, **kwargs)
    call = pkinspect.caller(ignore_modules=[contextlib])
    raise PKFail("{} {}".format(call, msg))


def pkne(expect, actual, *args, **kwargs):
    """If actual is equal to expect, throw assertion with calling context

    Opposite of `pkeq`.

    Args:
        expect (object): what to test for
        actual (object): run-time value
        args (tuple): passed to pkfail()
        kwargs (dict): passed to pkfail()
    """
    if expect == actual:
        _fail(("expect={} == actual={}", expect, actual), *args, **kwargs)


def pkok(cond, fmt, *args, **kwargs):
    """If cond is not true, throw PKFail with calling context

    Args:
        cond (object): expression which should evaluate to true
        fmt (str): to be passed to `string.format`
        args (tuple): passed to format
        kwargs (dict): passed to format

    Returns:
        object: `obj` value
    """
    if not cond:
        pkfail(fmt, *args, **kwargs)
    return cond


def pkre(expect_re, actual, flags=re.IGNORECASE + re.DOTALL):
    """If actual does not match (re.search) expect_re, throw PKFail with calling context.

    Args:
        expect_re (object): string or re object
        actual (object): run-time value
        flags: passed on to re.search [IGNORECASE + DOTALL]
    """
    if not re.search(expect_re, pkcompat.from_bytes(actual), flags=flags):
        pkfail("expect_re={} != actual={}", expect_re, actual)


def restart_or_fail(*args, **kwargs):
    """Test will be restarted (at process level) if it can, else `pkfail`

    Called by tests which experience known CI failures such
    as not being able to connect to servers.

    Communicates with pykern.pkcli.test

    Args:
        fmt (str): to be passed to `string.format`
        args (tuple): passed to format
        kwargs (dict): passed to format
    """
    if os.environ.get(RESTARTABLE):
        raise KeyboardInterrupt()
    pkfail(*args, **kwargs)


def save_chdir_work(is_pkunit_prefix=False, want_empty=True):
    """Change to `work_dir` which will be created.

    Default to `empty_work_dir` before chdir.

    Args:
        is_pkunit_prefix (bool): use as root of (most) file I/O (optional)
        want_empty (bool): call `empty_work_dir` before chdir if True [True]

    Returns:
        py.path.local: empty work directory

    """
    return pkio.save_chdir(
        empty_work_dir() if want_empty else work_dir(),
        is_pkunit_prefix=is_pkunit_prefix,
    )


#: DEPRECATED
unbound_localhost_tcp_port = pykern.util.unbound_localhost_tcp_port


def work_dir():
    """Returns ephemeral work directory, created if necessary.

    To enable easier debugging, the test directory is always
    ``<test>_work``, where ``<test>`` is the name of the test's python
    module with the ``_test`` or ``test_`` removed.  For example, if the
    test file is ``setup_test.py`` then the directory will be
    ``setup_work``.

    The name "work" distinguishes from "tmp", which could imply
    anything. Also, with editor autocomplete, "setup_work" and
    "setup_test" are more easily distinguishable.

    Returns:
        py.path: directory name
    """
    return _base_dir(WORK_DIR_SUFFIX).ensure(dir=True)


class _FileEq:
    """Implements `file_eq`"""

    def __init__(self, expect_path, *args, **kwargs):
        self._validate_args(expect_path, *args, **kwargs)
        self._set_expect_and_actual()
        self._compare()

    def _actual_xlsx(self):
        try:
            b = self._actual_path.new(ext=".xlsx")
            m = _CSV_SHEET_ID.search(b.purebasename)
            s = 0
            if m:
                b = b.new(purebasename=m.group(1))
                s = int(m.group(2))
            if b.check(file=True):
                self._actual_xlsx_to_csv(b, s)

                return True
            return False
        except Exception:
            _pkdlog(
                "ERROR converting xlsx to csv expect={} actual={}",
                self._expect_path,
                self._actual_path,
            )
            raise

    def _actual_xlsx_to_csv(self, actual_xlsx, sheet):
        import pandas

        p = pandas.read_excel(
            actual_xlsx,
            index_col=None,
            sheet_name=sheet,
        )
        p.columns = p.columns.map(lambda c: "" if "Unnamed" in str(c) else str(c))
        p.to_csv(
            str(self._actual_path),
            encoding="utf-8",
            index=False,
            lineterminator="\r\n",
        )

    def _compare(self):
        w = work_dir()

        def _cmd():
            if self.is_bytes:
                r = ["cmp"]
            else:
                r = ["diff"]
                for l in self._ignore_lines or ():
                    r.extend(("-I", l))
            return r + [str(self._expect_path), str(self._actual_path)]

        def _failed_msg(process):
            r = "'" + "' '".join(process.args) + f"'\n" + process.stdout + "\n"
            if not (process.returncode == 1 or self.is_bytes):
                return r + "diff command failed\n"
            if self._expect_is_jinja:
                return (
                    r
                    + f"""
Implementation restriction: expect is a jinja template which has been processed to
produce the diff. A simple copy of actual to expect is not possible. You will need to update
the expect jinja template={self._expect_path} manually.
"""
                )
            return r + self._update_message

        def _ndiff_config(work_d):
            return pykern.pkio.write_text(
                work_d.join("ndiff_conf.txt"),
                f"* * {'abs' if self._ndiff_epsilon_is_abs else 'rel'}={float(self._ndiff_epsilon)}",
            )

        def _ndiff_files(expect_path, actual_path):
            p = subprocess.run(
                (
                    "ndiff",
                    actual_path,
                    expect_path,
                    _ndiff_config(w),
                ),
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            d = pkcompat.from_bytes(p.stderr)
            if not re.search(r"processing '.*'\n\s*\d+ lines have been diffed\s*$", d):
                pkfail("diffs detected: {} {}", d, self._update_message)

        if self._is_ndiff:
            _ndiff_files(
                self._expect_path,
                self._actual_path,
            )
            return
        if self._expect == self._actual:
            return
        p = subprocess.run(
            _cmd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        if p.returncode != 0:
            pkfail("expect != actual:\n{}", _failed_msg(p))

    def _expect_csv(self):
        if not self._expect_path.ext == ".csv":
            return False
        self._actual_xlsx()
        self._actual = pkio.read_text(self._actual_path)
        self._expect = pkio.read_text(self._expect_path)
        return True

    def _expect_default(self):
        self._expect = self._read(self._expect_path)
        if self._have_actual_kwarg:
            self._write(self._actual_path, self._actual)

    def _expect_jinja(self):
        if not self._expect_is_jinja:
            return False
        import pykern.pkjinja

        self._expect = pykern.pkjinja.render_file(
            self._expect_path, self.j2_ctx, strict_undefined=True
        )
        if self._have_actual_kwarg:
            pkio.write_text(self._actual_path, self._actual)
        return True

    def _expect_json(self):
        if not self._expect_path.ext == ".json" or self._actual_path.exists():
            return False
        self._expect = pkio.read_text(self._expect_path)
        if self._have_actual_kwarg:
            import pykern.pkjson

            pkio.mkdir_parent_only(self._actual_path)
            self._actual = pykern.pkjson.dump_pretty(
                self._actual, filename=self._actual_path
            )
        return True

    def _set_expect_and_actual(self):
        self._read, self._write = (
            (pkio.read_binary, pkio.write_binary)
            if self.is_bytes
            else (pkio.read_text, pkio.write_text)
        )
        self._update_message = f"""
to update test data:
        cp '{self._actual_path}' '{self._expect_path}'
"""
        if self._expect_csv():
            assert not self.is_bytes, "csv is not compatible with is_bytes"
            return
        if self._have_actual_kwarg:
            self._actual = self.kwargs["actual"]
            if self._actual_path.exists():
                pkfail(
                    "actual={} and actual_path={} both exist",
                    self._actual,
                    self._actual_path,
                )
        else:
            self._actual = self._read(self._actual_path)
        if self._expect_json() or self._expect_jinja():
            assert not self.is_bytes, "json or jinja is not compatible with is_bytes"
            return
        self._expect_default()

    def _validate_args(self, expect_path, *args, **kwargs):
        from pykern.pkcollections import PKDict

        self.kwargs = kwargs
        self._have_actual_kwarg = "actual" in self.kwargs
        if args:
            assert (
                not self._have_actual_kwarg
            ), f'have actual as positional arg={args[0]} and kwargs={self.kwargs["actual"]}'
            assert (
                len(args) == 1
            ), f"too many positional args={args}, may only have one (actual)"
            self.kwargs["actual"] = args[0]
            self._have_actual_kwarg = True
        self._actual_path = kwargs.get("actual_path")
        self._expect_path = expect_path
        if not isinstance(self._expect_path, pykern.pkconst.PY_PATH_LOCAL_TYPE):
            self._expect_path = data_dir().join(self._expect_path)
        self._expect_is_jinja = self._expect_path.ext == ".jinja"
        self._is_ndiff = self._expect_path.ext == ".ndiff"
        self._ndiff_epsilon = kwargs.get("ndiff_epsilon", 1e-13)
        self._ndiff_epsilon_is_abs = kwargs.get("ndiff_epsilon_is_abs", False)
        b = (
            self._expect_path.purebasename
            if self._expect_is_jinja
            else self._expect_path.relto(data_dir())
        )
        if self._actual_path is None:
            self._actual_path = b
        if not isinstance(self._actual_path, pykern.pkconst.PY_PATH_LOCAL_TYPE):
            self._actual_path = work_dir().join(self._actual_path)
        self._ignore_lines = kwargs.get("ignore_lines")
        self.j2_ctx = kwargs.get("j2_ctx", PKDict())
        self.is_bytes = kwargs.get("is_bytes", False)


def _base_dir(postfix):
    """Base name with directory.

    Args:
        postfix (str): what to append to base (``_data`` or ``_work``).

    Returns:
        py.path.local: base directory with postfix
    """
    f = _test_file()
    if not f:
        raise PKFail("unable to find test file path; not running in pykern.pkcli.test?")
    b = re.sub(r"_test$|^test_", "", f.purebasename)
    assert b != f.purebasename, "{}: module name must end in _test".format(f)
    return f.new(basename=b + postfix).realpath()


def _fail(std_message_args, *args, **kwargs):
    """Augment standard failure messages with args and kwargs

    Args:
        std_message_args (tuple): fmt string and args. eg. ("expect={} != actual={}", expect, actual)
    """
    if args:
        pkfail(
            f"{std_message_args[0]} {args[0]}",
            *std_message_args[1:],
            *args[1:],
            **kwargs,
        )
    pkfail(*std_message_args)


def _pkdlog(*args, **kwargs):
    from pykern.pkdebug import pkdlog

    pkdlog(*args, **kwargs)


def _test_file():
    """Various ways to initialize _test_file"""
    global _init_test_file, __test_file

    if not _init_test_file:
        _init_test_file = True
        # pykern.pkcli.test
        t = os.environ.get(TEST_FILE_ENV)
        if t:
            __test_file = py.path.local(t)
    if __test_file:
        return __test_file
    if module_under_test:
        # POSIT: pykern.pytest_plugin or sirepo/tests/conftest.py
        m = module_under_test
        return py.path.local(m.__file__)
    # py.test alone, just guess
    s = inspect.currentframe().f_back.f_back
    f = None
    for _ in range(100):
        if s.f_code.co_filename.endswith("_test.py"):
            return py.path.local(s.f_code.co_filename)
        s = s.f_back
        if not s:
            break
    return None
