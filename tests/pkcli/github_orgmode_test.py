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
            pass

    class _Repo(PKDict):
        def __init__(self, repo):
            self._case = repo
            self.pkupdate(pkjson.load_any(pkio.read_text("repo.json")))
            self._issues = [_Issue(v) for v in self._issues]

        def issues(self, *args, **kwargs):
            return self._issues

    monkeypatch.setattr(GitHub, "repo_arg", lambda x: _Repo(x))
    for d in pkunit.case_dirs():
        m = re.sub("-.+", "", d.purebasename)
        # repo name is ignored, just used for debugging
        pkjson.dump_pretty(
            getattr(github_orgmode, m)(d.purebasename, org_d=d),
            filename="res.json",
        )
