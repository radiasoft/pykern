# -*- coding: utf-8 -*-
u"""PyTest for :mod:`pykern.pkunit`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import os

import py
import pytest

from pykern import pkunit


def test_empty_work_dir():
    expect = py.path.local('pkunit_work').realpath()
    if os.path.exists(str(expect)):
        expect.remove(rec=1)
    assert not os.path.exists(str(expect)), \
        'Ensure directory was removed'
    d = pkunit.empty_work_dir()
    assert type(d) == type(py.path.local()), \
        'Verify type of empty_work_dir is same as returned by py.path.local'
    assert d == expect, \
        'Verify empty_work_dir has correct return value'
    assert os.path.exists(str(d)), \
        'Ensure directory was created'


def test_data_dir():
    expect = py.path.local('pkunit_data').realpath()
    d = pkunit.data_dir()
    assert type(d) == type(py.path.local()), \
        'Verify type of data_dir is same as returned by py.path.local'
    assert d == expect, \
        'Verify data_dir has correct return value'
