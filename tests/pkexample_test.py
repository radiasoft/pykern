# -*- coding: utf-8 -*-
u"""Demonstrates RadiaSoft style testing.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from pykern import pkexample


def test_ema_compute():
    ema = pkexample.EMA(4)
    ema.compute(20.)
    assert 16. == ema.compute(10.), \
        'Adding a value to the series changes the average'

def test_ema_init():
    assert 5.0 == pkexample.EMA(1).compute(5.), \
        'First values sets initial average'


def test_ema_init_deviance():
    with pytest.raises(AssertionError) as e:
        pkexample.EMA(0)
    assert 'must be greater' in str(e.value)
