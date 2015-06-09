# -*- coding: utf-8 -*-
u"""PyTest for :mod:`pykern.pkinspect`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import sys

import pytest
import py

from pykern import pkunit
from pykern import pkinspect


def test_module_basename():
    p1 = pkunit.import_module_from_data_dir('p1')
    assert pkinspect.module_basename(p1) == 'p1'
    m1 = pkunit.import_module_from_data_dir('p1.m1')
    assert pkinspect.module_basename(m1) == 'm1'
    assert pkinspect.module_basename(m1.C) == 'm1'
    assert pkinspect.module_basename(m1.C()) == 'm1'
    assert pkinspect.module_basename(m1) == 'm1'
    assert pkinspect.module_basename(m1.C) == 'm1'
    assert pkinspect.module_basename(m1.C()) == 'm1'
    p2 = pkunit.import_module_from_data_dir('p1.p2')
    assert pkinspect.module_basename(p2) == 'p2'
    m2 = pkunit.import_module_from_data_dir('p1.p2.m2')
    assert pkinspect.module_basename(m2) == 'm2'
