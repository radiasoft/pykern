#!/usr/bin/env python
# -*-python-*-
from __future__ import print_function
import argh
import datetime
import github3
import glob
import json
import netrc
import os
import os.path
import re
import subprocess
import sys
import time
import traceback

_BACKUP_DIR = "~/bkp"
_GITHUB_HOST = 'github.com'
_GITHUB_URI = 'https://' + _GITHUB_HOST
_GITHUB_API = 'https://api.' + _GITHUB_HOST
_PURGE_DELTA = datetime.timedelta(days=2)
_WIKI_ERROR_OK = r'fatal: remote error: access denied or repository not exported: .*wiki.git'
try:
    _EXCLUDE = os.getenv('BIVIO_GITHUB_EXCLUDE')
    if _EXCLUDE:
        _EXCLUDE = re.compile(_EXCLUDE)
except Exception:
    _EXCLUDE = None

def restore(git_txz : 'git.txz file'):
    'Restores the git directory (only) to a new directory with the .git.txz suffix'
    m = re.search('(([^/]+)\.git)\.txz$', git_txz)
    if not m:
        raise ValueError(git_txz, ': does not end in .git.txz')
    d = m.group(2)
    _debug('restore: ' + d)
    g = m.group(1)
    os.mkdir(d)
    os.chdir(d)
    _shell(['tar', 'xJf', git_txz])
    os.rename(g, '.git')
    _shell(['git', 'config', 'core.bare', 'false'])
    _shell(['git', 'config', 'core.logallrefupdates', 'true'])
    _shell(['git', 'checkout'])


def backup():
    'Backs up all github repositories associated with user'
    try:
        _Backup()
    except subprocess.CalledProcessError as e:
        if hasattr(e, 'output'):
            _p('ERROR: Backup {}'.format(e.output))
    _p('SUCCESS')


class _Backup(object):
    def __init__(self):
        self._chdir()
        self._login()

        #TEST
        if False:
            self._repo(self._github.repository('biviosoftware', 'utilities'))
            return

        sleep = 0
        for r in self._github.iter_repos(type="all"):
            if sleep:
                time.sleep(sleep)
            else:
                sleep = 20
            self._repo(r)

        self._purge()

    def _chdir(self):
        self._root = os.path.expanduser(_BACKUP_DIR)
        d = os.path.join(
            self._root,
            datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        try:
            os.makedirs(d)
        except:
            pass
        os.chdir(d)
        _debug("directory: " + d)
        self._dir = d

    def _login(self):
        n = netrc.netrc()
        self._user, a, self._pw = n.authenticators(_GITHUB_HOST)
        self._github = github3.login(self._user, password=self._pw)


    def _purge(self):
        g = "[0-9]" * len(os.path.basename(self._dir))
        expires = datetime.datetime.utcnow() - _PURGE_DELTA
        for d in glob.glob(os.path.join(self._root, g)):
            t = datetime.datetime.utcfromtimestamp(os.stat(d).st_mtime)
            if t < expires:
                _shell(["rm", "-rf", d])

    def _repo(self, repo):
        fn = repo.full_name
        if _EXCLUDE and _EXCLUDE.search(fn):
            _debug('exclude: ' + fn)
            return
        _debug("backup: " + fn)
        bd = re.sub("/", "-", fn)

        def _clone(suffix):
            base = bd + suffix
            for cmd in [
                ["git", "clone", "--quiet", "--mirror",
                        _GITHUB_URI + "/" + fn + suffix,
                        base],
                ["tar", "cJf", base + ".txz", base],
                ["rm", "-rf", base]]:
                _shell(cmd)

        def _json(gen, suffix):
            base = bd + suffix
            with open(base, "wt") as f:
                sep = "["
                for i in gen:
                    f.write(sep)
                    j = i.to_json()
                    assert json.loads(j)
                    f.write(j)
                    sep = ","
                if sep == "[":
                    # Empty iteration
                    f.write(sep)
                f.write("]")
            _shell(["xz", base])

        try:
            _clone(".git")

            if repo.has_wiki:
                try:
                    _clone(".wiki.git")
                except subprocess.CalledProcessError as e:
                    if not re.search(_WIKI_ERROR_OK, str(e.output)):
                        raise
            _json(_Iterator(repo.iter_comments()), ".comments")

            if repo.has_issues:
                _json(_Iterator(repo.iter_issues(state="all")), ".issues")
        except Exception as e:
            if hasattr(e, 'output'):
                _p('ERROR: {} {}'.format(fn, e.output))
            traceback.print_exc()

class _Iterator(object):

    def __init__(self, child):
        self._child = child

    def __iter__(self):
        return self

    def __next__(self):
        i = self._child.next()
        if type(i.to_json()) is dict:
            return _Element(i)
        return i

class _Element(object):

    def __init__(self, child):
        self._child = child

    def to_json(self):
        res = json.dumps(self._child.to_json())
        assert res[-1] == '}'
        res = res[:-1]

        def _json(x):
            j = x.to_json()
            if type(j) is str:
                return j
            return json.dumps(j)
        for k in ['comments', 'events', 'labels']:
            func = getattr(self._child, 'iter_' + k, None)
            if func is None:
                continue
            v = ",".join(map(_json, func()))
            res += ',"' + k + '":[' + v + ']'
        res += '}'

        return res



def _debug(msg):
    pass
    #_p(msg)


def _p(msg):
    print(msg)
    sys.stdout.flush()



def _shell(cmd):
    subprocess.check_output(cmd, stderr=subprocess.STDOUT)


if __name__ == '__main__':
    argh.dispatch_commands([backup, restore])
