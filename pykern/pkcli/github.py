# -*- coding: utf-8 -*-
u"""run github backups and restores

:copyright: Copyright (c) 2013-2018 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
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

_TXZ = '.txz'

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


def collaborators(org, affiliation='direct'):
    """Lists direct repos to which user has access and is not a team member

    Configured user must be an owner

    Args:
        org (str): GitHub organization
        affiliation (str): all, direct, outside
    """
    import yaml

    g = _GitHub()._login()
    o = g.organization(org)
    res = dict()
    for r in o.repositories():
        res[str(r.name)] = [str(c.login) for c in  r.collaborators(affiliation=affiliation)]
    return yaml.dump(res, width=1000000)


def issues_as_csv(repo):
    """Export issues as CSV

    Args:
        repo (str): will add radiasoft/ if missing
    """
    import io

    a = repo.split('/')
    if len(a) == 1:
        a.insert(0, 'radiasoft')

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

    g = github3.login(cfg.user, password=cfg.password)
    r = g.repository(*a)
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
    a = repo.split('/')
    if len(a) == 1:
        a.insert(0, 'radiasoft')
    g = github3.login(cfg.user, password=cfg.password)
    r = g.repository(*a)
    for x in ('inprogress', 'c5def5'), ('1', 'b60205'), ('2', 'fbca04'):
        try:
            r.create_label(*x)
        except github3.exceptions.UnprocessableEntity:
            # 422 Validation Failed: happens because already exists
            pass


def restore(git_txz):
    """Restores the git directory (only) to a new directory with the .git.txz suffix
    """
    m = re.search('(([^/]+)\.git)\.txz$', git_txz)
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
    def _login(self):
        self._github = github3.GitHub(username=cfg.user, password=cfg.password) \
            if cfg.password else github3.GitHub()
        return self._github

    def _subscriptions(self):
        if cfg.test_mode:
            return [self._github.repository('radiasoft', 'test-github-backup')]
        return self._github.subscriptions()


    def _iter_subscriptions(self):
        self._login()
        for r in self._subscriptions():
            if cfg.exclude_re and cfg.exclude_re.search(r.full_name):
                pkdc('exclude: {}', r.full_name)
                continue
            yield r


class _Backup(_GitHub):
    def __init__(self):
        # POSIT: timestamps are sorted in _clone()
        self._date_d = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        with pkio.save_chdir(self._date_d, mkdir=True):
            sleep = 0
            for r in self._iter_subscriptions():
                if sleep:
                    time.sleep(sleep)
                else:
                    sleep = cfg.api_pause_seconds
                pkdlog('{}: begin', r.full_name)
                self._repo(r)
        self._purge()

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
            txz = base + _TXZ
            # POSIT: timestamp Backup
            prev = pkio.sorted_glob('../*/' + txz)
            if prev:
                pkdc('updating from {}', prev[-1])
                _shell(['tar', 'xJf', str(prev[-1])])
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
            if not repo.has_issues:
                return
            base = bd + '.issues'
            d = pkio.mkdir_parent(base)
            for i in repo.issues(state='all'):
                j = _trim_body(i)
                j['comments'] = [_trim_body(c) for c in i.comments()]
                p = i.pull_request()
                if p:
                    j['review_comments'] = [_trim_body(c) for c in p.review_comments()]
                pkjson.dump_pretty(j, filename=d.join(str(i.number) + '.json'))
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
            _json(repo.comments(), '.comments')
            #TODO(robnlager) releases
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


def _cfg():
    import netrc

    global cfg
    n = None
    p = pkcollections.Dict(
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
            'only backs up test-github-backup repo',
        ),
        user=[None, str, 'github user'],
    )
    try:
        n = netrc.netrc().authenticators('github.com')
        for i, k in (0, 'user'), (2, 'password'):
            p[k][0] = n[i]
    except Exception:
        pass
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


def _shell(cmd):
    subprocess.check_output(cmd, stderr=subprocess.STDOUT)


_cfg()
