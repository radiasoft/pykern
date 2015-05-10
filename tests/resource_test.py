# -*- coding: utf-8 -*-
u"""pytest for `pykern.resource`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import pytest

from t_resource import t1

def test_conformance1():
    """Verify basic modes work"""
    assert t1.somefile().startswith('anything')
