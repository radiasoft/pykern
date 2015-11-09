# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkconfig`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import pytest
import sys

import py.path

def test_init(monkeypatch):
    """Validate initializing a module"""
    # Can't import anything yet
    data_dir = py.path.local(__file__).dirpath('pkconfig_data')
    monkeypatch.setenv('HOME', str(data_dir))
    sys.path.insert(0, str(data_dir))
    from pykern import pkconfig
    pkconfig._root_pkg = None
    pkconfig.set_root_pkg('p1')
    from p1.m1 import cfg
    assert 'replace1' == cfg.dict1['d1'], \
        '~/.p1_pkconfig.py should replace dict1[d1]'
    assert 'default2' == cfg.dict1['d2'], \
        'Nothing should change dict1[d2]'
    assert 'new3' == cfg.dict1['d3'], \
        '~/.p1_pkconfig.py should create dict1[d3]'
    assert ['first1', 'after1', 'after2'] == cfg.list2, \
        '~/.p1_pkconfig.py should append to list2'
    assert 123 == cfg.p3, \
        '~/.p1_pkconfig.py should set p3'
    assert '!first1!' == cfg.p4, \
        'Jinja should replace p4 value with list2[0]'
    assert datetime.datetime(2012, 12, 12, 12, 12, 55) == cfg.p6, \
        'pkconfig_base.py sets basic time with jinja p3 value and m1._custom_p6'
