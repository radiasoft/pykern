# -*- coding: utf-8 -*-
"""test pkjson

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_load_any():
    import json
    from pykern import pkcollections
    from pykern import pkjson
    from pykern.pkunit import pkeq

    j = json.dumps(["a", "b"])
    j2 = pkjson.load_any(j)
    pkeq("a", j2[0])
    j3 = json.dumps({"a": 33})
    j4 = pkjson.load_any(j3)
    pkeq(
        33,
        j4.a,
        "{}: j4.a is not 33",
        j4.a,
    )
    j5 = json.dumps({"a": 33, "b": {"values": "will collide, but ok"}})
    j6 = pkjson.load_any(j5)
    pkjson.load_any(j5, object_pairs_hook=pkcollections.PKDict)


def test_load_any_parse_int():
    from pykern import pkjson
    from pykern.pkunit import pkeq, pkexcept

    for c, e in (
        ("9007199254740992", float(2**53)),
        ("9007199254740991", int(2**53 - 1)),
        ("-9007199254740991", int(-(2**53) + 1)),
        ("-9007199254740992", float(-(2**53))),
        ("1" * 64, 1.1111111111111112e63),
    ):
        a = pkjson.load_any(c)
        pkeq(type(e), type(a))
        pkeq(e, a)
    with pkexcept("unreasonably large"):
        pkjson.load_any("1" * 65)


def test_dump_bytes():
    import json
    from pykern import pkjson, pkcompat
    from pykern.pkunit import pkeq

    v = ["a", "b"]
    expect = pkcompat.to_bytes(
        json.dumps(v).replace(" ", ""),
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

    v = {"d": ["a", "b"], "c": Other("xyz")}
    a = pkjson.dump_pretty(v)
    pkeq(
        """{
    "c": "xyz",
    "d": [
        "a",
        "b"
    ]
}
""",
        a,
    )
