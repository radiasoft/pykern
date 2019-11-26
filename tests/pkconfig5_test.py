# -*- coding: utf-8 -*-
u"""pkconfig to_environ() test

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_to_environ(pkconfig_setup):
    pkconfig = pkconfig_setup(
        cfg=dict(OTHER_THING='', P1_M1_SET4='a:b'),
        env=dict(P1_M1_REQ8='33'),
    )

    from pykern.pkcollections import PKDict
    assert PKDict(P1_M1_REQ8='33', P1_M1_SET4='a:b') == pkconfig.to_environ(['p1.*'])
    assert PKDict(P1_M1_REQ8='33', P1_M1_SET4='a:b', OTHER_THING='') \
        == pkconfig.to_environ(['p1.*', 'other.thing'])
    assert PKDict() == pkconfig.to_environ(['nomatch.*'])
