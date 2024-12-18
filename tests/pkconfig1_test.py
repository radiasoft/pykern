# -*- coding: utf-8 -*-
"""pytest for `pykern.pkconfig`

:copyright: Copyright (c) 2015-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_channel_in(pkconfig_setup):
    """Validate channel_in()"""
    pkconfig = pkconfig_setup(
        env={
            "PYKERN_PKCONFIG_CHANNEL": "dev",
            "SOME_VALUE": "1",
            "some_value": "2",
        },
    )
    channel = "dev"
    not_channel = "alpha"
    assert pkconfig.channel_in(channel), "Should match configured channel"
    assert not pkconfig.channel_in(not_channel), "Should not match configured channel"
    assert pkconfig.channel_in(not_channel, channel), "Should match configured channel"
    with pytest.raises(AssertionError):
        pkconfig.channel_in("bad channel")


def test_flatten_values():
    from pykern.pkconfig import flatten_values
    from pykern import pkcollections

    base = pkcollections.Dict()
    flatten_values(base, {"aa": 1, "bb": {"cc": 3}})
    assert base["bb_cc"] == 3
    flatten_values(base, {"bb": {"dd": 4}})
    assert base["bb_cc"] == 3
    assert base["bb_dd"] == 4


def test_parse_bytes():
    from pykern.pkconfig import parse_bytes

    assert 10 == parse_bytes(10)
    assert 20 == parse_bytes("20")
    assert 1024 == parse_bytes("1k")
    assert 2097152 == parse_bytes("2m")
    assert 751619276800 == parse_bytes("700GB")
    assert 4398046511104 == parse_bytes("004Tb")


def test_parse_positive_int():
    from pykern.pkconfig import parse_positive_int
    from pykern import pkunit

    pkunit.pkeq(1, parse_positive_int(1))
    pkunit.pkeq(2, parse_positive_int("2"))
    with pkunit.pkexcept("int or str"):
        parse_positive_int(1.0)
    with pkunit.pkexcept("be positive"):
        parse_positive_int(0)
    with pkunit.pkexcept("be positive"):
        parse_positive_int("-1")


def test_parse_seconds():
    from pykern.pkconfig import parse_seconds, parse_secs

    assert 999 == parse_seconds("999")
    assert 3600 == parse_seconds("1:0:0")
    assert 90061 == parse_seconds("1d1:1:1")
    assert 86461 == parse_seconds("1d1:1")
    assert 86401 == parse_seconds("1d1")
    assert 172800 == parse_seconds("2d")
    # deprecated form
    assert 1 == parse_secs(1)
