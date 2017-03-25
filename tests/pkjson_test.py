# -*- coding: utf-8 -*-
u"""test pkjson

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_load_any():
    """Validate json_load_any()"""
    import json
    from pykern import pkjson
    from pykern.pkunit import pkeq

    j = json.dumps(['a', 'b'])
    j2 = pkjson.load_any(j)
    pkeq('a', j2[0])
