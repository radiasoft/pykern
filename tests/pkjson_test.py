# -*- coding: utf-8 -*-
u"""test pkjson

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_load_any():
    import json
    from pykern import pkjson
    from pykern.pkunit import pkeq

    j = json.dumps(['a', 'b'])
    j2 = pkjson.load_any(j)
    pkeq('a', j2[0])


def test_dump_bytes():
    import json
    from pykern import pkjson, pkcompat
    from pykern.pkunit import pkeq

    v = ['a', 'b']
    expect = pkcompat.to_bytes(
        json.dumps(v).replace(' ', ''),
    )
    actual = pkjson.dump_bytes(v)
    pkeq(expect, actual)
    actual = pkjson.load_any(actual)
    pkeq(v, actual)


def test_dump_pretty():
    from pykern import pkjson
    from pykern.pkunit import pkeq

    class Other(object):
        def __init__(self, x):
            self.x = x

        def __str__(self):
            return str(self.x)

    v = {'d': ['a', 'b'], 'c': Other('xyz')}
    a = pkjson.dump_pretty(v)
    pkeq(
        '''{
    "c": "xyz",
    "d": [
        "a",
        "b"
    ]
}
''',
        a,
    )
