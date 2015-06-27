# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkcli`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open
from pykern.pkdebug import pkdc, pkdp

import re
import sys

import argh
import pytest

from pykern import pkcli
from pykern import pkunit


def test_command_error(capsys):
    with pytest.raises(argh.CommandError) as e:
        pkcli.command_error('{abc}', abc='abcdef')
    assert 'abcdef' in e.value, \
        'When passed a format, command_error should output formatted result'


def test_main1():
    """Verify basic modes work"""
    _conf(['conf1', 'cmd1', '1'])
    _conf(['conf1', 'cmd2'], first_time=False)
    _conf(['conf2', 'cmd1', '2'])
    _conf(['conf3', '3'], default_command=True)


def test_main2(capsys):
    _dev([], None, r'\nconf1\nconf2\n', capsys)
    _dev(['--help'], None, r'\nconf1\nconf2\n', capsys)
    _dev(['conf1'], SystemExit, r'cmd1,cmd2.*too few', capsys)
    _dev(['not_found'], None, r'no module', capsys)
    _dev(['conf2', 'not-cmd1'], SystemExit, r'\{cmd1\}', capsys)


def _conf(argv, first_time=True, default_command=False):
    full_name = _root_pkg() + '.pykern_cli.' + argv[0]
    if not first_time:
        assert not hasattr(sys.modules, full_name)
    assert _main(argv) == 0, 'Unexpected exit'
    m = sys.modules[full_name]
    if default_command:
        assert m.last_cmd.__name__ == 'default_command'
        assert m.last_arg == argv[1]
    else:
        assert m.last_cmd.__name__ == argv[1]


def _dev(argv, exc, expect, capsys):
    if exc:
        with pytest.raises(exc):
            _main(argv)
    else:
        assert _main(argv) == 1, 'Failed to exit(1): ' + argv
    out, err = capsys.readouterr()
    assert re.search(pkdp(expect), pkdp(err), flags=re.IGNORECASE+re.DOTALL), \
        'Looking for {} in err={}'.format(expect, err)


def _main(argv):
    sys.argv[:] = ['pkcli_test']
    sys.argv.extend(argv)
    return pkcli.main(_root_pkg())


def _root_pkg():
    """Return data dir, which is a Python package"""
    return pkunit.data_dir().basename
