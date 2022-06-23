# -*- coding: utf-8 -*-
"""pkconfig init test

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_init(pkconfig_setup):
    """Validate initializing a module"""
    pkconfig = pkconfig_setup(
        cfg=dict(
            P1_M1_BOOL3="",
            P1_M1_BOOL4="y",
            P1_M1_P6="2012-12-12T12:12:12Z",
        ),
        env=dict(P1_M1_REQ8="99"),
    )
    import dateutil.parser

    from p1.m1 import cfg

    assert "default2" == cfg["dict1"]["d2"], "Nothing should change dict1[d2]"
    assert (
        dateutil.parser.parse("2012-12-12T12:12:12Z") == cfg["p6"]
    ), "environ sets time value and m1._custom_p6"
    assert 999 == cfg.dynamic_default10, "When value is None, calls parser"
    assert False == cfg.bool1, "When bool1 is none, is False"
    assert True == cfg.bool2, "When bool2 is none, is True"
    pkconfig.reset_state_for_testing()
    assert False == cfg.bool3, "bool3 should be overriden to be False"
    assert True == cfg.bool4, "bool4 should be overriden to be True"
