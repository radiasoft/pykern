# -*- coding: utf-8 -*-
"""test github_orgmode

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
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
            return _MockRepoOrGitHub3(repo)

        def login(self):
            return _MockRepoOrGitHub3("")

    class _MockIssue(PKDict):
        def as_dict(self):
            return self

        def edit(self, **kwargs):
            pass

        @property
        def issue(self):
            """has to be a property to avoid recursion on canonicalize"""
            return self

        def pull_request(self, **kwargs):
            return self.get("pull_request_urls")

    class _MockRepoOrGitHub3(PKDict):
        def __init__(self, repo):
            self._case = repo
            self.pkupdate(pkjson.load_any(pkio.read_text("repo.json")))

        def issues(self, *args, **kwargs):
            return [_MockIssue(v) for v in self._issues]

        def labels(self, *args, **kwargs):
            return self._labels

        def me(self):
            # it's only used for the output file
            return PKDict(login="assignee_issues")

        def milestones(self, *args, **kwargs):
            return self._milestones

        def search_issues(self, *args, **kwargs):
            return [_MockIssue(v) for v in self._issues]

    monkeypatch.setattr(github, "GitHub", _MockGitHub)
    for d in pkunit.case_dirs():
        m = re.sub("-.+", "", d.purebasename)
        # repo name is ignored, just used for debugging
        if m == "from_issues":
            a = github_orgmode.from_issues(d.purebasename, org_d=d)
        elif m == "to_issues":
            a = github_orgmode.to_issues(org_path=d.join(f"{d.purebasename}.org"))
        elif m == "assignee_issues":
            a = github_orgmode.assignee_issues(user="assignee_issues", org_d=d)
        else:
            pkunit.pkfail("case={} unknown method", d.purebasename)
        pkjson.dump_pretty(a, filename="res.json")
