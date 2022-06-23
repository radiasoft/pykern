# -*- coding: utf-8 -*-
"""pkconfig init testing

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_init(pkconfig_setup):
    """Validate parse_tuple"""
    pkconfig = pkconfig_setup(
        cfg=dict(P1_M1_TUPLE3="", P1_M1_TUPLE4="aaa:bbbb"),
        env=dict(P1_M1_REQ8="99"),
    )
    from p1.m1 import cfg

    assert () == cfg.tuple1, "When tuple1 is none, is empty"
    assert (1,) == cfg.tuple2, "When tuple2 is none, is (1,)"
    pkconfig.reset_state_for_testing()
    assert () == cfg.tuple3, "tuple3 should be overriden to be empty"
    assert (
        "aaa",
        "bbbb",
    ) == cfg.tuple4, 'tuple4 should be overriden to be ("aaa", "bbbb")'
    assert ("dev-host",) == cfg.req10
