# -*- coding: utf-8 -*-
"""convert to/from orgmode

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkcli
import pykern.pkcli.github
import pykern.pkcollections
import pykern.pkio
import re


_PROPERTIES = (
    # order matters, and underscore is a not a GitHub API name
    "assignees",
    "_repo",
    "html_url",
    "milestone",
    "number",
    "user",
)


def from_issues(repo, org_d="~/org"):
    """Export issues to orgmode file named ``org_d/repo.org``

    Args:
        repo (str): will add radiasoft/ if missing
        org_d (str): where to store org files [~/org]
    Returns:
        str: Name of org file created
    """
    return str(_OrgModeGen(repo, org_d).from_issues())


def test_data(repo, path):
    """Used to generate the unit test data"""
    from pykern import pkjson

    r = pykern.pkcli.github.GitHub().repo_arg(repo)
    res = _dict(r)
    res._issues = sorted(
        [_dict(i) for i in r.issues(state="open")],
        key=lambda x: x.number,
    )
    pkjson.dump_pretty(res, filename=path)


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
    _ATTRS = tuple(
        k for k in _PROPERTIES + ("body", "labels", "title") if not k.startswith("_")
    )

    _COMMENT_TAG = ":_separator_:"

    def __init__(self, repo, org_d):
        self._github = pykern.pkcli.github.GitHub()
        self._repo = self._github.repo_arg(repo)
        self._org_d = pykern.pkio.py_path(org_d)
        self._repo_name = f"{self._repo.organization['login']}/{self._repo.name}"
        self._org_path = self._org_d.join(self._repo_name.replace("/", "-") + ".org")

    def _issue_as_dict(self, issue):
        def _str(item):
            if isinstance(item, list):
                return " ".join(sorted(_str(i) for i in item))
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

        i = _dict(issue)
        return PKDict({k: _str(i[k]) for k in self._ATTRS if k in i})

    def _open_issues(self):
        """Ignores pull requests"""
        for i in self._repo.issues(state="open"):
            if not i.pull_request():
                yield i


class _OrgModeGen(_Base):
    _TITLE = re.compile(r"^(\d{4})-?(\d\d)-?(\d\d)\s*(.*)")
    _NO_DEADLINES_MARK = "ISSUES DO NOT HAVE DEADLINES AFTER THIS " + _Base._COMMENT_TAG
    _CFG = "#+STARTUP: showeverything\n#+COLUMNS: %number(Num) %ITEM %DEADLINE %TAGS\n"

    def from_issues(self):
        self._no_deadlines = None
        return self._write(self._CFG + "".join(self._issue(i) for i in self._sorted()))

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
                "".join(_property(k) for k in _PROPERTIES),
            )

        def _property(name):
            res = f":{name}:"
            if len(issue[name]) > 0:
                res += f" {issue[name]}"
            return res + "\n"

        def _tags():
            if not issue.labels:
                return ""
            return " :" + issue.labels.replace(" ", ":") + ":"

        def _title():
            res = ""
            if self._no_deadlines is None and issue.get("_deadline") is None:
                self._no_deadlines = True
                res = f"* {self._NO_DEADLINES_MARK}\n"
            return f"{res}* {issue.title or ''}{_tags()}\n"

        return _title() + pykern.pkcli.github.GitHub.indent2(
            _deadline()
            + _properties()
            + _drawer("BODY", pykern.pkcli.github.GitHub.issue_body(issue)),
        )

    def _sorted(self):
        def _dict(issue):
            res = self._issue_as_dict(issue)
            m = self._TITLE.search(res.title)
            if m:
                k = res._deadline = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                res.title = m.group(4)
            else:
                k = "9999-01-01"
            res._key = f"{k} {res.number:>010}"
            res._repo = self._repo_name
            return res

        return sorted(
            [_dict(i) for i in self._open_issues()],
            key=lambda x: x._key,
        )

    def _write(self, text):
        return pykern.pkio.write_text(self._org_path, text)


class _OrgModeParser(_Base):
    _ARRAY_ATTRS = ("assignees", "labels")
    _DEADLINE = re.compile(r"^\s*DEADLINE:\s*<(\d{4})-(\d\d)-(\d\d)")
    _HEADING = re.compile(r"^\*+\s*(.*)")
    #: orgmode indent is always 2; POSIT indent2() indents by 2
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
        pykern.pkcli.command_error("{} path={}", msg, self._org_path)

    def _next(self, expect=None):
        while self._lines:
            res = self._lines.pop(0)
            if res.startswith("#"):
                continue
            return res
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
            if self._COMMENT_TAG in m.group(1):
                continue
            self._add_issue(self._parse_issue(l, m.group(1)))

    def _parse_issue(self, line, title):
        res = PKDict()
        self._title(res, title)
        self._deadline(res)
        self._properties(res)
        self._body(res)
        return res

    def _properties(self, issue):
        for l in self._drawer("PROPERTIES"):
            m = self._PROPERTY.search(l)
            if not m:
                self._error(f"expected :property: value but got line={l}")
            issue[m.group(1)] = m.group(2).strip()

    def _title(self, issue, line):
        m = self._TAGS.search(line)
        if m:
            issue.title = m.group(1)
            issue.labels = " ".join(
                sorted(t for t in m.group(2).split(":") if len(t) > 0),
            )
        else:
            issue.title = line

    def _update(self):
        def _fix_milestone(edits):
            m = edits.get("milestone")
            if m is None:
                return edits
            res = edits.copy()
            try:
                v = self._github.milestone(self._repo, m)
            except KeyError:
                v = self._repo.create_milestone(m).number
            res.milestone = v
            return res

        def _edits(base, update):
            res = PKDict()
            for k in "assignees", "body", "labels", "milestone", "title":
                if base[k] != update[k]:
                    res[k] = update[k].split() if k in self._ARRAY_ATTRS else update[k]
                    if k == "labels":
                        y = set(res[k]) - set(x.name for x in self._repo.labels())
                        if y:
                            # labels will be created automatically, which is unlikely
                            # something we want, since labels have colors and we
                            # have a tool to create labels.
                            raise ValueError(f"non-existent labels={y}")
            return res

        res = PKDict()
        # only update issues that are still open
        for i in self._open_issues():
            try:
                u = self._issues.get(str(i.number))
                if not u:
                    continue
                e = None
                e = _edits(self._issue_as_dict(i), u)
                if e and not self._dry_run:
                    i.edit(**_fix_milestone(e))
                if e:
                    res[i.number] = e
            except Exception:
                pkdlog("edits={} error in issue={}", e, i.number)
                raise
        return res


def _dict(model):
    return pykern.pkcollections.canonicalize(model.as_dict())
