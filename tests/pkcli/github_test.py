# -*- coding: utf-8 -*-
u"""test github

:copyright: Copyright (c) 2019 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import os
import re

pytestmark = pytest.mark.skipif(
    bool(os.environ.get('TRAVIS')),
    reason='travis uses shared IPs so gets rate limited too easily',
)

def test_backup():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing({
        'PYKERN_PKCLI_GITHUB_TEST_MODE': '1',
        'PYKERN_PKCLI_GITHUB_API_PAUSE_SECONDS': '0',
    })
    from pykern.pkcli import github
    from pykern import pkunit
    from pykern import pkio

    with pkunit.save_chdir_work():
        github.backup()
        github.backup()


def test_issue_start():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing({
        'PYKERN_PKCLI_GITHUB_TEST_MODE': '1',
        'PYKERN_PKCLI_GITHUB_API_PAUSE_SECONDS': '0',
    })
    from pykern.pkcli import github
    from pykern import pkunit
    from pykern import pkio

    r = _close_issues()
    github.issue_pending_alpha(github._TEST_REPO)
    i, t = _create_commit(r)
    a = github.issue_update_alpha_pending(github._TEST_REPO)
    pkunit.pkre(i, a)
    pkunit.pkre(t, a)
    m = None
    for x in (
        github.issue_start_alpha,
        github.issue_start_beta,
        github.issue_start_prod,
    ):
        a = x(github._TEST_REPO)
        pkunit.pkre(i, a)
        pkunit.pkre(t, a)
        if m:
            pkunit.pkre(m.group(1), a)
        m = re.search(r'(?:Started|Created) (#\d+)', a)
        assert m
        r.issue(m.group(1)[1:]).close()


def _close_issues():
    from pykern.pkcli import github

    r = github._GitHub().repo(github._TEST_REPO)
    for i in r.issues(state='open'):
        if re.search(' release ', i.title, flags=re.IGNORECASE):
            i.close()
    return r


def _create_commit(repo):
    from pykern import pkcompat
    from pykern import pkunit

    t = pkunit.random_alpha()
    i = repo.create_issue(title=t + ' for github_test', body='n/a');
    m = repo.readme()
    b = pkcompat.from_bytes(m.decoded)
    x = re.sub(r'(?<=github_test)=([^\n]+)', t, b)
    if b == x:
        b += f'github_test={t}\n'
    m.update(f'fix #{i.number} for github_test', pkcompat.to_bytes(b))
    return (f'#{i.number}', t)
