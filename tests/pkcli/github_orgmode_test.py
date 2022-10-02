# -*- coding: utf-8 -*-
"""test github_orgmode

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import re
import pytest


def test_issues(monkeypatch):
    from pykern import pkunit, pkjson, pkio
    from pykern.pkcli import github_orgmode
    from pykern.pkcli import github
    from pykern.pkdebug import pkdp
    from pykern.pkcollections import PKDict

    class _MockGitHub(github.GitHub):
        def repo_arg(self, repo):
            return _MockRepo(repo)

    class _MockIssue(PKDict):
        def as_dict(self):
            return self

        def edit(self, **kwargs):
            pass

        def pull_request(self, **kwargs):
            return self.get("pull_request_urls")

    class _MockRepo(PKDict):
        def __init__(self, repo):
            self._case = repo
            self.pkupdate(pkjson.load_any(pkio.read_text("repo.json")))
            self._issues = [_MockIssue(v) for v in self._issues]

        def issues(self, *args, **kwargs):
            return self._issues

        def milestones(self, *args, **kwargs):
            return iter(self._milestones)

    monkeypatch.setattr(github, "GitHub", _MockGitHub)
    for d in pkunit.case_dirs():
        m = re.sub("-.+", "", d.purebasename)
        # repo name is ignored, just used for debugging
        pkjson.dump_pretty(
            getattr(github_orgmode, m)(d.purebasename, org_d=d),
            filename="res.json",
        )
