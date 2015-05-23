# -*- coding: utf-8 -*-
u"""Useful I/O operations

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import contextlib
import copy
import errno
import os
import os.path

import py


def write_file(filename, contents):
    """Open file, write to it, and close.

    Args:
        filename (str or py.path.Local): File to open
        contents (str): New contents

    Returns:
        py.path.local: filename
    """
    f = py.path.local(filename)
    f.write(contents)
    return f


@contextlib.contextmanager
def save_chdir(dirname):
    """Save current directory, change to directory, and restore.

    Args:
        dirname (str): directory to change to

    Returns:
        str: current directory before `chdir`
    """
    prev_dir = py.path.local(os.getcwd()).realpath()
    try:
        os.chdir(str(dirname))
        yield copy.deepcopy(prev_dir)
    finally:
        os.chdir(str(prev_dir))
