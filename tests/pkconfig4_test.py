# -*- coding: utf-8 -*-
"""pkconfig init

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_init(pkconfig_setup):
    """Validate parse_set"""
    pkconfig = pkconfig_setup(
        cfg=dict(P1_M1_SET3="", P1_M1_SET4="a:b"),
        env=dict(P1_M1_REQ8="99", PYKERN_PKCONFIG_CHANNEL="dev"),
    )
    from p1.m1 import cfg
    from pykern import pkunit

    pkunit.pkeq(set(), cfg.set1)
    pkunit.pkeq(set([1]), cfg.set2)
    pkconfig.reset_state_for_testing()
    pkunit.pkeq(set(), cfg.set3)
    pkunit.pkeq(set(("a", "b")), cfg.set4)
    pkunit.pkeq(True, pkconfig.in_dev_mode())
