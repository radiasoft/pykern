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
            P1_M1_BOOL3="",
            P1_M1_BOOL4="y",
            P1_M1_P6="2012-12-12T12:12:12Z",
        ),
        env=dict(P1_M1_REQ8="99"),
    )
    from pykern import pkunit

    with pkunit.pkexcept("Must be a directory and exist; key=root, value="):
        from p1.exceptions import cfg