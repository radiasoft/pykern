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
        cfg=dict(
            PYKERN_PKCONFIG_CHANNEL='alpha',
            P1_M1_SET3='',
            P1_M1_SET4='a:b',
        ),
        env=dict(P1_M1_REQ8='99', P1_M1_REQ10='h1:h2'),
    )
    from pykern import pkunit
    from p1.m1 import cfg
    assert cfg.req10 == ('h1', 'h2')
