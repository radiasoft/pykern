# -*- coding: utf-8 -*-
u"""Test `pykern.pytest_fixtures`.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import os
import os.path

_WORK_DIR = 'pytest_plugin_work'

_SENTINEL = 'sentinel.d'

# Leave something in the directory so we are sure it gets cleared
d = os.path.join(os.path.dirname(__file__), _WORK_DIR, _SENTINEL)
if not os.path.exists(d):
    os.makedirs(d)


def test_1_chdir_work(pk_chdir_work):
    """Verify pk_chdir_work clears and sets current dir"""
    import os, py.path
    assert _WORK_DIR == pk_chdir_work.basename, \
        '{}: pk_chdir_work should return work_dir'.format(pk_chdir_work)
    d = py.path.local(py.path.local(__file__).dirname).join(_WORK_DIR).realpath()
    assert d == os.getcwd(), \
        '{}: pk_chdir_work should chdir to work_dir'.format(os.getcwd())
    s = py.path.local(_SENTINEL)
    assert s.check(exists=False), \
        '{}: sentinel should not exist'.format(s)
    s.ensure(dir=True)


def test_2_work_dir(pk_work_dir):
    """Verify pk_work_dir does not empty directory"""
    import py.path
    d = py.path.local(py.path.local(__file__).dirname).realpath()
    assert os.getcwd() == str(d)
    s = pk_work_dir.join(_SENTINEL)
    assert s.check(exists=True), \
        '{}: sentinel should exist'.format(s)
