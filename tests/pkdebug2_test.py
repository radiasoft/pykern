# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkdebug`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


def test_format(capsys):
    from pykern import pkconfig
    pkconfig.reset_state_for_testing({
        'PYKERN_PKDEBUG_MAX_DEPTH': '2',
        'PYKERN_PKDEBUG_MAX_ELEMENTS': '5',
        'PYKERN_PKDEBUG_MAX_STRING': '5',
    })

    from pykern.pkdebug import pkdlog

    def _e(expected, value):
        pkdlog('{}', value)
        out, err = capsys.readouterr()
        err = ' '.join(err.split(' ')[1:])
        assert expected + '\n' == err, 'expected={} actual={}'.format(expected, err)

    _e(
        "{'a': 'b', 'c': {'d': {<SNIP>}}, 'h': 'i'}",
        {'a': 'b', 'c': {'d': {'e': {'f': 'g'}}}, 'h': 'i'},
    )
    _e(
        '[1, 2, 3, 4, 5, 6, <SNIP>]',
        [1, 2, 3, 4, 5, 6, 7, 8],
    )
    _e(
        '(1, 2, 3, 4)',
        (1, 2, 3, 4),
    )
    _e(
        '(1, {2, 3}, {4: 5}, [6, 7])',
        (1, {2, 3}, {4: 5}, [6, 7])
    )
    _e(
        "{'Passw<SNIP>': '<REDA<SNIP>', 'c': {'botp': '<REDA<SNIP>'}, 'totp': '<REDA<SNIP>', 'q': ['pAssw<SNIP>', 1], 'x': 'y', 's': 'r', <SNIP>}",
        {'Passwd': 'b', 'c': {'botp': 'a'}, 'totp': 'iiii', 'q': ['pAssword', 1], 'x': 'y', 's': 'r', 't': 'u'},
    )
    _e('a' * 5 + '<SNIP>', 'a' * 80)
    _e('<SNIP>' + 'a' * 5, '\n  File "' + 'a' * 80)
