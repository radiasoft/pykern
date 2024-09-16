"""Useful I/O operations

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# Root module: Limit imports to avoid dependency issues
from pykern import pkconst
from pykern import pkinspect
import pykern.util
import contextlib
import errno
import filecmp
import glob
import io
import os
import os.path
import py
import re
import shutil

#: used during unit testing see ``pykern.pkunit.save_chdir``
pkunit_prefix = None

TEXT_ENCODING = "utf-8"


def atomic_write(path, contents, **kwargs):
    """Overwrites an existing file with contents via rename to ensure integrity

    Args:
        path (str or py.path.Local): Path of file to overwrite
        contents (str): New contents
        kwargs (kwargs): to pass to `py.path.local.write`
    """
    n = py_path(path).new(ext="pkio-tmp-" + pykern.util.random_base62())
    assert not n.exists(), f"{n} already exists (file name collision)"
    try:
        n.write(contents, **kwargs)
        n.rename(path)
    finally:
        # unchecked_remove is too brutal for this specific case
        if n.exists():
            try:
                os.remove(str(n))
            except Exception:
                pass


def compare_files(path1, path2, force=False):
    """Compares two files using `filecmp.cmp`

    Note that `filecmp` uses `os.stat` to see if a file is the
    same. If the size, mtime, and type are not identical, it does
    a comparison of the contents.

    `filecmp` caches prior resuls of the content comparisons.
    `force` "ensures" no caching, but since the cache is global,
    this can't be guaranteed in multithreaded environments.

    Args:
        path1 (str or py.path): first file
        path2 (str or py.path): second file
        force (bool): if True, call `filecmp.clear_cache` before comparison and ignore stats.

    Returns:
        bool: True if the files exist and have the same stats

    """
    if force:
        filecmp.clear_cache()
    try:
        return filecmp.cmp(str(path1), str(path2), shallow=not force)
    except Exception as e:
        if exception_is_not_found(e):
            return False
        raise


def exception_is_not_found(exc):
    """True if exception is one various file not found errors

    Checks `FileNotFoundError` and `IOError` with `errno.ENOENT`.

    Args:
        exc (BaseException): to check

    Returns:
        bool: True if is a file not found exception.
    """
    return (
        isinstance(exc, FileNotFoundError)
        or isinstance(exc, IOError)
        and exc.errno == errno.ENOENT
        or isinstance(exc, py.error.ENOENT)
    )


def has_file_extension(filename, to_check):
    """if matches any of the file extensions

    Args:
        filename (str|py.path.local): what to check
        to_check (str|tuple|list): is without '.' and lower

    Returns:
        bool: if any of the extensions matches
    """
    if isinstance(to_check, pkconst.STRING_TYPES):
        to_check = (to_check,)
    e = py_path(filename).ext[1:].lower()
    return e in to_check


def is_pure_text(filepath, test_size=512):
    """Read test_size bytes of filepath to determine if it is likely a text file.

    See `pykern.util.is_pure_text` for the heuristics used to test bytes.

    Args:
        filepath (str|py.path): file to check
        test_size (int): number of bytes to read from filename

    Returns:
        bool: True if file is likely pure text, false if likely binary
    """
    from pykern import util

    with open(filepath, "rb") as f:
        b = f.read(test_size + 1)
    return util.is_pure_text(b[:test_size], is_truncated=len(b) > test_size)


def mkdir_parent(path):
    """Create the directories and their parents (if necessary)

    Args:
        path (str): dir to create

    Returns:
        py.path.local: path
    """
    return py_path(path).ensure(dir=True)


def mkdir_parent_only(path):
    """Create the paths' parent directories.

    Args:
        path (str): children of dir to create

    Returns:
        py.path.local: parent directory of path
    """
    return mkdir_parent(py_path(path).dirname)


def open_text(filename, **kwargs):
    """Open file with utf-8 for text.

    Args:
        filename (str or py.path.Local): File to open

    Returns:
        object: open file handle
    """
    kwargs.setdefault("mode", "rt")
    kwargs.setdefault("encoding", TEXT_ENCODING)
    return io.open(str(py_path(filename)), **kwargs)


def py_path(path=None):
    """Creates a py.path.Local object

    Will expanduser, if needed.

    If `pkunit_prefix` is set, will prefix, too.

    Args:
        path (str): path to convert (or None for current dir)

    Returns:
        py.path.Local: path
    """
    global pkunit_prefix

    res = py.path.local(path, expanduser=True)
    if pkunit_prefix:
        # Allow for <test>_work and <test>_data so we don't add
        # prefix if there's a common parent directory.
        if not str(res).startswith(pkunit_prefix.dirname):
            res = pkunit_prefix.join(res)
        py.path.local(res.dirname).ensure(dir=True)
    return res


def random_base62(*args, **kwargs):
    """DEPRECATED call `pykern.util.random_base62`"""
    from pykern import util

    return util.random_base62(*args, **kwargs)


def read_binary(filename):
    """Open file, read binary, and close.

    Args:
        filename (str or py.path.Local): File to open

    Returns:
        bytes: contents of `filename`
    """
    return py_path(filename).read_binary()


def read_text(filename):
    """Open file, read with utf-8 text, and close.

    Args:
        filename (str or py.path.Local): File to open

    Returns:
        Str: contents of `filename`
    """
    try:
        with open_text(filename) as f:
            return f.read()
    except Exception as e:
        pkinspect.append_exception_reason(e, f"filename={filename}")
        raise


@contextlib.contextmanager
def save_chdir(dirname, mkdir=False, is_pkunit_prefix=False):
    """Save current directory, change to directory, and restore.

    Args:
        dirname (str): directory to change to
        mkdir (bool): Make the directory?
        is_pkunit_prefix (bool): If True, sets pkunit_prefix.

    Returns:
        str: current directory before `chdir`
    """
    global pkunit_prefix

    prev_d = py.path.local().realpath()
    prev_ppp = pkunit_prefix
    try:
        if is_pkunit_prefix:
            d = py.path.local(dirname)
        else:
            d = py_path(dirname)
        if mkdir and not d.check(dir=1):
            mkdir_parent(d)
        os.chdir(str(d))
        if is_pkunit_prefix:
            pkunit_prefix = py.path.local(d)
        yield d.realpath()
    finally:
        os.chdir(str(prev_d))
        if is_pkunit_prefix:
            pkunit_prefix = prev_ppp


def sorted_glob(pattern, key=None):
    """Returns sorted list of files & dirs matching pattern.

    Use '**' in pattern for recursive search, else, use * as wildcard.
    Sorts using key if provided, else in ascending order.
    Doesn't include dot files unless dot "." is included explicitly
    at the start of a path component. Doesn't include . and ..
    To return files only, see walk_tree().

    Args:
        pattern (py.path.Local or str): to match file paths
        key (str): used to sort, must be name of py.path.Local attribute

    Returns:
        list: py.path.Local objects in sorted order
    """

    def _path_sort_attr(path):
        a = getattr(path, key)
        if callable(a):
            return a()
        return a

    return sorted(
        (py_path(f) for f in glob.iglob(str(pattern), recursive=True)),
        key=_path_sort_attr if key else None,
    )


def unchecked_remove(*paths):
    """Remove files or directories, ignoring OSError.

    Will not remove '/' or '.'

    Args:
        paths (str): paths to remove
    """
    cwd = py_path()
    for a in paths:
        p = py_path(a)
        assert len(p.parts()) > 1, "{}: will not remove root directory".format(p)
        assert cwd != p, "{}: will not remove current directory".format(p)
        try:
            os.remove(str(a))
        except OSError:
            try:
                shutil.rmtree(str(a), ignore_errors=True)
            except OSError:
                pass


def walk_tree(dirname, file_re=None):
    """Returns list of all files (only) in dirname (recursive), sorted in ascending order.

    Include file_re to filter results.
    Includes dot files, but not . and ..
    To include dirs in results, see sorted_glob().

    Args:
        dirname (str): top-level directory to walk
        file_re (re or str): Optionally, only return files which match the regular expression

    Returns:
        list: py.path.Local objects in sorted order
    """

    def _walk(dirname):
        for r, _, x in os.walk(dirname):
            r = py_path(r)
            for f in x:
                yield r.join(f)

    if not file_re:
        res = _walk(dirname)
    else:
        if not hasattr(file_re, "search"):
            file_re = re.compile(file_re)
        d = py_path(dirname)
        res = []
        for p in _walk(dirname):
            if file_re.search(d.bestrelpath(p)):
                res.append(p)
    return sorted(res)


def write_binary(path, contents):
    """Open file, write binary, and close.

    Args:
        path (str or py.path.Local): Path of file to write to
        contents (bytes): New contents

    Returns:
        py.path.local: `filename` as :class:`py.path.Local`
    """
    p = py_path(path)
    p.write_binary(contents)
    return p


def write_text(path, contents):
    """Open file, write text with utf-8, and close.

    Args:
        path (str or py.path.Local): Path of file to write to
        contents (str or bytes): New contents

    Returns:
        py.path.local: `filename` as :class:`py.path.Local`
    """
    from pykern import pkcompat

    p = py_path(path)
    try:
        with io.open(str(p), "wt", encoding=TEXT_ENCODING) as f:
            f.write(pkcompat.from_bytes(contents))
    except Exception as e:
        pkinspect.append_exception_reason(e, f"path={path}")
        raise
    return p
