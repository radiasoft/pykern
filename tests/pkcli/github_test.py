"""test github

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import pytest
import os
import re

pytestmark = pytest.mark.skipif(
    (
        bool(os.environ.get("PYKERN_TEST_CI"))
        or not bool(os.environ.get("PYKERN_PKCLI_GITHUB_PASSWORD"))
    ),
    reason="CI pipelines use shared IPs so gets rate limited too easily",
)


def test_repo_no_wiki():
    from pykern import pkconfig
    from pykern.pkdebug import pkdlog, pkdp, pkdc, pkdexc

    pkconfig.reset_state_for_testing(
        {
            "PYKERN_PKCLI_GITHUB_TEST_MODE": "1",
            "PYKERN_PKCLI_GITHUB_API_PAUSE_SECONDS": "0",
        }
    )
    import os
    from pykern.pkcli import github
    from pykern import pkunit
    from pykern import pkio
    import subprocess

    with pkunit.save_chdir_work():
        github.backup("radiasoft")
        for n, e in PKDict(
            {
                "radiasoft-test-pykern-github": 1,
                "radiasoft-test-pykern-github-no-wiki": 0,
                "biviosoftware-test-pykern-github-no-wiki": 0,
            }
        ).items():
            a = len(pkio.sorted_glob(f"**/{n}.wiki.git/config"))
            pkunit.pkeq(e, a, "repo={} expected={} != actual={}", n, e, a)


def test_backup():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing(
        {
            "PYKERN_PKCLI_GITHUB_TEST_MODE": "1",
            "PYKERN_PKCLI_GITHUB_API_PAUSE_SECONDS": "0",
        }
    )
    from pykern.pkcli import github
    from pykern import pkunit
    from pykern import pkio

    with pkunit.save_chdir_work():
        github.backup("radiasoft")
        github.backup("radiasoft")
        x = pkio.sorted_glob("*/radiasoft-test-pykern-github.git/config")
        pkunit.pkeq(2, len(x))
        pkunit.pkeq(2, x[0].stat().nlink)
        x = [
            os.popen(f"tar tJf {y}").read()
            for y in pkio.sorted_glob("*/radiasoft-test-pykern-github.issues.txz")
        ]
        pkunit.pkeq(2, len(x))
        pkunit.pkeq(x[0], x[1])


def test_issue_start():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing(
        {
            "PYKERN_PKCLI_GITHUB_TEST_MODE": "1",
            "PYKERN_PKCLI_GITHUB_API_PAUSE_SECONDS": "0",
        }
    )
    from pykern.pkcli import github
    from pykern import pkunit

    r = _close_issues()
    github.issue_pending_alpha(_test_repo())
    with pkunit.pkexcept("prior release"):
        github.issue_start_alpha(_test_repo())

    def _commit(repo, full_name, issues):
        issues.append(_create_commit(repo, full_name=full_name))
        a = github.issue_update_alpha_pending(_test_repo())
        pkunit.pkre(issues[-1].title, a)
        pkunit.pkre(issues[-1].link, a)

    issues = []
    _commit(r, False, issues)
    _commit(r, True, issues)

    m = None
    for x in (
        github.issue_start_alpha,
        github.issue_start_beta,
        github.issue_start_prod,
    ):
        a = x(_test_repo())
        for i in issues:
            pkunit.pkre(i.link, a)
            pkunit.pkre(i.title, a)

        if m:
            pkunit.pkre(m.group(1), a)
        m = re.search(r"(?:Started|Created) (#\d+)", a)
        assert m
        r.issue(m.group(1)[1:]).close()
    github.issue_pending_alpha(_test_repo())
    a = github.issue_update_alpha_pending(_test_repo())
    pkunit.pkeq("", a)


def test_labels():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing(
        {
            "PYKERN_PKCLI_GITHUB_TEST_MODE": "1",
            "PYKERN_PKCLI_GITHUB_API_PAUSE_SECONDS": "0",
        }
    )
    from pykern.pkcli import github
    from pykern import pkunit

    github.labels(_test_repo())
    github.labels(_test_repo(), clear=True)


def test_list_repos():
    from pykern.pkcli import github
    from pykern import pkunit

    r = github.list_repos("radiasoft")
    pkunit.pkok("pykern" in r, "pykern missing in actual={}", r)


def _close_issues():
    from pykern.pkcli import github

    r = github.GitHub().repo(_test_repo())
    for i in r.issues(state="open"):
        if re.search(" release ", i.title, flags=re.IGNORECASE):
            i.close()
    return r


def _create_commit(repo, full_name=False):
    from pykern import pkcompat
    from pykern import pkunit, util

    t = util.random_base62()
    i = repo.create_issue(title=t + " for github_test", body="n/a")
    m = repo.readme()
    b = pkcompat.from_bytes(m.decoded)
    x = re.sub(r"(?<=github_test)=([^\n]+)", t, b)
    if b == x:
        b += f"github_test={t}\n"
    r = f'{repo if full_name else ""}#{i.number}'
    m.update(f"fix {r} for github_test", pkcompat.to_bytes(b))
    return PKDict(link=f"{repo}#{i.number}", title=t)


def _test_repo():
    from pykern.pkcli import github

    t = github._TEST_REPOS[0]
    return "/".join((t.org, t.name))
