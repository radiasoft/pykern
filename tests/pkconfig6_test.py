# -*- coding: utf-8 -*-
"""pkconfig init

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_init(pkconfig_setup):
    """Validate parse_set"""
    pkconfig = pkconfig_setup(
        cfg=dict(
            PYKERN_PKCONFIG_CHANNEL="dev",
            PYKERN_PKCONFIG_DEV_MODE="false",
            P1_M1_SET3="",
            P1_M1_SET4="a:b",
        ),
        env=dict(P1_M1_REQ8="99", P1_M1_HOSTS="h1"),
    )
    from pykern import pkunit

    with pkunit.pkexcept("p1.m1.req10: config"):
        from p1.m1 import cfg
