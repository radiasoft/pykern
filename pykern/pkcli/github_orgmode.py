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
    "created_at",
    "html_url",
    "milestone",
    "number",
    "user",
)


def assignee_issues(user, org_d="~/org"):
    """Export issues for auth user to orgmode file named ``org_d/user.org``

    Args:
        user (str): user name to use
        org_d (str): where to store org files [~/org]
    Returns:
        str: Name of org file created
    """
    return str(_OrgModeGen(user=user, org_d=org_d).from_issues())


def from_issues(*repos, org_d="~/org"):
    """Export issues to orgmode file named ``org_d/repo.org``

    Args:
        repos (str): will add radiasoft/ if missing
        org_d (str): where to store org files [~/org]
    Returns:
        str: Name of org file created
    """
    return str(_OrgModeGen(repos=repos, org_d=org_d).from_issues())


def test_data(repo, path):
    """Used to generate the unit test data"""
    from pykern import pkjson

    if len(repo):
        r = pykern.pkcli.github.GitHub().repo_arg(repo)
        res = _dict(r)
    else:
        r = pykern.pkcli.github.GitHub().login()
        res = PKDict()
    res._issues = sorted(
        [_dict(i) for i in r.issues(state="open")],
        key=lambda x: x.number,
    )
    pkjson.dump_pretty(res, filename=path)


def to_issues(org_path, dry_run=False):
    """Import (existing) issues from ``org_d/repo.org``

    Args:
        org_path (str): org mode file
        dry_run (bool): whether to update issues or not
    Returns:
        str: updates made
    """
    return _OrgModeParser(org_path=org_path).to_issues(dry_run)


class _Base:
    _NON_PROPERTIES = ("body", "labels", "title")
    _ATTRS = tuple(k for k in _PROPERTIES + _NON_PROPERTIES if not k.startswith("_"))

    _COMMENT_TAG = ":_separator_:"

    def __init__(self, **kwargs):
        self._github = pykern.pkcli.github.GitHub()

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

    def _iter_issues(self, issues):
        for i in issues:
            if not i.pull_request():
                yield i

    def _open_issues(self, repo):
        """Ignores pull requests"""
        return self._iter_issues(repo.issues(state="open"))


class _OrgModeGen(_Base):
    _TITLE = re.compile(r"^(\d{4})-?(\d\d)-?(\d\d)\s*(.*)")
    # strict for now
    _HTML_URL = re.compile(r"https://github.com/([\.\w-]+/[\.\w-]+)/issues/\d+$")
    _NO_DEADLINES_MARK = "ISSUES DO NOT HAVE DEADLINES AFTER THIS " + _Base._COMMENT_TAG
    _CFG = "#+STARTUP: showeverything\n#+COLUMNS: %13DEADLINE %50ITEM %number(Num) %15assignees %TAGS\n"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._org_d = pykern.pkio.py_path(kwargs["org_d"])
        if "repos" in kwargs:
            if not kwargs["repos"]:
                self._error("no repos supplied")
            if len(kwargs["repos"]) == 1:
                r = self._github.repo_arg(kwargs["repos"][0])
                b = f"{r.organization['login']}-{r.name}"
                self._issues = self._open_issues(r)
            else:
                b = "issues"
                self._issues = []
                for r in kwargs["repos"]:
                    self._issues.extend(self._open_issues(self._github.repo_arg(r)))
        elif "user" in kwargs:
            b = kwargs["user"]
            self._issues = self._iter_issues(
                (
                    i.issue
                    for i in self._github.login().search_issues(
                        query=f"assignee:{b} state:open"
                    )
                ),
            )
        else:
            raise AssertionError(f"kwargs={kwargs} invalid")
        self._org_path = self._org_d.join(f"{b}.org")

    def from_issues(self):
        self._no_deadlines = None
        return self._write(self._CFG + "".join(self._issue(i) for i in self._sorted()))

    def _error(self, msg):
        pykern.pkcli.command_error("{} org_d={}", msg, self._org_d)

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
        repo_name_cache = PKDict()

        def _dict(issue):
            res = self._issue_as_dict(issue)
            m = self._TITLE.search(res.title)
            if m:
                k = res._deadline = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                res.title = m.group(4)
            else:
                k = "9999-01-01"
            # created_at makes deterministic
            res._key = f"{k} {res.number:>010} {res.created_at}"
            res._repo = _repo_name(res.html_url)
            return res

        def _repo_name(url):
            return repo_name_cache.pksetdefault(url, lambda: _repo_name_calc(url))[url]

        def _repo_name_calc(url):
            m = self._HTML_URL.search(url)
            if not m:
                raise ValueError(f"html_url={url} invalid format")
            return m.group(1)

        return sorted([_dict(i) for i in self._issues], key=lambda x: x._key)

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

    def __init__(self, org_path):
        super().__init__()
        self._org_path = pykern.pkio.py_path(org_path)

    def to_issues(self, dry_run):
        self._dry_run = dry_run
        self._lines = pykern.pkio.read_text(self._org_path).splitlines()
        self._parse()
        return self._update()

    def _add_issue(self, issue):
        i = self._repos.setdefault(issue._repo, PKDict())
        if issue.number in i:
            self._error(
                f"number={issue.number} duplicated in prev={i[issue.number]} curr={issue}",
            )
        i[issue.number] = issue

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
        self._error(f"expect={expect} but got EOF")

    def _parse(self):
        self._repos = PKDict()
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
            issue.labels = ""

    def _update(self):
        res = PKDict()
        for k in sorted(self._repos):
            e = self._update_repo(self._github.repo_arg(k), self._repos[k])
            if e:
                res[k] = e
        return res

    def _update_repo(self, repo, issues):
        def _fix_milestone(edits):
            m = edits.get("milestone")
            if m is None:
                return edits
            res = edits.copy()
            try:
                v = self._github.milestone(repo, m)
            except KeyError:
                v = repo.create_milestone(m).number
            res.milestone = v
            return res

        def _edits(base, update):
            res = PKDict()
            for k in "assignees", "body", "labels", "milestone", "title":
                if base[k] != update[k]:
                    res[k] = (
                        sorted(update[k].split())
                        if k in self._ARRAY_ATTRS
                        else update[k]
                    )
                    if k == "labels":
                        y = set(res[k]) - set(x.name for x in repo.labels())
                        if y:
                            # labels will be created automatically, which is unlikely
                            # something we want, since labels have colors and we
                            # have a tool to create labels.
                            raise ValueError(f"non-existent labels={y}")
            return res

        res = PKDict()
        # only update issues that are still open
        for i in self._open_issues(repo):
            try:
                u = issues.get(str(i.number))
                if not u:
                    continue
                e = None
                e = _edits(self._issue_as_dict(i), u)
                if e and not self._dry_run:
                    i.edit(**_fix_milestone(e))
                if e:
                    res[i.number] = e
            except Exception:
                pkdlog("edits={} error in issue={}", e, f"{repo}#{i.number}")
                raise
        return res


def _dict(model):
    return pykern.pkcollections.canonicalize(model.as_dict())
