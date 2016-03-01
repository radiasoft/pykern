# -*- coding: utf-8 -*-
u"""Useful operations for unit tests

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern import pkyaml
import importlib
import inspect
import json
import os
import py
import re
import sys

#: Where persistent input files are stored (test_base_name_data)
_DATA_DIR_SUFFIX = '_data'

#: Where to write temporary files (test_base_name_work)
_WORK_DIR_SUFFIX = '_work'


def assert_object_with_json(basename, actual):
    """Converts actual to JSON and compares with data_dir/basename.json

    Reads data_dir/basename.json and compares with actual
    converted to json. Trailing newline is managed properly. The
    keys are sorted and indentation is 4. actual written to work_dir.

    Args:
        expected_basename (str): file to be found in data_dir with json suffix
        actual (object): to be serialized as json
    """
    actual = json.dumps(actual, sort_keys=True, indent=4, separators=(',', ': ')) + '\n'
    fn = '{}.json'.format(basename)
    pkio.write_text(work_dir().join(fn), actual)
    expect = pkio.read_text(data_dir().join(fn))
    assert expect == actual


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
    """Create empty work_dir and chdir

    Returns:
        py.path.local: empty work directory

    """
    return pkio.save_chdir(empty_work_dir())


def work_dir():
    """Name of ephemeral work directory

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
    return _base_dir(_WORK_DIR_SUFFIX)


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
