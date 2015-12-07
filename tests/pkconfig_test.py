# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkconfig`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import dateutil.parser
import pytest
import sys

import py.path

def test_init(monkeypatch):
    """Validate initializing a module"""
    # Can't import anything yet
    data_dir = py.path.local(__file__).dirpath('pkconfig_data')
    monkeypatch.setenv('HOME', str(data_dir))
    #TODO(robnagler) test for this
    monkeypatch.setenv('P1_M1_DICT1_D4', 'env4')
    sys.path.insert(0, str(data_dir))
    from pykern import pkconfig
    pkconfig._root_pkg = None
    pkconfig.insert_search_path('p1')
    from p1.m1 import cfg
    assert 'replace1' == cfg['dict1']['d1'], \
        '~/.p1_pkconfig.py should replace dict1[d1]'
    assert 'default2' == cfg['dict1']['d2'], \
        'Nothing should change dict1[d2]'
    assert 'd3' in cfg['dict1'], \
        'd3 should appear in dict1 from the merge in ~/.p1_pkconfig.py'
    assert 'new3' == cfg.dict1.d3, \
        'dict1[d3] should be set to the value in new3'
    assert ['first1', 'second1'] == cfg['list2'], \
        '~/.p1_pkconfig.py should replace list2'
    assert 55 == cfg['p3'], \
        '~/.p1_pkconfig.py should set p3'
    assert dateutil.parser.parse('2012-12-12T12:12:12Z') == cfg['p6'], \
        'pkconfig_base.py sets time value and m1._custom_p6'
