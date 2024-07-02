# -*- coding: utf-8 -*-
"""PyTest for :mod:`pykern.pkarray`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_new_double():
    from pykern import pkarray

    d = pkarray.new_double()
    assert 0 == len(d), "new_double without initializer should be empty"
    d = pkarray.new_double([3, 5])
    assert 2 == len(d), "new_double with initializer, should be non-zero"
    assert float(5) == d[1], "new_double should intitialize to a float"


def test_new_float():
    from pykern import pkarray

    d = pkarray.new_float()
    assert 0 == len(d), "new_float without initializer should be empty"
    d = pkarray.new_float([3, 5])
    assert 2 == len(d), "new_float with initializer, should be non-zero"
    assert float(5) == d[1], "new_float should intitialize to a float"
