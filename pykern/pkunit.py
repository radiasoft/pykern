# -*- coding: utf-8 -*-
u"""Useful operations for unit tests

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import importlib
import inspect
import os
import re
import sys

import py

from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern import pkyaml

#: Where persistent input files are stored (test_base_name_data)
_DATA_DIR_SUFFIX = '_data'

#: Where to write temporary files (test_base_name_work)
_WORK_DIR_SUFFIX = '_work'

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
    return pkyaml.load_file(data_dir().join(base_name) + '.yml')


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
    d = _base_dir(_WORK_DIR_SUFFIX)
    if os.path.exists(str(d)):
        # doesn't ignore "not found" errors
        d.remove(rec=1, ignore_errors=True)
    return d.ensure(dir=True)


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


def save_chdir_work():
    """Create empty workdir and chdir

    Returns:
        py.path.local: empty work directory

    """
    return pkio.save_chdir(empty_work_dir())


def _base_dir(postfix):
    """Base name with directory.

    Args:
        postfix (str): what to append to base (``_data`` or ``_work``).

    Returns:
        py.path.local: base directory with postfix
    """
    filename = py.path.local(pkinspect.caller_module().__file__)
    b = re.sub(r'_test$|^test_', '', filename.purebasename)
    return py.path.local(filename.dirname).join(b + postfix).realpath()
