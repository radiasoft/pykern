# -*- coding: utf-8 -*-
"""convert to/from orgmode

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkcli.github


def issues_as_org(repo):
    """Export issues to orgmode files

    Args:
        repo (str): will add radiasoft/ if missing
    Returns:
        str: orgmode text
    """
    return _OrgModeGen().from_github(repo)


def org_to_issues(path):
    """Import (existing) issues for orgmode `path`

    Args:
        path (str): format must match `issues_as_orgmode`
    Returns:
        str: updates made
    """
    return _OrgModeParser().to_github(path)


class _OrgModeGen:
    _TITLE = re.compile(r"^(\d{4})-?(\d\d)-?(\d\d)\s*(.*)")
    _PROPERTIES = (
        # order matters, and underscore is a not a GitHub API name
        "_repo",
        "html_url",
        "milestone",
        "number",
        "user",
    )
    _NO_DEADLINES_MARK = "NO DEADLINES AFTER THIS"

    def from_github(self, repo):
        self._repo = pykern.pkcli.github.GitHub.repo_arg(repo)
        self._no_deadlines = None
        return "#+STARTUP: showeverything\n" + "".join(
            self._issue(i) for i in self._sorted()
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

        return _title() + _indent2(
            _deadline() + _properties() + _drawer("BODY", _issue_body(issue)),
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
            res._repo = f"{self._repo.organization['login']}/{self._repo.name}"
            return res

        return sorted(
            [_dict(i) for i in self._repo.issues(state="open")],
            key=lambda x: x._key,
        )


class _OrgModeParser:
    _DEADLINE = re.compile(r"^\s*DEADLINE:\s*<(\d{4})-(\d\d)-(\d\d)")
    _HEADING = re.compile(r"^\*\s*(.*)")
    #: orgmode indent is always 2
    _INDENT = 2
    _PROPERTY = re.compile(r"^:(\w+):\s*(.*)")
    _TAGS = re.compile(r"^(.+)\s+(:(?:\S+:)+)\s*$")

    def to_github(self, path):
        self._parse(path)
        return self._repos

    def _add_issue(self, issue):
        r = self._repos.setdefault(issue._repo, PKDict())
        if issue.number in r:
            self._error(
                "number={} duplicated in prev={} curr={}",
                issue.number,
                r[issue.number],
                issue,
            )
        r[issue.number] = issue

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
        pkcli.command_error("{} path={}", msg, self._path)

    def _next(self, expect=None):
        if self._lines:
            return self._lines.pop(0)
        if expect is None:
            return None
        self._error("expect={} but got EOF", expect)

    def _parse(self, path):
        self._path = path
        self._repos = PKDict()
        self._lines = pkio.read_text(path).splitlines()
        while True:
            l = self._next(None)
            if l is None:
                return
            m = self._HEADING.search(l)
            if not m:
                continue
            if m.group(1) == _OrgModeGen._NO_DEADLINES_MARK:
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
