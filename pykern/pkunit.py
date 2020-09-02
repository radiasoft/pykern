# -*- coding: utf-8 -*-
u"""Useful operations for unit tests

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkinspect
from pykern import pkio
# defer importing pkconfig
import contextlib
import importlib
import inspect
import json
import os
import py
import pytest
import re
import sys

#: Environment var set by pykern.pkcli.test for each module under test
TEST_FILE_ENV = 'PYKERN_PKUNIT_TEST_FILE'

#: Where persistent input files are stored (test_base_name_data)
_DATA_DIR_SUFFIX = '_data'

#: Where to write temporary files (test_base_name_work)
_WORK_DIR_SUFFIX = '_work'

#: Set to the most recent test module by `pykern.pytest_plugin`
module_under_test = None

#: Type of a regular expression
_RE_TYPE = type(re.compile(''))

#: _test_file initialized?
_init = False

#: module being run by `pykern.pkcli.test`
_test_file = None


class PKFail(AssertionError):
    pass


def assert_object_with_json(basename, actual, ):
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
    fn = '{}.json'.format(basename)
    a = work_dir().join(fn)
    pkio.write_text(a, actual)
    e = data_dir().join(fn)
    expect = pkio.read_text(e)
    pkeq(expect, actual, 'diff {} {}', e, a)


def data_dir():
    """Compute the data directory based on the test name

    The test data directory is always ``<test>_data``, where ``<test>``
    is the name of the test's python module with the ``_test`` or
    ``test_`` removed.  For example, if the test file is
    ``setup_test.py`` then the directory will be ``setup_data``.

    Returns:
        py.path.local: data directory

    """
    return _base_dir(_DATA_DIR_SUFFIX)


def data_yaml(base_name):
    """Load base_name.yml from data_dir

    Args:
        base_name (str): name of YAML file with ``.yml`` extension

    Returns:
        object: YAML data structure, usually dict or array
    """
    from pykern import pkyaml

    return pkyaml.load_file(data_dir().join(base_name) + '.yml')


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


def file_eq(expect_path, **kwargs):
    """If actual is not expect_path, throw assertion with calling context.

    if `expect_path` ends in ``.json``, `pkjson` will be used.
    Otherwise, `expect_path` will be read as plain text.
    Same for `actual_path`.

    Args:
        expect_path (str or py.path): text file to be read; if str, then joined with `data_dir`
        actual (object): string or json data structure; if missing, read `actual_path`
        actual_path (py.path or str): where to write results; if str, then joined with `work_dir`; if None, ``work_dir().join(expect_path.relto(data_dir()))``
    """
    import pykern.pkjson
    import pykern.pkconst

    actual_path = kwargs.get('actual_path')
    if not isinstance(expect_path, pykern.pkconst.PY_PATH_LOCAL_TYPE):
        expect_path = data_dir().join(expect_path)
    if actual_path is None:
        actual_path = expect_path.relto(data_dir())
    if not isinstance(actual_path, pykern.pkconst.PY_PATH_LOCAL_TYPE):
        actual_path = work_dir().join(actual_path)
    a = 'actual' in kwargs
    actual = kwargs['actual'] if a else pkio.read_text(actual_path)
    if expect_path.ext == '.json':
        e = pykern.pkjson.load_any(expect_path)
        if a:
            pykern.pkjson.dump_pretty(actual, filename=actual_path)
    else:
        e = pkio.read_text(expect_path)
        if a:
            pkio.write_text(actual_path, actual)
    if e == actual:
        return
    c = f"diff '{expect_path}' '{actual_path}'"
    with os.popen(c) as f:
        pkfail(
            '{}',
            f'''expect != actual:
{c}
{f.read()}

to update test data:
    cp '{actual_path}' '{expect_path}'
'''
        )


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


@contextlib.contextmanager
def pkexcept(exc_or_re, *fmt_and_args, **kwargs):
    """Expect an exception to be thrown and match or output msg

    If `fmt_and_args` is falsey, will generate a message saying
    what was expected and what was received.

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
        fmt_and_args (tuple): passed to format
        kwargs (dict): passed to format

    Yields:
        None: just for context manager
    """
    try:
        yield None
    except BaseException as e:
        from pykern.pkdebug import pkdexc

        e_str = '{} {}'.format(type(e), e)
        if isinstance(exc_or_re, type) and issubclass(exc_or_re, BaseException):
            if isinstance(e, exc_or_re):
                return
            if not fmt_and_args:
                fmt_and_args=(
                    '{}: an exception was raised, but expected it to be {}; stack={}',
                    e_str,
                    exc_or_re,
                    pkdexc(),
                )
        else:
            if not isinstance(exc_or_re, _RE_TYPE):
                exc_or_re = re.compile(exc_or_re, flags=re.IGNORECASE)
            if exc_or_re.search(e_str):
                return
            if not fmt_and_args:
                fmt_and_args=(
                    '{}: an exception was raised, but did not match "{}"; stack={}',
                    e_str,
                    exc_or_re.pattern,
                    pkdexc(),
                )
    else:
        if not fmt_and_args:
            fmt_and_args=('Exception was not raised: expecting={}', exc_or_re)
    pkfail(*fmt_and_args, **kwargs)


def pkeq(expect, actual, *args, **kwargs):
    """If actual is not expect, throw assertion with calling context.

    Args:
        expect (object): what to test for
        actual (object): run-time value
        args (tuple): passed to pkfail()
        kwargs (dict): passed to pkfail()
    """
    if expect != actual:
        if args or kwargs:
            pkfail(*args, **kwargs)
        else:
            pkfail('expect={} != actual={}', expect, actual)


def pkfail(fmt, *args, **kwargs):
    """Format message and raise PKFail.

    Args:
        fmt (str): to be passed to `string.format`
        args (tuple): passed to format
        kwargs (dict): passed to format
    """
    msg = fmt.format(*args, **kwargs)
    call = pkinspect.caller(ignore_modules=[contextlib])
    raise PKFail('{} {}'.format(call, msg))


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
    if not re.search(expect_re, actual, flags=flags):
        pkfail('expect_re={} != actual={}', expect_re, actual)


def random_alpha(length=6):
    """Random lowercase alpha string

    Args:
        length (int): how many chars

    Returns:
        str: lower case alpha string
    """
    import random
    import string
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


def save_chdir_work(is_pkunit_prefix=False):
    """Create empty work_dir and chdir

    Args:
        is_pkunit_prefix (bool): use as root of (most) file I/O (optional)

    Returns:
        py.path.local: empty work directory

    """
    return pkio.save_chdir(empty_work_dir(), is_pkunit_prefix=is_pkunit_prefix)


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
    return _base_dir(_WORK_DIR_SUFFIX).ensure(dir=True)


def _base_dir(postfix):
    """Base name with directory.

    Args:
        postfix (str): what to append to base (``_data`` or ``_work``).

    Returns:
        py.path.local: base directory with postfix
    """
    global _init, _test_file
    if not _init:
        _init = True
        # pykern.pkcli.test
        t = os.environ.get(TEST_FILE_ENV)
        if t:
            _test_file = py.path.local(t)
    if _test_file:
        f = _test_file
    elif module_under_test:
        # pykern.pytest_plugin
        m = module_under_test
        f = py.path.local(m.__file__)
    else:
        # py.test alone, just guess
        s = inspect.currentframe().f_back.f_back
        f = None
        for _ in range(100):
            if s.f_code.co_filename.endswith('_test.py'):
                f = py.path.local(s.f_code.co_filename)
                break
            s = s.f_back
            if not s:
                break
        if not f:
            raise PKFail('unable to find test module')
    b = re.sub(r'_test$|^test_', '', f.purebasename)
    assert b != f.purebasename, \
        '{}: module name must end in _test'.format(f)
    return f.new(basename=b + postfix).realpath()
