# -*- coding: utf-8 -*-
u"""run github backups and restores

:copyright: Copyright (c) 2013-2018 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
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
import os
import os.path
import re
import subprocess
import sys
import time


_GITHUB_HOST = 'github.com'
_GITHUB_URI = 'https://' + _GITHUB_HOST
_GITHUB_API = 'https://api.' + _GITHUB_HOST
_WIKI_ERROR_OK = r'fatal: remote error: access denied or repository not exported: .*wiki.git'
_RE_TYPE = type(re.compile(''))
_MAX_TRIES = 3
_TEST_REPO = 'test-pykern-github'
_TXZ = '.txz'
_LIST_ARG_SEP_RE = re.compile(r'[\s,:;]+')

def backup():
    """Backs up all github repositories associated with user into pwd

    Creates timestamped directory, and purges directories older than cfg.keep_days
    """
    try:
        _Backup()
    except subprocess.CalledProcessError as e:
        if hasattr(e, 'output'):
            pkdlog('ERROR: Backup {}', e.output)
    pkdlog('DONE')


def collaborators(org, filename, affiliation='outside', private=True):
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


def create_issue(repo, title, body='', assignees=None, labels=None, milestone=None):

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


def create_milestone(repo, title, description='', due_on=None):
    a = PKDict()
    if due_on:
        # GitHub seems to always create at 08:00:00Z in any zone
        # so just have the user put in the time.
        a.due_on = due_on + 'T08:00:00Z'
    if description:
        a.description = description
    return _repo_arg(repo).create_milestone(
        title=title,
        **a,
    ).number


def get_milestone(repo, title):
    t = title.lower()
    for m in _repo_arg(repo).milestones(state='open'):
        if m.title.lower() == t:
            return m.number
    raise KeyError(f'milestone={title} not found')


def issue_pending_alpha(repo):
    """Create "Alpha Release [pending]" issue

    This should be created after the current alpha completes.
    """
    r, a = _alpha_pending(repo, assert_exists=False)
    if a:
        return '#{a.number} {a.title} already exists'
    i = r.create_issue(title=_release_title('Alpha', pending=True), body='');
    return f'Created #{i.number}'


def issue_start_alpha(repo):
    r, a = _alpha_pending(repo)
    for i in r.issues(state='open'):
        if (
            i.number != a.number
            and re.search(r'^alpha release \d+', i.title, flags=re.IGNORECASE)
        ):
            _assert_closed(i)
            # does not get here
    a.edit(title=_release_title('Alpha'));
    return f'Started #{a.number} and {issue_pending_alpha(repo)}' + (
        a.body if cfg.test_mode else ''
    )


def issue_start_beta(repo):
    return _promote(repo, 'Alpha', 'Beta')


def issue_start_prod(repo):
    return _promote(repo, 'Beta', 'Prod')


def issue_update_alpha_pending(repo):
    r, a = _alpha_pending(repo)
    c = list(
        r.commits(
            sha='master',
            since=datetime.datetime.now() - datetime.timedelta(minutes=24 * 60),
        ),
    )[0]
    m = re.search(r'#(\d+)', c.message)
    assert m, \
        f'last commit={c.sha} missing #NN in message={c.message}'
    try:
        i = r.issue(m.group(1))
    except Exception as e:
        raise AssertionError(f'Issue #{m.group(1)} exception={e}')
    x = f'#{i.number}'
    b = a.body
    if x in b:
        return f'#{a.number} already references {x}'
    if b and not b.endswith('\n'):
        b += '\n'
    x = f'- {i.title} {x}\n'
    a.edit(body=b + x)
    return f'Updated #{a.number} with: {x}'


def issues_as_csv(repo):
    """Export issues as CSV

    Args:
        repo (str): will add radiasoft/ if missing
    """
    import io

    cols = (
        u'number',
        u'title',
        u'assignees',
        u'comments_count',
        u'comments_url',
        u'created_at',
        u'events_url',
        u'html_url',
        u'id',
        u'labels_urlt',
        u'locked',
        u'milestone',
        u'original_labels',
        u'pull_request_urls',
        u'state',
        u'updated_at',
        u'user',
        u'body',
    )

    def _s(v):
        if v is None:
            return u''
        if isinstance(v, list):
            return u','.join([_s(x) for x in v])
        return unicode(getattr(v, 'name', v))

    specials = set(u'\n,')
    def _c(i, c):
        v = _s(getattr(i, c)) \
            .replace(u'"', u'""')
        if any(c in specials for c in v):
            return u'"' + v + u'"'
        return v

    r = _repo_arg(repo)
    n = a[1] + '.csv'
    with io.open(n, mode='w', encoding='utf8') as f:
        def _write(v):
            # Need custom csv, because utf8 not handled by py2's csv
            f.write(u','.join(v) + u'\r\n')

        _write(cols)
        for i in r.issues(state='open'):
            _write([_c(i, c) for c in cols])
    return n


def labels(repo):
    """Setup the RadiaSoft labels for ``repo``.

    Will add "radiasoft/" to the name if it is missing.

    Args:
        repo (str): will add https://github.com/radiasoft if missing
    """
    r = _repo_arg(repo)
    for x in ('inprogress', 'c5def5'), ('1', 'b60205'), ('2', 'fbca04'):
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
    """Restores the git directory (only) to a new directory with the .git.txz suffix
    """
    m = re.search(r'(([^/]+)\.git)\.txz$', git_txz)
    if not m:
        raise ValueError(git_txz, ': does not end in .git.txz')
    git_txz = pkio.py_path(git_txz)
    d = m.group(2)
    pkdc('restore: {}', d)
    g = m.group(1)
    with pkio.save_chdir(d, mkdir=True):
        _shell(['tar', 'xJf', str(git_txz)])
        os.rename(g, '.git')
        _shell(['git', 'config', 'core.bare', 'false'])
        _shell(['git', 'config', 'core.logallrefupdates', 'true'])
        _shell(['git', 'checkout'])


class _GitHub(object):
    def __init__(self):
        self._github = None

    def login(self):
        self._github = github3.GitHub(username=cfg.user, password=cfg.password) \
            if cfg.password else github3.GitHub()
        return self._github

    def repo(self, repo):
        if not self._github:
            self.login()
        a = repo.split('/')
        if len(a) == 1:
            a.insert(0, 'radiasoft')
        return self._github.repository(*a)

    def _subscriptions(self):
        if cfg.test_mode:
            return [self._github.repository('radiasoft', _TEST_REPO)]
        return self._github.subscriptions()


    def _iter_subscriptions(self):
        """Returns a list so that we don't get rate limited at startup.
        """
        self.login()
        res = []
        for r in self._subscriptions():
            if cfg.exclude_re and cfg.exclude_re.search(r.full_name):
                pkdc('exclude: {}', r.full_name)
                continue
            res.append(r)
        return res


class _Backup(_GitHub):
    def __init__(self):
        # POSIT: timestamps are sorted in _clone()
        self._date_d = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        with pkio.save_chdir(self._date_d, mkdir=True):
            sleep = 0
            for r in _try(self._iter_subscriptions):
                pkdlog('{}: begin', r.full_name)
                self._repo(r)
        self._purge()

    def _extract_backup(self, backup):
        pkdc('updating from {}', backup)
        _shell(['tar', 'xJf', str(backup)])

    def _prev_backup(self, base):
        # POSIT: timestamp Backup
        b = pkio.sorted_glob('../*/' + base + _TXZ)
        return b[-1] if b else []

    def _purge(self):
        expires = datetime.datetime.utcnow() - cfg.keep_days
        for d in pkio.sorted_glob('[0-9]' * len(self._date_d)):
            t = datetime.datetime.utcfromtimestamp(d.stat().mtime)
            if t < expires:
                pkio.unchecked_remove(d)

    def _repo(self, repo):
        fn = repo.full_name
        bd = re.sub('/', '-', fn)

        def _clone(suffix):
            base = bd + suffix
            prev = self._prev_backup(base)
            if prev:
                self._extract_backup(prev)
                with pkio.save_chdir(base):
                    _shell(['git', 'remote', 'update'])
            else:
                _shell([
                    'git',
                    'clone',
                    '--quiet',
                    '--mirror',
                    _GITHUB_URI + '/' + fn + suffix,
                    base,
                ])
            _tar(base)

        def _issues():
            def _issue(i, d):
                j = _trim_body(i)
                j['comments'] = [_trim_body(c) for c in i.comments()]
                p = i.pull_request()
                if p:
                    j['review_comments'] = [_trim_body(c) for c in p.review_comments()]
                pkjson.dump_pretty(j, filename=d.join(str(i.number) + '.json'))

            if not repo.has_issues:
                return
            base = bd + '.issues'
            d = pkio.mkdir_parent(base)
            prev = self._prev_backup(base)
            k = PKDict(state='all')
            if prev:
                self._extract_backup(prev)
                k.since = datetime.datetime.now() - datetime.timedelta(days=7)
            for i in _try(lambda: list(repo.issues(**k))):
                _try(lambda: _issue(i, d))
            _tar(base)

        def _json(gen, suffix):
            base = bd + suffix
            with open(base, 'wt') as f:
                sep = '[\n'
                for i in gen:
                    f.write(sep)
                    f.write(pkjson.dump_pretty(_trim_body(i)))
                    sep = ',\n'
                if '[' in sep:
                    # Empty iteration
                    f.write(sep)
                f.write(']\n')
            _shell(['xz', base])

        def _tar(base):
            _shell(['tar', 'cJf', base + _TXZ, base])
            pkio.unchecked_remove(base)

        def _trim_body(o):
            res = o.as_dict()
            try:
                # github returns three formats, and we only want source
                del res['body_text']
                del res['body_html']
            except KeyError:
                pass
            return res

        try:
            _issues()
            _clone('.git')
            if repo.has_wiki:
                try:
                    _clone('.wiki.git')
                except subprocess.CalledProcessError as e:
                    if not re.search(_WIKI_ERROR_OK, str(e.output)):
                        raise
            _try(lambda: _json(repo.comments(), '.comments'))
            #TODO(robnagler) releases, packages, projects
            return
        except Exception as e:
            pkdlog(
                'ERROR: {} {} {} {} {}',
                fn,
                type(e),
                e,
                getattr(e, 'output', None),
                pkdexc(),
            )


def _alpha_pending(repo, assert_exists=True):
    r = _GitHub().repo(repo)
    for a in list(r.issues(state='open')):
        if re.search(r'^alpha release.*pending', a.title, flags=re.IGNORECASE):
            return r, a
    assert not assert_exists, \
        '"Alpha Release [pending]" issue not found'
    return r, None


def _assert_closed(issue):
    assert issue.state == 'closed', f'Need to close #{issue.number} {issue.title}'


def _cfg():
    global cfg
    n = None
    p = PKDict(
        api_pause_seconds=(
            0 if pkconfig.channel_in('dev') else 10,
            int,
            'pauses between backups',
        ),
        exclude_re=(None, _cfg_exclude_re, 'regular expression to exclude a repo'),
        keep_days=(
            _cfg_keep_days(2),
            _cfg_keep_days,
            'how many days of backups to keep',
        ),
        password=[None, str, 'github passsword'],
        test_mode=(
            pkconfig.channel_in('dev'),
            pkconfig.parse_bool,
            f'only backs up {_TEST_REPO} repo',
        ),
        user=[None, str, 'github user'],
    )
    cfg = pkconfig.init(**p)
    assert cfg.test_mode or cfg.password is not None and cfg.user is not None, \
        'user and password required unless test_mode'


def _cfg_exclude_re(anything):
    if isinstance(anything, _RE_TYPE):
        return anything
    return re.compile(anything, flags=re.IGNORECASE)


def _cfg_keep_days(anything):
    if isinstance(anything, datetime.timedelta):
        return anything
    return datetime.timedelta(days=int(anything))


def _promote(repo, prev, this):
    r = _repo_arg(repo)
    b = ''
    for i in r.issues(state='all', sort='updated', direction='desc'):
        if re.search(f'^{this} release', i.title, flags=re.IGNORECASE):
            _assert_closed(i)
            t = i
            break
        if re.search(f'^{prev} release', i.title, flags=re.IGNORECASE):
            if 'pending' in i.title:
                continue
            _assert_closed(i)
            b += (
                f'- #{i.number} {i.title}\n'
                + re.sub(
                    r'^(?=[^\n])',
                    '  ',
                    i.body,
                    flags=re.MULTILINE,
                )
            )
            if not b.endswith('\n'):
                b += '\n'
    else:
        raise AssertionError(f'No previous "{this} Release" issue found')
    assert b, \
        f'no "{prev} Release" found, since #{t.number} {t.title}'
    i = r.create_issue(title=_release_title(this), body=b);
    return f'Created #{i.number} {i.title}' + (b if cfg.test_mode else '')


def _release_title(channel, pending=False):
    x = '[pending]' if pending else datetime.datetime.utcnow().replace(
        microsecond=0,
    ).isoformat(sep=' ') + ' UTC'
    return f'{channel} Release {x}'


def _repo_arg(repo):
    assert repo, 'repo not supplied'
    return _GitHub().repo(repo) if isinstance(repo, str) else repo


def _shell(cmd):
    subprocess.check_output(cmd, stderr=subprocess.STDOUT)


def _try(op):
    for t in range(_MAX_TRIES, 0, -1):
        try:
            return op()
        except github3.exceptions.ForbiddenError as e:
            x = getattr(e, 'response', None)
            # Response ojects return false so don't use "not x" here
            if x is None:
                pkdlog(
                    'no "response" in ForbiddenError attributes={}',
                    [(a, getattr(e, a)) for a in dir(e) if not a.startswith('_')],
                )
                raise
            h = getattr(x, 'headers', None)
            # See above. Being cautious about falsey testing
            if h is None:
                pkdlog('no "headers" in ForbiddenError response={}', h)
                raise
            r = h.get('X-RateLimit-Remaining', 'n/a')
            if r != '0':
                pkdlog('some other error(?) X-RateLimit-Remaining={}', r)
                raise
            if t == 0:
                pkdlog('MAX_TRIES={} reached', _MAX_TRIES)
                raise
            r = int(h['X-RateLimit-Reset'])
            n = int(time.time())
            s = r - n
            if s <= 0:
                pkdlog('trying min sleep X-RateLimit-Reset={} <= now={}', r, n)
                s = 60
            elif s > 4000:
                # Should reset in an hour if the GitHub API is right
                pkdlog('trying max sleep; X-RateLimit-Reset={} > 4000 + now={}', r, n)
                s = 3600
            pkdlog('RateLimit hit sleep={}', s)
            time.sleep(s)
    raise AssertionError('should not get here')

_cfg()
