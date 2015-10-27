# -*- coding: utf-8 -*-
u"""PyTest for :mod:`pykern.pkarray`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import pytest

import py

from pykern import pkarray


def test_new_double():
    d = pkarray.new_double()
    assert 0 == len(d), \
        'new_double without initializer should be empty'
    d = pkarray.new_double([3, 5])
    assert 2 == len(d), \
        'new_double with initializer, should be non-zero'
    assert float(5) == d[1], \
        'new_double should intitialize to a float'


def test_new_float():
    d = pkarray.new_float()
    assert 0 == len(d), \
        'new_float without initializer should be empty'
    d = pkarray.new_float([3, 5])
    assert 2 == len(d), \
        'new_float with initializer, should be non-zero'
    assert float(5) == d[1], \
        'new_float should intitialize to a float'
