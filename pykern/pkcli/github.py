# -*- coding: utf-8 -*-
"""run github backups and restores

:copyright: Copyright (c) 2013-2018 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcli
from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdc, pkdexc
import datetime
import github3
import github3.exceptions
import glob
import json
import pykern.pkcollections
import os
import os.path
import re
import subprocess
import sys
import time


_GITHUB_HOST = "github.com"
_GITHUB_URI = "https://" + _GITHUB_HOST
_GITHUB_API = "https://api." + _GITHUB_HOST
_WIKI_ERROR_OK = (
    r"fatal: remote error: access denied or repository not exported: .*wiki.git"
)
_RE_TYPE = type(re.compile(""))
_MAX_TRIES = 3
_TEST_REPO = "test-pykern-github"
_TXZ = ".txz"
_LIST_ARG_SEP_RE = re.compile(r"[\s,:;]+")


def backup():
    """Backs up all github repositories associated with user into pwd

    Creates timestamped directory, and purges directories older than cfg.keep_days

    Note: backups are incremental in case of repositories to save
    space. Hard-linking is used between "keep_dates". The assumption
    here is that the github backup is actually copied to a backup
    server.
    """
    try:
        _Backup()
    except subprocess.CalledProcessError as e:
        if hasattr(e, "output"):
            pkdlog("ERROR: Backup {}", e.output)
    pkdlog("DONE")


def ci_check(repo, branch=None):
    def _branch(r, name, reraise=True):
        try:
            return r.branch(name=name)
        except github3.exceptions.NotFoundError:
            if reraise:
                raise
            return None

    r = _repo_arg(repo)
    b = (
        _branch(r, branch)
        if branch
        else _branch(r, "master", False) or _branch(r, "main")
    )
    s = b.commit.sha
    c = [c.conclusion for c in b.commit.check_runs()]
    i = f"branch={b.name} sha={s}"
    if not c:
        pkcli.command_error(f"{i} No workflow runs for commit")
    if c[0] != "success":
        pkcli.command_error(f"{i} Unsuccessful conclusion={c}")
    return f"{i} Passed CI"


def collaborators(org, filename, affiliation="outside", private=True):
    """Lists direct repos to which user has access and is not a team member

    Configured user must be an owner

    Args:
        org (str): GitHub organization
        affiliation (str): all, direct, outside
    """
    from pykern import pkyaml

    g = _GitHub().login()
    o = g.organization(org)
    res = dict()
    for r in o.repositories():
        if r.private == private:
            x = [str(c.login) for c in r.collaborators(affiliation=affiliation)]
            if x:
                res[str(r.name)] = x
    pkyaml.dump_pretty(res, filename)


def create_issue(repo, title, body="", assignees=None, labels=None, milestone=None):

    r = _repo_arg(repo)
    a = PKDict()
    if milestone:
        try:
            m = int(milestone)
            assert m > 0
            a.milestone = str(m)
        except Exception:
            a.milestone = get_milestone(r, title=milestone)

    def _list_arg(arg):
        if isinstance(arg, str):
            return _LIST_ARG_SEP_RE.split(arg)
        return arg

    if labels:
        a.labels = _list_arg(labels)
    if assignees:
        a.assignees = _list_arg(assignees)
    return r.create_issue(
        title=title,
        body=body,
        **a,
    ).number


def create_milestone(repo, title, description="", due_on=None):
    a = PKDict()
    if due_on:
        # GitHub seems to always create at 08:00:00Z in any zone
        # so just have the user put in the time.
        a.due_on = due_on + "T08:00:00Z"
    if description:
        a.description = description
    return (
        _repo_arg(repo)
        .create_milestone(
            title=title,
            **a,
        )
        .number
    )


def get_milestone(repo, title):
    t = title.lower()
    for m in _repo_arg(repo).milestones(state="open"):
        if m.title.lower() == t:
            return m.number
    raise KeyError(f"milestone={title} not found")


def issue_pending_alpha(repo):
    """Create "Alpha Release [pending]" issue

    This should be created after the current alpha completes.
    """
    r, a = _alpha_pending(repo, assert_exists=False)
    if a:
        return f"#{a.number} {a.title} already exists"
    i = _create_release_issue(r, _release_title("Alpha", pending=True), "")
    return f"Created #{i.number}"


def issue_start_alpha(repo):
    r, a = _alpha_pending(repo)
    if not a.body:
        raise ValueError("no new issues before prior release so no need to start alpha")
    for i in r.issues(state="open"):
        if i.number != a.number and re.search(
            r"^alpha release \d+", i.title, flags=re.IGNORECASE
        ):
            _assert_closed(i)
            # does not get here
    a.edit(title=_release_title("Alpha"))
    return f"Started #{a.number} and {issue_pending_alpha(repo)}" + (
        a.body if cfg.test_mode else ""
    )


def issue_start_beta(repo):
    return _promote(repo, "Alpha", "Beta")


def issue_start_prod(repo):
    return _promote(repo, "Beta", "Prod")


def issue_update_alpha_pending(repo):
    r, a = _alpha_pending(repo)
    res = ""
    b = a.body or ""
    # the loop below picks up the pending so don't add b to p
    p = []
    for i in r.issues(state="all", sort="updated", direction="desc"):
        if re.search(f"^alpha release", i.title, flags=re.IGNORECASE):
            p.append(i.body or "")
            # somewhat arbitrary
            if len(p) > 10:
                break
    p = "\n".join(p)
    g = _GitHub()
    g.login()
    for c in r.commits(
        sha="master",
        since=datetime.datetime.now() - datetime.timedelta(minutes=24 * 60),
    ):
        m = re.search(r"([-\w]+/[-\w]+)?#(\d+)", c.message)
        if not m:
            res += f"commit={c.sha} missing #NN in message={c.message}, ignoring\n"
            continue
        n = m.group(1) or r.full_name
        try:
            i = g.repo(n).issue(m.group(2))
        except Exception as e:
            res += f"Issue {n}#{m.group(2)} exception={e}\n"
            continue
        z = f"\\b{n}#{i.number}"
        if n == r.full_name:
            z += "|#{i.number}"
        y = re.compile("(?:" + z + r")\b")
        if y.search(p):
            # don't bother to note already included commits; also makes
            # unit test simpler
            continue
        if b and not b.endswith("\n"):
            b += "\n"
        x = f"- {i.title} {n}#{i.number}\n"
        b += x
        a.edit(body=b)
        res += f"Updated #{a.number} with: {x}"
    return res


def issues_as_csv(repo):
    """Export issues as CSV

    Args:
        repo (str): will add radiasoft/ if missing
    """
    cols = (
        "number",
        "title",
        "assignees",
        "comments_count",
        "comments_url",
        "created_at",
        "events_url",
        "html_url",
        "id",
        "labels_url",
        "locked",
        "milestone",
        "original_labels",
        "pull_request_urls",
        "state",
        "updated_at",
        "user",
        "body",
    )

    def _s(v):
        if v is None:
            return ""
        if isinstance(v, list):
            return ",".join([_s(x) for x in v])
        return str(getattr(v, "name", v))

    specials = set("\n,")

    def _c(i, c):
        v = _s(getattr(i, c)).replace('"', '""')
        if any(c in specials for c in v):
            return f'"{v}"'
        return v

    r = _repo_arg(repo)
    n = r.name + ".csv"
    with open(n, mode="w") as f:

        def _write(v):
            # Need custom csv, because utf8 not handled by py2's csv
            f.write(",".join(v) + "\r\n")

        _write(cols)
        for i in r.issues(state="open"):
            _write([_c(i, c) for c in cols])
    return n


def issues_as_orgmode(repo):
    """Export issues for orgmode

    Args:
        repo (str): will add radiasoft/ if missing
    Returns:
        str: orgmode text
    """
    return _OrgModeGen().from_github(repo)


def issues_update_from_orgmode(path):
    """Import (existine) issues for orgmode `path`

    Args:
        path (str): format must match `issues_as_orgmode`
    Returns:
        str: updates made
    """
    return _OrgModeParse().to_github(path)


def labels(repo, clear=False):
    """Setup the RadiaSoft labels for ``repo``.

    Will add "radiasoft/" to the name if it is missing.

    Args:
        repo (str): will add https://github.com/radiasoft if missing
        clear (bool): if True, clear all existing labels
    """
    r = _repo_arg(repo)
    if clear:
        for l in r.labels():
            l.delete()
    for x in (
        ("customer", "0e8a16"),
        ("devops", "84b6eb"),
        ("doc", "84b6eb"),
        ("question", "84b6eb"),
        ("release", "84b6eb"),
        ("sw", "84b6eb"),
        ("test", "84b6eb"),
        ("user", "0e8a16"),
    ):
        try:
            r.create_label(*x)
        except github3.exceptions.UnprocessableEntity:
            # 422 Validation Failed: happens because already exists
            pass


def list_repos(organization):
    """Lists repos for organization

    Args:
        organization (str): GitHub organization
    """
    g = _GitHub().login()
    o = g.organization(organization)
    res = []
    for r in o.repositories():
        if not r.fork:
            res.append(str(r.name))
    return sorted(res)


def restore(git_txz):
    """Restores the git directory (only) to a new directory with the .git.txz suffix"""
    m = re.search(r"(([^/]+)\.git)\.txz$", git_txz)
    if not m:
        raise ValueError(git_txz, ": does not end in .git.txz")
    git_txz = pkio.py_path(git_txz)
    d = m.group(2)
    pkdc("restore: {}", d)
    g = m.group(1)
    with pkio.save_chdir(d, mkdir=True):
        _shell(["tar", "xJf", str(git_txz)])
        os.rename(g, ".git")
        _shell(["git", "config", "core.bare", "false"])
        _shell(["git", "config", "core.logallrefupdates", "true"])
        _shell(["git", "checkout"])


class _GitHub(object):
    def __init__(self):
        self._github = None

    def login(self):
        self._github = (
            github3.GitHub(username=cfg.user, password=cfg.password)
            if cfg.password
            else github3.GitHub()
        )
        return self._github

    def repo(self, repo):
        if not self._github:
            self.login()
        a = repo.split("/")
        if len(a) == 1:
            a.insert(0, "radiasoft")
        return self._github.repository(*a)

    def _subscriptions(self):
        if cfg.test_mode:
            return [self._github.repository("radiasoft", _TEST_REPO)]
        return self._github.subscriptions()

    def _iter_subscriptions(self):
        """Returns a list so that we don't get rate limited at startup."""
        self.login()
        res = []
        for r in self._subscriptions():
            if cfg.exclude_re and cfg.exclude_re.search(r.full_name):
                pkdc("exclude: {}", r.full_name)
                continue
            res.append(r)
        return res


