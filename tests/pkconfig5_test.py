# -*- coding: utf-8 -*-
"""pkconfig to_environ() test

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_to_environ(pkconfig_setup):
    pkconfig = pkconfig_setup(
        cfg=dict(OTHER_THING="", P1_M1_SET4="a:b"),
        env=dict(P1_M1_REQ8="33", PYKERN_PKCONFIG_DEV_MODE="0"),
    )

    from pykern.pkcollections import PKDict

    assert PKDict(P1_M1_REQ8="33", P1_M1_SET4="a:b") == pkconfig.to_environ(["p1.*"])
    assert PKDict(
        P1_M1_REQ8="33", P1_M1_SET4="a:b", OTHER_THING=""
    ) == pkconfig.to_environ(["p1.*", "other.thing"])
    assert PKDict() == pkconfig.to_environ(["nomatch.*"])

    from pykern import pkunit

    a = pkconfig.to_environ(
        ["foo.*", "baz.*.*"],
        values=dict(
            {
                "foo_bar": ["a", "c"],
                "foo.bar2": "2",
                "foo_BAR3": True,
                "FOO": {
                    "BAR4": False,
                    "BAR5": 5,
                },
                "baz.bar.exclude": 7,
                "baz.nomatch": 8,
                "baz.bar.foo": 9,
                "nomatch.foo": "4",
            }
        ),
        exclude_re="exclude",
    )
    pkunit.pkeq(
        dict(
            FOO_BAR="a:c",
            FOO_BAR2="2",
            FOO_BAR3="1",
            FOO_BAR4="",
            FOO_BAR5="5",
            BAZ_BAR_FOO="9",
        ),
        a,
    )
    pkunit.pkeq(False, pkconfig.in_dev_mode())
