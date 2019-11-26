# -*- coding: utf-8 -*-
u"""pkconfig init

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_init(pkconfig_setup):
    """Validate parse_set"""
    pkconfig = pkconfig_setup(
        cfg=dict(P1_M1_SET3='', P1_M1_SET4='a:b'),
        env=dict(P1_M1_REQ8='99'),
    )
    from p1.m1 import cfg
    assert set() == cfg.set1, \
        'When set1 is none, is empty'
    assert set([1]) == cfg.set2, \
        'When set2 is none, is (1,)'
    pkconfig.reset_state_for_testing()
    assert set() == cfg.set3, \
        'set3 should be overriden to be empty'
    assert set(('a', 'b')) == cfg.set4, \
        'set4 should be overriden to be ("a", "b")'