class _Backup(_GitHub):
    def __init__(self):
        # POSIT: timestamps are sorted in _clone()
        self._date_d = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        with pkio.save_chdir(self._date_d, mkdir=True):
            sleep = 0
            for r in _try(self._iter_subscriptions):
                pkdlog("{}: begin", r.full_name)
                self._repo(r)
        self._purge()

    def _extract_backup(self, backup):
        pkdc("updating from {}", backup)
        _shell(["tar", "xJf", str(backup)])

    def _prev_backup(self, base, ext):
        # POSIT: timestamp Backup
        b = pkio.sorted_glob(f"../*/{base}{ext}")
        return b[-1] if b else []

    def _purge(self):
        expires = datetime.datetime.utcnow() - cfg.keep_days
        for d in pkio.sorted_glob("[0-9]" * len(self._date_d)):
            t = datetime.datetime.utcfromtimestamp(d.stat().mtime)
            if t < expires:
                pkio.unchecked_remove(d)

    def _repo(self, repo):
        fn = repo.full_name
        bd = re.sub("/", "-", fn)

        def _clone(suffix):
            base = bd + suffix
            prev = self._prev_backup(base, ext="")
            if not prev:
                _shell(
                    (
                        "git",
                        "clone",
                        "--quiet",
                        "--mirror",
                        _GITHUB_URI + "/" + fn + suffix,
                        base,
                    ),
                )
                return
            _shell(("cp", "--archive", "--link", str(prev), "./"))
            with pkio.save_chdir(base):
                _shell(["git", "remote", "update"])

        def _issues():
            def _issue(i, d):
                j = _trim_body(i)
                j["comments"] = [_trim_body(c) for c in i.comments()]
                p = i.pull_request()
                if p:
                    j["review_comments"] = [_trim_body(c) for c in p.review_comments()]
                pkjson.dump_pretty(j, filename=d.join(str(i.number) + ".json"))

            if not repo.has_issues:
                return
            base = bd + ".issues"
            prev = self._prev_backup(base, ext=_TXZ)
            d = pkio.mkdir_parent(base)
            k = PKDict(state="all")
            if prev:
                self._extract_backup(prev)
                k.since = datetime.datetime.now() - datetime.timedelta(days=7)
            for i in _try(lambda: list(repo.issues(**k))):
                _try(lambda: _issue(i, d))
            _tar(base)

        def _json(gen, suffix):
            base = bd + suffix
            with open(base, "wt") as f:
                sep = "[\n"
                for i in gen:
                    f.write(sep)
                    f.write(pkjson.dump_pretty(_trim_body(i)))
                    sep = ",\n"
                if "[" in sep:
                    # Empty iteration
                    f.write(sep)
                f.write("]\n")
            _shell(["xz", base])

        def _tar(base):
            _shell(["tar", "cJf", base + _TXZ, base])
            pkio.unchecked_remove(base)

        def _trim_body(o):
            res = o.as_dict()
            try:
                # github returns three formats, and we only want source
                del res["body_text"]
                del res["body_html"]
            except KeyError:
                pass
            return res

        try:
            # backup the code first; should be fast
            _clone(".git")
            _issues()
            if repo.has_wiki:
                try:
                    _clone(".wiki.git")
                except subprocess.CalledProcessError as e:
                    if not re.search(_WIKI_ERROR_OK, str(e.output)):
                        raise
            _try(lambda: _json(repo.comments(), ".comments"))
            # TODO(robnagler) releases, packages, projects
            return
        except Exception as e:
            pkdlog(
                "ERROR: {} {} {} {} {}",
                fn,
                type(e),
                e,
                getattr(e, "output", None),
                pkdexc(),
            )


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
        self._repo = _repo_arg(repo)
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


