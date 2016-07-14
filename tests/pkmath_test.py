# -*- coding: utf-8 -*-
u"""Validate pkmath

Used as a demonstration for good testing.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from pykern import pkmath


def test_ema():
    e = pkmath.EMA(4)
    assert 5.0 == e.compute(5.0), \
        'First values sets initial average'
    assert 7.0 == e.compute(10.0), \
        'Adding a value to the series changes the average'
    with pytest.raises(AssertionError):
        pkmath.EMA(0)
