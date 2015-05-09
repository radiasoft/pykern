# -*- coding: utf-8 -*-
"""pytest for `pykern.resource`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""

import pytest

from t_resource import t1

def test_conformance1():
    """Verify basic modes work"""
    assert t1.somefile().startswith('anything')
