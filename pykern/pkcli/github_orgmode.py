# -*- coding: utf-8 -*-
"""convert to/from orgmode

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkcli.github
import pykern.pkio
import re

_COMMENT_TAG = ":orgmode-separator:"

_TEST_REPO = "test-pykern-github-orgmode"


def from_issues(repo, org_d="~/org"):
    """Export issues to orgmode file named ``org_d/repo.org``

    Args:
        repo (str): will add radiasoft/ if missing
        org_d (str): where to store org files [~/org]
    Returns:
        str: Name of org file created
    """
    return _OrgModeGen(repo, org_d).from_issues()


def to_issues(repo, org_d="~/org", dry_run=False):
    """Import (existing) issues from ``org_d/repo.org``

    Args:
        repo (str): will add radiasoft/ if missing
        org_d (str): where to store org files [~/org]
        dry_run (bool): whether to update issues or not
    Returns:
        str: updates made
    """
    return _OrgModeParser(repo, org_d).to_issues(dry_run)


class _Base:
    def __init__(self, repo, org_d):
        self._repo = pykern.pkcli.github.GitHub.repo_arg(repo)
        self._org_d = pykern.pkio.py_path(org_d)
        self._repo_name = f"{self._repo.organization['login']}/{self._repo.name}"
        self._org_path = self._org_d.join(self._repo_name.replace("/", "-") + ".org")


class _OrgModeGen(_Base):
    _TITLE = re.compile(r"^(\d{4})-?(\d\d)-?(\d\d)\s*(.*)")
    _PROPERTIES = (
        # order matters, and underscore is a not a GitHub API name
        "assignees",
        "_repo",
        "html_url",
        "milestone",
        "number",
        "user",
    )
    _NO_DEADLINES_MARK = "NO DEADLINES AFTER THIS " + _COMMENT_TAG

    def from_issues(self):
        self._no_deadlines = None
        return self._write(
            "#+STARTUP: showeverything\n"
            + "".join(self._issue(i) for i in self._sorted()),
        )

    def _issue(self, issue):
        def _deadline():
            d = issue.get("_deadline")
            if not d:
                return ""
            return f"DEADLINE: <{d}>\n"

        def _drawer(name, body):
            return f":{name}:\n{body}:END:\n"

        def _properties():
            return _drawer(
                "PROPERTIES",
                "".join(f":{k}: {_str(issue[k])}\n" for k in self._PROPERTIES),
            )

        def _str(item):
            if isinstance(item, list):
                return " ".join(_str(i) for i in item)
            if isinstance(item, str):
                return item
            if item is None:
                return ""
            if isinstance(item, int):
                return str(item)
            if isinstance(item, dict):
                for k in "name", "login", "title":
                    if k in item:
                        return item[k]
            raise AssertionError(f"unknown type={type(item)} item={item}")

        def _tags():
            res = ":".join(f"{l.name}" for l in issue.labels)
            if not res:
                return ""
            return f" :{res}:"

        def _title():
            res = ""
            if self._no_deadlines is None and issue.get("_deadline") is None:
                self._no_deadlines = True
                res = "* {_NO_DEADLINES_MARK}\n"
            return f"{res}* {issue.title or ''}{_tags()}\n"

        return _title() + pykern.pkcli.github.GitHub.indent2(
            _deadline()
            + _properties()
            + _drawer("BODY", pykern.pkcli.github.GitHub.issue_body(issue)),
        )

    def _sorted(self):
        def _dict(issue):
            res = pykern.pkcollections.canonicalize(issue.as_dict())
            m = self._TITLE.search(res.title)
            if m:
                k = res._deadline = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                res.title = m.group(4)
            else:
                k = "3000-00-00"
            res._key = f"{k} {res.number:010d}"
            res._repo = self._repo_name
            return res

        return sorted(
            [_dict(i) for i in self._repo.issues(state="open")],
            key=lambda x: x._key,
        )

    def _write(self, text):
        return pykern.pkio.write_text(self._org_path, text)


class _OrgModeParser(_Base):
    _DEADLINE = re.compile(r"^\s*DEADLINE:\s*<(\d{4})-(\d\d)-(\d\d)")
    _HEADING = re.compile(r"^\*+\s*(.*)")
    #: orgmode indent is always 2
    _INDENT = 2
    _PROPERTY = re.compile(r"^:(\w+):\s*(.*)")
    _TAGS = re.compile(r"^(.+)\s+(:(?:\S+:)+)\s*$")

    def to_issues(self, dry_run):
        self._dry_run = dry_run
        self._lines = pykern.pkio.read_text(self._org_path).splitlines()
        self._parse()
        return self._update()

    def _add_issue(self, issue):
        if self._repo_name != issue._repo:
            raise ValueError(
                "issue={issue.number} repo={issue._repo} does not match arg={self._repo_name}"
            )
        if issue.number in self._issues:
            self._error(
                "number={} duplicated in prev={} curr={}",
                issue.number,
                self._issues[issue.number],
                issue,
            )
        self._issues[issue.number] = issue

    def _body(self, issue):
        issue.body = "\n".join(self._drawer("BODY"))
        if len(issue.body):
            issue.body += "\n"

    def _deadline(self, issue):
        l = self._next("DEADLINE:")
        m = self._DEADLINE.search(l)
        if not m:
            # Optional
            self._lines.insert(0, l)
            return
        issue.title = f"{m.group(1)}{m.group(2)}{m.group(3)} {issue.title}"

    def _drawer(self, name):
        def _line(key):
            x = f":{key}:"
            l = self._next(x)[self._INDENT :]
            if x == l:
                return None
            if key != "END":
                self._error(f"expect={x} but got line={l}")
            return l

        _line(name)
        res = []
        while True:
            l = _line("END")
            if l is None:
                break
            res.append(l)
        return res

    def _error(self, msg):
        pkcli.command_error("{} path={}", msg, self._org_path)

    def _next(self, expect=None):
        if self._lines:
            return self._lines.pop(0)
        if expect is None:
            return None
        self._error("expect={} but got EOF", expect)

    def _parse(self):
        self._issues = PKDict()
        while True:
            l = self._next(None)
            if l is None:
                return
            m = self._HEADING.search(l)
            if not m:
                continue
            if _COMMENT_TAG in m.group(1):
                continue
            self._add_issue(self._parse_issue(l))

    def _parse_issue(self, line):
        res = PKDict()
        self._title(res, line)
        self._deadline(res)
        self._properties(res)
        self._body(res)
        return res

    def _properties(self, issue):
        for l in self._drawer("PROPERTIES"):
            m = self._PROPERTY.search(l)
            if not m:
                self._error(f"expected :property: value but got line={l}")
            issue[m.group(1)] = m.group(2)

    def _title(self, issue, line):
        m = self._TAGS.search(line)
        if m:
            issue.title = m.group(1)
            issue.labels = [t for t in m.group(2).split(":") if len(t) > 0]
        else:
            issue.title = line

    def _update(self):
        res = PKDict()
        # only update issues that are still open
        for i in self._repo.issues(state="open"):
            u = self._issues.get(i.number)
            if not u:
                continue
            e = PKDict()
            if i.title != u.title:
                e.title = u.title
            if i.body != u.body:
                e.body = u.body
            if not self._dry_run:
                i.edit(**e)
            res[i.number] = e
        return res
