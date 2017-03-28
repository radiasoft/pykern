# -*- coding: utf-8 -*-
u"""Useful I/O operations

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
import contextlib
import copy
import errno
import glob
import io
import locale
import os
import os.path
import py
import re
import shutil
import six

#: used during unit testing see ``pykern.pkunit.save_chdir``
pkunit_prefix = None


def exception_is_not_found(exc):
    """True if exception is IOError and ENOENT

    Args:
        exc (BaseException): to check

    Returns:
        bool: True if is a file not found exception.
    """
    return isinstance(exc, IOError) and exc.errno == errno.ENOENT or isinstance(exc, py.error.ENOENT)


def expand_user_path(path):
    """Calls expanduser on path

    If `pkunit_prefix` is set, will prefix, too.

    Args:
        path (str): path to expand

    Returns:
        py.path.Local: expanded path
    """
    return py_path(path)


def has_file_extension(filename, to_check):
    """if matches any of the file extensions

    Args:
        filename (str|py.path.local): what to check
        to_check (str|tuple|list): is without '.' and lower

    Returns:
        bool: if any of the extensions matches
    """
    if isinstance(to_check, six.string_types):
        to_check = (to_check)
    e = py_path(filename).ext[1:].lower()
    return e in to_check


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


def read_text(filename):
    """Open file, read with preferred encoding text, and close.

    Args:
        filename (str or py.path.Local): File to open

    Returns:
        str: contest of `filename`
    """
    fn = py_path(filename)
    with io.open(str(fn), encoding=locale.getpreferredencoding()) as f:
        return f.read();


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


def sorted_glob(path):
    """sorted list of py.path.Local objects, non-recursive

    Args:
        path (py.path.Local or str): pattern

    Returns:
        list: py.path.Local objects
    """
    return sorted(py_path(f) for f in glob.glob(str(path)))


def unchecked_remove(*paths):
    """Remove files or directories, ignoring OSError.

    Will not remove '/' or '.'

    Args:
        paths (str): paths to remove
    """
    cwd = py_path()
    for a in paths:
        p = py_path(a)
        assert len(p.parts()) > 1, \
            '{}: will not remove root directory'.format(p)
        assert cwd != p, \
            '{}: will not remove current directory'.format(p)
        try:
            os.remove(str(a))
        except OSError:
            try:
                shutil.rmtree(str(a), ignore_errors=True)
            except OSError:
                pass


def walk_tree(dirname, file_re=None):
    """Return list files (only) as py.path's, top down, sorted

    If you want to go bottom up, just reverse the list.

    Args:
        dirname (str): directory to walk
        match_re (re or str): Optionally, only return files which match file_re

    Yields:
        py.path.local: paths in sorted order
    """
    fr = file_re
    if fr and not hasattr(fr, 'search'):
        fr = re.compile(fr)
    dirname = py_path(dirname).realpath()
    dn = str(dirname)
    res = []
    for r, d, files in os.walk(dn, topdown=True, onerror=None, followlinks=False):
        for f in files:
            p = py_path(r).join(f)
            if fr and not fr.search(dirname.bestrelpath(p)):
                continue
            res.append(p)
    # Not an iterator, but works as one. Don't assume always will return list
    return sorted(res)


def write_text(filename, contents):
    """Open file, write text with preferred encoding, and close.

    Args:
        filename (str or py.path.Local): File to open
        contents (str): New contents

    Returns:
        py.path.local: `filename` as :class:`py.path.Local`
    """
    fn = py_path(filename)
    with io.open(str(fn), 'w', encoding=locale.getpreferredencoding()) as f:
        f.write(pkcompat.locale_str(contents))
    return fn
