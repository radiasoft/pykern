# -*- coding: utf-8 -*-
"""pytest for `pykern.pkdebug.pkdformat`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_pkdformat():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing(
        {
            "PYKERN_PKDEBUG_MAX_DEPTH": "2",
            "PYKERN_PKDEBUG_MAX_ELEMENTS": "5",
            "PYKERN_PKDEBUG_MAX_STRING": "5",
        }
    )

    from pykern.pkdebug import pkdformat
    from pykern.pkunit import pkeq

    def _e(expected, value):
        pkeq(expected, pkdformat("{}", value))

    _e(
        "{'a': 'b', 'c': {'d': {<SNIP>}}, 'h': 'i'}",
        {"a": "b", "c": {"d": {"e": {"f": "g"}}}, "h": "i"},
    )
    _e(
        "{1}",
        set([1]),
    )

    _e(
        "(1, 2, 3, 4, 5)",
        (1, 2, 3, 4, 5),
    )
    _e(
        "[1, 2, 3, 4, 5, <SNIP>]",
        [1, 2, 3, 4, 5, 6],
    )
    _e(
        "(1, 2, 3, 4)",
        (1, 2, 3, 4),
    )
    _e(
        "(1, {2, 3}, {'passw<SNIP>': <REDACTED>}, [6, 7])",
        (1, {2, 3}, {"password": 5}, [6, 7]),
    )
    _e(
        "{'Secre<SNIP>': <REDACTED>, 'c2': {'botp': <REDACTED>}, 'q3': ['passw<SNIP>', 1], 's4': 'r', 't5': 'u', <SNIP>}",
        {
            "Secret1": "b",
            "c2": {"botp": "a"},
            "totp7": "iiii",
            "q3": ["password", 1],
            "x6": "y",
            "s4": "r",
            "t5": "u",
        },
    )
    _e("a" * 5 + "<SNIP>", "a" * 80)
    _e("<SNIP>" + "a" * 5, '\n  File "' + "a" * 80)

    class T:
        def pkdebug_str(self):
            return "foo"

    _e("foo", T())


def test_pkdformat_spec():
    from pykern import pkdebug, pkunit
    import decimal

    pkunit.pkeq(
        "1.23 None 003 01 True",
        pkdebug.pkdformat("{:.2f} {} {:03d} {:02d} {}", 1.23, None, 3, True, True),
    )
