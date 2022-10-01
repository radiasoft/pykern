# -*- coding: utf-8 -*-
"""test github_orgmode

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import re
import pytest


def test_from_issues(monkeypatch):
    from pykern import pkunit, pkjson, pkio
    from pykern.pkcli import github_orgmode
    from pykern.pkcli.github import GitHub
    from pykern.pkdebug import pkdp
    from pykern.pkcollections import PKDict

    class _Issue(PKDict):
        def as_dict(self):
            return self

        def edit(self, **kwargs):
            self.setdefault("edits", PKDict())[number] = PKDict(kwargs)

    class _Repo(PKDict):
        def __init__(self, repo, state):
            self.pkupdate(pkjson.load_any(pkio.read_text("repo.json")))
            self._issues = [_Issue(v) for v in self._issues]
            state.repo = self

        def issues(self, *args, **kwargs):
            return self._issues

    state = PKDict()
    monkeypatch.setattr(GitHub, "repo_arg", lambda x: _Repo(x, state))
    for d in pkunit.case_dirs("from_issues"):
        github_orgmode.from_issues("ignored", org_d=d)
