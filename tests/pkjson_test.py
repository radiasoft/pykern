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
    from pykern import pkjson
    from pykern.pkunit import pkeq

    v = ['a', 'b']
    expect = json.dumps(v).encode(pkjson.ENCODING).replace(' ', '')
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

    v = {'d': ['a', 'b'], 'c': str(Other('xyz'))}
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


def test_encode_uknown_type():
    from pykern import pkjson
    from pykern.pkunit import pkexcept

    class X(object):
        pass

    with pkexcept('TypeError.*Unable to encode.*pkjson_test.X'):
        pkjson.dump_pretty({'a': X()})


def test_encode_pypath():
    from pykern import pkjson
    from pykern import pkio
    from pykern.pkunit import pkeq

    p = '/foo/bar.py'
    pkeq(
        '{{"p":"{}"}}'.format(p),
        pkjson.dump_pretty({'p': pkio.py_path(p)}, pretty=False),
        )
