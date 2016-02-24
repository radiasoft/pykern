# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkcli`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp

import re
import sys

import argh
import pytest

from pykern import pkcli
from pykern import pkconfig
from pykern import pkunit

_PKGS = {
    'p1': 'pykern_cli',
    'p2': 'pkcli',
}


def test_command_error(capsys):
    with pytest.raises(argh.CommandError) as e:
        pkcli.command_error('{abc}', abc='abcdef')
    assert 'abcdef' in e.value, \
        'When passed a format, command_error should output formatted result'


def test_main1():
    """Verify basic modes work"""
    for rp in _PKGS:
        pkconfig.reset_state_for_testing()
        _conf(rp, ['conf1', 'cmd1', '1'])
        _conf(rp, ['conf1', 'cmd2'], first_time=False)
        _conf(rp, ['conf2', 'cmd1', '2'])
        _conf(rp, ['conf3', '3'], default_command=True)


def test_main2(capsys):
    all_modules = r':\nconf1\nconf2\nconf3\n$'
    for rp in _PKGS:
        pkconfig.reset_state_for_testing()
        _dev(rp, [], None, all_modules, capsys)
        _dev(rp, ['--help'], None, all_modules, capsys)
        _dev(rp, ['conf1'], SystemExit, r'cmd1,cmd2.*too few', capsys)
        _dev(rp, ['conf1', '-h'], SystemExit, r'\{cmd1,cmd2\}.*positional arguments', capsys)
        _dev(rp,['not_found'], None, r'no module', capsys)
        _dev(rp, ['conf2', 'not-cmd1'], SystemExit, r'\{cmd1\}', capsys)


def test_main3():
    """Verify underscores are converted to dashes"""
    assert 0 == _main('p3', ['some-mod', 'some-func']), \
        'some-mod some-func: dashed module and function should work'
    assert 0 == _main('p3', ['some_mod', 'some_func']), \
        'some_mod some-func: underscored module and function should work'


def _conf(root_pkg, argv, first_time=True, default_command=False):
    full_name = '.'.join([root_pkg, _PKGS[root_pkg], argv[0]])
    if not first_time:
        assert not hasattr(sys.modules, full_name)
    assert _main(root_pkg, argv) == 0, 'Unexpected exit'
    m = sys.modules[full_name]
    if default_command:
        assert m.last_cmd.__name__ == 'default_command'
        assert m.last_arg == argv[1]
    else:
        assert m.last_cmd.__name__ == argv[1]


def _dev(root_pkg, argv, exc, expect, capsys):
    if exc:
        with pytest.raises(exc):
            _main(root_pkg, argv)
    else:
        assert _main(root_pkg, argv) == 1, 'Failed to exit(1): ' + argv
    out, err = capsys.readouterr()
    if not err:
        err = out
    assert re.search(expect, err, flags=re.IGNORECASE+re.DOTALL), \
         'Looking for {} in err={}'.format(expect, err)


def _main(root_pkg, argv):
    sys.argv[:] = ['pkcli_test']
    sys.argv.extend(argv)
    dd = str(pkunit.data_dir())
    try:
        sys.path.insert(0, dd)
        return pkcli.main(root_pkg)
    finally:
        if sys.path[0] == dd:
            sys.path.pop(0)