class OrgModeParse:
    _HEADING = re.compile(r"^\*\s*(.*)")
    #: orgmode indent is always 2
    _INDENT = 2
    _PROPERTY = re.compile("r^:(\w+):\s*(.*)")
    _TAGS = re.compile(r"^(.+)\s+(:(?:\S+:)+)\s*$")

    def update(self, path):
        self._parse(path)

    def _add_issue(issue):
        r = self._repos.get(issue._repo) or PKDict()
        if issue.number in r:
            self._error("number={} duplicated in prev={} curr={}", issue.number, r[issue.number], issue)
        r[issue.number] = issue

    def _body(self, issue):
        issue.body = "\n".join(self._drawer("BODY"))
        if len(issue.body):
            issue.body += "\n"

    def _drawer(self, name):
        def _line(key):
            x = f":{key}:"
            l = self._next(x)[_INDENT:]
            if x == l:
                return None
            if name != "END":
                self._error("expect={} but got line={}", x, l)
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
        pkcli.command_error(f"{msg} path={}", self._path)

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
        self._title(res, l)
        self._deadline(res)
        self._properties(res)
        self._body(res)
        return res

    def _properties(self, issue):
        for l in self._drawer("PROPERTIES"):
            m = self._PROPERTY.search(l)
            if not m:
                self._error("expected :property: value but got line={}", l)
            issue[m.group(1)] = m.group(2)

    def _title(self, issue, line):
        m = self._TAGS.search(line)
        if m:
            issue.title = m.group(1)
            issue.labels = [t for t in m.group(2).split(":") if len(t) > 0]
        else:
            issue.title = line


