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
import io
import locale
import os
import os.path
import py
import re
import shutil


def exception_is_not_found(exc):
    """True if exception is IOError and ENOENT

    Args:
        exc (BaseException): to check

    Returns:
        bool: True if is a file not found exception.
    """
    return isinstance(exc, IOError) and exc.errno == errno.ENOENT


def mkdir_parent(path):
    """Create the directories and their parents (if necessary)

    Args:
        path (str): dir to create

    Returns:
        py.path.local: path
    """
    return py.path.local(path).ensure(dir=True)


def mkdir_parent_only(path):
    """Create the paths' parent directories.

    Args:
        path (str): children of dir to create

    Returns:
        py.path.local: parent directory of path
    """
    return mkdir_parent(py.path.local(path).dirname)


def read_text(filename):
    """Open file, read with preferred encoding text, and close.

    Args:
        filename (str or py.path.Local): File to open

    Returns:
        str: contest of `filename`
    """
    fn = py.path.local(filename)
    with io.open(str(fn), encoding=locale.getpreferredencoding()) as f:
        return f.read();


@contextlib.contextmanager
def save_chdir(dirname, mkdir=False):
    """Save current directory, change to directory, and restore.

    Args:
        dirname (str): directory to change to
        mkdir (bool): Make the directory?

    Returns:
        str: current directory before `chdir`
    """
    prev_d = py.path.local().realpath()
    try:
        d = py.path.local(dirname)
        if mkdir and not d.check(dir=1):
            mkdir_parent(d)
        os.chdir(str(d))
        yield d.realpath()
    finally:
        os.chdir(str(prev_d))


def unchecked_remove(*paths):
    """Remove files or directories, ignoring OSError.

    Will not remove '/' or '.'

    Args:
        paths (str): paths to remove
    """
    cwd = py.path.local('.')
    for a in paths:
        p = py.path.local(a)
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
    dirname = py.path.local(dirname).realpath()
    dn = str(dirname)
    res = []
    for r, d, files in os.walk(dn, topdown=True, onerror=None, followlinks=False):
        for f in files:
            p = py.path.local(r).join(f)
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
    fn = py.path.local(filename)
    with io.open(str(fn), 'w', encoding=locale.getpreferredencoding()) as f:
        f.write(pkcompat.locale_str(contents))
    return fn
