# -*- coding: utf-8 -*-
u"""Useful operations for unittests

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import errno
import inspect
import os
import re

import py


def data_dir():
    """Compute the data directory based on the test name

    The test data directory is always ``<test>_data``, where ``<test>``
    is the name of the test's python module with the ``_test`` or
    ``test_`` removed.  For example, if the test file is
    ``setup_test.py`` then the directory will be ``setup_data``.

    Returns:
        py.path.local: data directory

    """
    return _base_dir('_data')


def empty_work_dir():
    """Create an empty subdirectory based on the test name.

    To enable easier debugging, the test directory is always
    ``<test>_work``, where ``<test>`` is the name of the test's python
    module with the ``_test`` or ``test_`` removed.  For example, if the
    test file is ``setup_test.py`` then the directory will be
    ``setup_work``.

    The name "work" distinguishes from "tmp", which could imply
    anything. Also, with editor autocomplete, "setup_work" and
    "setup_test" are more easily distinguishable.

    All contents of the test directory will be removed.

    Returns:
        py.path.local: empty work directory

    """
    d = _base_dir('_work')
    if os.path.exists(str(d)):
        # doesn't ignore "not found" errors
        d.remove(rec=1, ignore_errors=True)
    return d.ensure(dir=True)


def _base_dir(postfix):
    """Base name with directory.

    Args:
        postfix (str): what to append to base (``_data`` or ``_work``).

    Returns:
        py.path.local: base directory with postfix
    """
    try:
        frame = inspect.currentframe().f_back.f_back
        filename = py.path.local(frame.f_code.co_filename)
    finally:
        if frame:
            del frame
    b = re.sub(r'_test$|^test_', '', filename.purebasename)
    return py.path.local(filename.dirname).join(b + postfix).realpath()