def _alpha_pending(repo, assert_exists=True):
    r = _GitHub().repo(repo)
    for a in list(r.issues(state="open")):
        if re.search(r"^alpha release.*pending", a.title, flags=re.IGNORECASE):
            return r, a
    assert not assert_exists, '"Alpha Release [pending]" issue not found'
    return r, None


def _assert_closed(issue):
    assert issue.state == "closed", f"Need to close #{issue.number} {issue.title}"


def _cfg():
    global cfg
    n = None
    p = PKDict(
        api_pause_seconds=(
            0 if pkconfig.channel_in("dev") else 10,
            int,
            "pauses between backups",
        ),
        exclude_re=(None, _cfg_exclude_re, "regular expression to exclude a repo"),
        keep_days=(
            _cfg_keep_days(2),
            _cfg_keep_days,
            "how many days of backups to keep",
        ),
        password=[None, str, "github passsword"],
        test_mode=(
            pkconfig.channel_in("dev"),
            pkconfig.parse_bool,
            f"only backs up {_TEST_REPO} repo",
        ),
        user=[None, str, "github user"],
    )
    cfg = pkconfig.init(**p)
    assert (
        cfg.test_mode or cfg.password is not None and cfg.user is not None
    ), "user and password required unless test_mode"


def _cfg_exclude_re(anything):
    if isinstance(anything, _RE_TYPE):
        return anything
    return re.compile(anything, flags=re.IGNORECASE)


