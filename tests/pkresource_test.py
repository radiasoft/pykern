# -*- coding: utf-8 -*-
u"""pytest for `pykern.resource`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import importlib

import pytest

from pykern import pkunit


def test_conformance1():
    d = pkunit.data_dir()
    t1 = importlib.import_module(d.basename + '.t1')
    assert t1.somefile().startswith('anything'), \
        'When somefile is called, it should return the "anything" file'
