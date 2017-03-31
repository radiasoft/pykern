# -*- coding: utf-8 -*-
u"""test pykern.pkcli.sim

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import os


def test_init_and_run(monkeypatch):
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcli import sim
    from pykern.pkcli import rsmanifest
    import netrc
    import os
    import os.path
    import re
    import subprocess

    cfg = pkunit.cfg.aux.get('sim_test', None)
    if not cfg:
        # No testing if there's no auth config
        return
    u, p = cfg.split(' ')
    monkeypatch.setattr(netrc, 'netrc', _netrc)
    _netrc.result = (u, None, p)
    with pkunit.save_chdir_work(is_pkunit_prefix=True):
        f = 'out/log'
        expect_code = pkunit.random_alpha()
        pkio.write_text('run.sh', 'echo {}>{}'.format(expect_code, f))
        rsmanifest.pkunit_setup()
        sim._cmd_init()
        sim._cmd_run()
        x = subprocess.check_output(['git', 'remote', '-v']),
        m = re.search(r'/(sim-sim_work-\d+-\d+)\.git', x[0])
        repo = m.group(1)
        pkunit.pkok(m, 'git remote: failed: {}', x)
        pkunit.pkeq(expect_code, pkio.read_text('out/log').rstrip())
        os.remove('run.sh')
        sim._cmd_pip('djson')
        pkio.write_text('run.py', 'import djson'.format(expect_code, f))
        sim._cmd_run()
        sim._git_api_request(
            'delete',
            'repositories/{user}/{repo}',
            dict(repo=repo),
        )

class _netrc(object):
    def authenticators(self, *args, **kwargs):
        return self.result
