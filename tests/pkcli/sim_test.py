# -*- coding: utf-8 -*-
u"""test pykern.pkcli.sim

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import os


def test_init_and_run():
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcli import sim
    from pykern.pkcli import rsmanifest
    import os
    import os.path
    import re
    import subprocess

    cfg = pkunit.cfg.aux.get('sim_test', None)
    if not cfg:
        # No testing if there's no auth config
        return
    u, p = cfg.split(' ')
    n = os.path.expanduser('~/.netrc')
    assert not os.path.exists(n), \
        '{}: netrc must not exist'.format(n)
    with open(n, 'w') as f:
        f.write(
            'machine {}\nlogin {}\npassword {}\n'.format(
                sim._GIT_REMOTE, u, p,
            ),
        )
    os.chmod(n, 0600)
    with pkunit.save_chdir_work():
        f = 'out/log'
        expect_code = pkunit.random_alpha()
        pkio.write_text('run.sh', 'echo {}>{}'.format(expect_code, f))
        rsmanifest.pkunit_setup()
        sim._cmd_init()
        sim._cmd_run()
        x = subprocess.check_output(['git', 'remote', '-v']),
        m = re.search(r'/(sim-sim_work-\d+-\d+)\.git', x[0])
        pkunit.pkok(m, 'git remote: failed: {}', x)
        pkunit.pkeq(expect_code, pkio.read_text('out/log').rstrip())
        sim._git_api_request(
            'delete',
            'repositories/{user}/{repo}',
            dict(
                repo=m.group(1),
            ),
        )