def _cfg_keep_days(anything):
    if isinstance(anything, datetime.timedelta):
        return anything
    return datetime.timedelta(days=int(anything))


def _create_release_issue(repo, title, body):
    return repo.create_issue(title=title, body=body, labels=["release"])


def _issue_body(issue):
    res = issue.body
    if res is None or len(res) == 0:
        return ""
    res = res.replace("\r", "")
    if not res.endswith("\n"):
        res += "\n"
    return res


def _indent2(text):
    return re.sub(r"^(?=[^\n])", "  ", text, flags=re.MULTILINE)


def _promote(repo, prev, this):
    r = _repo_arg(repo)
    b = ""
    for i in r.issues(state="all", sort="updated", direction="desc"):
        if re.search(f"^{this} release", i.title, flags=re.IGNORECASE):
            _assert_closed(i)
            t = i
            break
        if re.search(f"^{prev} release", i.title, flags=re.IGNORECASE):
            if "pending" in i.title:
                continue
            _assert_closed(i)
            b += f"- #{i.number} {i.title}\n" + _indent2(_issue_body(i))
    else:
        raise AssertionError(f'No previous "{this} Release" issue found')
    assert b, f'no "{prev} Release" found, since #{t.number} {t.title}'
    i = _create_release_issue(r, _release_title(this), b)
    return f"Created #{i.number} {i.title}" + (b if cfg.test_mode else "")


def _release_title(channel, pending=False):
    x = (
        "[pending]"
        if pending
        else datetime.datetime.utcnow()
        .replace(
            microsecond=0,
        )
        .isoformat(sep=" ")
        + " UTC"
    )
    return f"{channel} Release {x}"


def _repo_arg(repo):
    assert repo, "repo not supplied"
    return _GitHub().repo(repo) if isinstance(repo, str) else repo


def _shell(cmd):
    subprocess.check_output(cmd, stderr=subprocess.STDOUT)


def _try(op):
    for t in range(_MAX_TRIES, 0, -1):
        try:
            return op()
        except github3.exceptions.ForbiddenError as e:
            x = getattr(e, "response", None)
            # Response ojects return false so don't use "not x" here
            if x is None:
                pkdlog(
                    'no "response" in ForbiddenError attributes={}',
                    [(a, getattr(e, a)) for a in dir(e) if not a.startswith("_")],
                )
                raise
            h = getattr(x, "headers", None)
            # See above. Being cautious about falsey testing
            if h is None:
                pkdlog('no "headers" in ForbiddenError response={}', h)
                raise
            r = h.get("X-RateLimit-Remaining", "n/a")
            if r != "0":
                pkdlog("some other error(?) X-RateLimit-Remaining={}", r)
                raise
            if t == 0:
                pkdlog("MAX_TRIES={} reached", _MAX_TRIES)
                raise
            r = int(h["X-RateLimit-Reset"])
            n = int(time.time())
            s = r - n
            if s <= 0:
                pkdlog("trying min sleep X-RateLimit-Reset={} <= now={}", r, n)
                s = 60
            elif s > 4000:
                # Should reset in an hour if the GitHub API is right
                pkdlog("trying max sleep; X-RateLimit-Reset={} > 4000 + now={}", r, n)
                s = 3600
            pkdlog("RateLimit hit sleep={}", s)
            time.sleep(s)
    raise AssertionError("should not get here")


_cfg()
