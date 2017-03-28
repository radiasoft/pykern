# -*- coding: utf-8 -*-
u"""wrapper for running simulations

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig

#: Where we install files with pip
_PYTHON_USER_BASE = 'rsbase'

#: how to run python
_PYTHON = ('python', 'run.py')

#: how to run bash
_BASH = ('bash', 'run.sh')

#: git initialized
_GIT_DIR = '.git'

#: remote host
_GIT_REMOTE = 'bitbucket.org'

#: output directory
_OUT_DIR = 'out'

#: configuration
cfg = None


def default_command(cmd, *args, **kwargs):
    """Wrapper until figure out *args with argh"""
    import sys

    return getattr(sys.modules[__name__], '_cmd_'+ cmd)(*args, **kwargs)


def _call(args):
    """Run a command with the proper local python and path environment

    Args:
        args (tuple): what to run (flags and all)
    """
    from pykern import pkio
    import subprocess
    import os

    ub = pkio.py_path(_PYTHON_USER_BASE)
    env = os.environ.copy()
    env['PATH'] = str(ub.join('bin')) + ':' + env['PATH']
    env['PYTHONUSERBASE'] = str(ub)
    subprocess.check_call(args, env=env)


def _cmd_init():
    """Create git repo locally and on remote
    """
    from pykern import pkcli
    import os.path

    if os.path.exists(_GIT_DIR):
        pkcli.command_error('already initialized (.git directory exists)')
    #TODO(robnagler) configure bitbucket locally for each repo
    _init_python_user_base()
    _init_git()


def _cmd_pip(*args):
    """Install a Python package in rsbase

    Args:
        args (tuple): arguments to pass to pip
    """
    args = ['pip', '--user'] + list(args)
    return _call(args)


def _cmd_run():
    """Execute run.py or run.sh
    """
    from pykern import pkcli
    import os.path

    missing = []
    # Prefer _BASH, which may call run.py
    for x in (_BASH, _PYTHON):
        if os.path.exists(x[1]):
            _rsmanifest()
            _git_commit('run', check_init=True)
            return _call(x)
        missing.append(x[1])
    pkcli.command_error('{}: neither run file exists', missing)


def _git_auth():
    """Get git user.name

    Returns:
        str: configured user name
    """
    from pykern import pkcli
    import netrc

    try:
        b = netrc.netrc().authenticators(_GIT_REMOTE)
        if b:
            return (b[0], b[2])
    except netrc.NetrcParseError:
        pass
    pkcli.command_error('missing login info {}; please "git login"', _GIT_REMOTE)


def _git_commit(msg, check_init=False):
    """Write rsmanifest and commit all files

    Args:
        check_init (bool): make sure git is initialized
    """
    #TODO(robnagler) do every run(?)
    from pykern import pkcli
    import os.path
    import subprocess

    if check_init:
        if not os.path.exists(_GIT_DIR):
            pkcli.command_error('not initialized, please call "init"')
        _git_auth()
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', msg])
    c = ['git', 'push']
    if not check_init:
        c.extend(['-u', 'origin', 'master'])
    subprocess.check_call(c)


def _git_api_request(method, url, ctx):
    from pykern import pkcli
    import requests

    user, pw = _git_auth()
    ctx['method'] = method
    ctx['user'] = user
    ctx['pass'] = pw
    ctx['host'] = _GIT_REMOTE
    ctx['url'] = ('https://api.{host}/2.0/' + url).format(**ctx)
    x = dict(
        url=ctx['url'],
        method=ctx['method'],
        auth=(user, pw),
    )
    if 'json' in ctx:
        x['json'] = ctx['json']
    r = requests.request(**x)
    # Will return 2xx so best test for now
    if not r.ok:
        pkcli.command_error('{}: post failed: {} {}', ctx['url'], r, r.text)
    return r, ctx


def _init_git():
    """Init git locally and to bitbucket"""
    from pykern import pkcli
    from pykern import pkio
    import datetime
    import re
    import subprocess

    title = pkio.py_path().basename
    v = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    name = 'sim-{}-{}'.format(pkio.py_path().basename, v).lower()
    r, ctx = _git_api_request(
        'post',
        'repositories/{user}/{repo}',
        dict(
            repo=name,
            json=dict(
                scm='git',
                is_private=True,
                fork_policy='no_public_forks',
                name=name,
            ),
        ),
    )
    repo_url = r.json()['links']['clone'][0]['href']
    #TODO(robnagler) add README.md if not already there
    subprocess.check_call(['git', 'init'])
    subprocess.check_call(['git', 'remote', 'add', 'origin', repo_url])
    subprocess.check_call(['git', 'config', 'user.name', ctx['user']])
    subprocess.check_call(['git', 'checkout', '-b', 'master'])
    _out_dir()
    _git_commit('init')


def _init_python_user_base():
    """Ensure all python_user_base files are committed"""
    from pykern import pkio

    ub = pkio.py_path(_PYTHON_USER_BASE).ensure_dir()
    ub.join('.gitignore').write('!*\n')


def _out_dir():
    from pykern import pkio
    p = pkio.py_path(_OUT_DIR).ensure_dir()
    p.join('.gitignore').write('*\n!.gitignore\n')


def _pyenv_version():
    """Determine which pyenv

    Returns:
        str: pyenv version
    """
    import subprocess

    return subprocess.check_output(['pyenv', 'version']).split(' ')[0]


def _rsmanifest():
    from pykern import pkcollections
    from pykern import pkjson
    from pykern.pkcli import rsmanifest
    import cpuinfo
    import datetime
    import os
    import subprocess

    m = rsmanifest.read_all()
    m['sim'] = {
        'run': {
            'datetime': datetime.datetime.utcnow().isoformat(),
            'cpu_info': cpuinfo.get_cpu_info(),
            'pyenv': _pyenv_version(),
            'environ': pkcollections.Dict(os.environ),
        },
    }
    pkjson.dump_pretty(m, filename=rsmanifest.BASENAME)
