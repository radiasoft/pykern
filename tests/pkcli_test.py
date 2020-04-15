# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkcli`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_command_error(capsys):
    from pykern import pkcli
    from pykern import pkconfig

    pkconfig.reset_state_for_testing()
    with pytest.raises(pkcli.CommandError) as e:
        pkcli.command_error('{abc}', abc='abcdef')
    assert 'abcdef' in str(e.value), \
        'When passed a format, command_error should output formatted result'
    _dev('p2', ['some-mod', 'command-error'], None, r'raising CommandError', capsys)


def test_main1():
    """Verify basic modes work"""
    from pykern import pkconfig

    pkconfig.reset_state_for_testing()
    rp = 'p1'
    _conf(rp, ['conf1', 'cmd1', '1'])
    _conf(rp, ['conf1', 'cmd2'], first_time=False)
    _conf(rp, ['conf2', 'cmd1', '2'])
    _conf(rp, ['conf3', '3'], default_command=True)


def test_main2(capsys):
    from pykern import pkconfig
    import six

    all_modules = r':\nconf1\nconf2\nconf3\n$'
    pkconfig.reset_state_for_testing()
    rp = 'p1'
    _dev(rp, [], None, all_modules, capsys)
    _dev(rp, ['--help'], None, all_modules, capsys)
    _dev(rp, ['conf1'], SystemExit, r'cmd1,cmd2.*too few', capsys)
    _dev(rp, ['conf1', '-h'], SystemExit, r'\{cmd1,cmd2\}.*positional arguments', capsys)
    if six.PY2:
        _dev(rp, ['not_found'], None, r'no module', capsys)
    else:
        _dev(rp, ['not_found'], ModuleNotFoundError, None, capsys)
    _dev(rp, ['conf2', 'not-cmd1'], SystemExit, r'\{cmd1\}', capsys)


def test_main3():
    """Verify underscores are converted to dashes"""
    from pykern import pkconfig

    pkconfig.reset_state_for_testing()
    assert 0 == _main('p2', ['some-mod', 'some-func']), \
        'some-mod some-func: dashed module and function should work'
    assert 0 == _main('p2', ['some_mod', 'some_func']), \
        'some_mod some-func: underscored module and function should work'


def _conf(root_pkg, argv, first_time=True, default_command=False):
    import sys

    full_name = '.'.join([root_pkg, 'pkcli', argv[0]])
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
    import re
    from pykern.pkdebug import pkdp
    from pykern import pkunit

    if exc:
        with pytest.raises(exc):
            _main(root_pkg, argv)
        if not expect:
            return
    else:
        assert _main(root_pkg, argv) == 1, 'Failed to exit(1): ' + argv
    out, err = capsys.readouterr()
    if not err:
        err = out
    assert re.search(expect, err, flags=re.IGNORECASE+re.DOTALL) is not None, \
         'Looking for {} in err={}'.format(expect, err)


def _main(root_pkg, argv):
    import sys
    from pykern import pkunit, pkcli

    sys.argv[:] = ['pkcli_test']
    sys.argv.extend(argv)
    dd = str(pkunit.data_dir())
    try:
        sys.path.insert(0, dd)
        return pkcli.main(root_pkg)
    finally:
        if sys.path[0] == dd:
            sys.path.pop(0)
