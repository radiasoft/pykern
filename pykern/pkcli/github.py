# -*- coding: utf-8 -*-
u"""run github backups and restores

:copyright: Copyright (c) 2013-2018 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern.pkdebug import pkdlog, pkdp, pkdc, pkdexc
import datetime
import github3
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


def labels(repo):
    """Setup the RadiaSoft labels for ``repo``.

    Will add "radiasoft/" to the name if it is missing.

    Args:
        repo (str): will add https://github.com/radiasoft if missing
    """
    import github3.exceptions

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


class _Backup(object):
    def __init__(self):
        self._date_d = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        with pkio.save_chdir(self._date_d, mkdir=True):
            self._login()
            sleep = 0
            for r in self._github.subscriptions():
                if cfg.test_mode:
                    if r.name != 'pykern':
                        continue
                if cfg.exclude_re and cfg.exclude_re.search(r.full_name):
                    pkdc('exclude: {}', r.full_name)
                    continue
                if sleep:
                    time.sleep(sleep)
                else:
                    sleep = cfg.api_pause_seconds
                pkdlog('{}: begin', r.full_name)
                self._repo(r)
        self._purge()

    def _login(self):
        self._github = github3.login(cfg.user, password=cfg.password)

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
            for cmd in [
                ['git', 'clone', '--quiet', '--mirror',
                        _GITHUB_URI + '/' + fn + suffix,
                        base],
                ['tar', 'cJf', base + '.txz', base],
            ]:
                _shell(cmd)
            pkio.unchecked_remove(base)

        def _json(gen, suffix):
            base = bd + suffix
            with open(base, 'wt') as f:
                sep = '['
                for i in gen:
                    f.write(sep)
                    j = i.as_json()
                    assert json.loads(j)
                    f.write(j)
                    sep = ','
                if sep == '[':
                    # Empty iteration
                    f.write(sep)
                f.write(']')
            _shell(['xz', base])

        try:
            _clone('.git')
            if repo.has_issues:
                _json(repo.issues(state='all'), '.issues')
            if repo.has_wiki:
                try:
                    _clone('.wiki.git')
                except subprocess.CalledProcessError as e:
                    if not re.search(_WIKI_ERROR_OK, str(e.output)):
                        raise
            _json(repo.comments(), '.comments')
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
        api_pause_seconds=(30, int, 'pauses between backups'),
        exclude_re=(None, _cfg_exclude_re, 'regular expression to exclude a repo'),
        keep_days=(
            _cfg_keep_days(2),
            _cfg_keep_days,
            'how many days of backups to keep',
        ),
        password=[str, 'github passsword'],
        test_mode=(False, pkconfig.parse_bool, 'only backup this repo'),
        user=[str, 'github user'],
    )
    try:
        n = netrc.netrc().authenticators('github.com')
        for i, k in (0, 'user'), (2, 'password'):
            p[k].insert(0, n[i])
    except Exception:
        for k in 'password', 'user':
            p[k] = pkconfig.Required(*p[k])
    cfg = pkconfig.init(**p)


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
