# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkconfig`

:copyright: Copyright (c) 2015-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_channel_in(pkconfig_setup):
    """Validate channel_in()"""
    pkconfig = pkconfig_setup(env={'PYKERN_PKCONFIG_CHANNEL': 'dev'})
    channel = 'dev'
    not_channel = 'alpha'
    assert pkconfig.channel_in(channel), \
        'Should match configured channel'
    assert not pkconfig.channel_in(not_channel), \
        'Should not match configured channel'
    assert pkconfig.channel_in(not_channel, channel), \
        'Should match configured channel'
    with pytest.raises(AssertionError):
        pkconfig.channel_in('bad channel')


def test_flatten_values():
    from pykern.pkconfig import flatten_values
    from pykern import pkcollections

    base = pkcollections.Dict()
    flatten_values(base, {'aa': 1, 'bb': {'cc': 3}})
    assert base['bb_cc'] == 3
    flatten_values(base, {'bb': {'dd': 4}})
    assert base['bb_cc'] == 3
    assert base['bb_dd'] == 4
