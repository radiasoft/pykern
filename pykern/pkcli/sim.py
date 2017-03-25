# -*- coding: utf-8 -*-
u"""wrapper for running simulations

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

#: Where we install files with pip
_VENV = 'rsvenv'

#: how to run python
_PYTHON = ('python', 'run.py')

#: how to run bash
_BASH = ('bash', 'run.sh')

#: git initialized
_GIT_DIR = '.git'

#: output directory
_OUT_DIR = 'out'


def default_command(cmd, *args, **kwargs):
    """Wrapper until figure out *args with argh"""
    import sys

    return getattr(sys.modules[__name__], '_cmd_'+ cmd)(*args, **kwargs)


def _cmd_init():
    """Create git repo locally and on remote
    """
    from pykern import pkcli
    import os.path

    if os.path.exists(_GIT_DIR):
        pkcli.command_error('already initialized (.git directory exists)')
    #TODO(robnagler) configure bitbucket locally for each repo
    _init_venv()
    _init_git()


def _cmd_pip(*args):
    """Install a Python package in sim-venv

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


def _call(args):
    """Run a command with the proper local python and path environment

    Args:
        args (tuple): what to run (flags and all)
    """
    from pykern import pkio
    import subprocess
    import os

    venv = pkio.py_path(_VENV)
    env = os.environ.copy()
    env['PATH'] = str(venv.join('bin')) + ':' + env['PATH']
    env['PYTHONUSERBASE'] = str(venv)
    subprocess.check_call(args, env=env)


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
        _git_uid()
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', msg])
    subprocess.check_call(['git', 'push', '-u', 'origin', 'master'])


def _git_uid():
    from pykern import pkcli
    import subprocess

    try:
        return subprocess.check_output(['git', 'config', 'user.name']).rstrip()
    except subprocess.CalledProcessError:
        pkcli.command_error('please "git login" first')


def _init_git():
    """Init git locally and to bitbucket"""
    from pykern import pkcli
    from pykern import pkio
    import datetime
    import requests
    import subprocess

    title = pkio.py_path().basename
    v = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    name='sim-{}-{}'.format(pkio.py_path().basename, v).lower()
    uid = _git_uid()
    url = 'https://api.bitbucket.org/2.0/repositories/{}/{}'.format(uid, name)
    r = requests.post(
        url,
        json=dict(
            scm='git',
            is_private=True,
            fork_policy='no_public_forks',
            name=name,
        ),
    )
    if r.status_code != 200:
        pkcli.command_error('{}: post failed: {} {}', url, r, r.text)
    repo_url = r.json()['links']['clone'][0]['href']
    #TODO(robnagler) add README.md if not already there
    subprocess.check_call(['git', 'init'])
    subprocess.check_call(['git', 'remote', 'add', 'origin', repo_url])
    subprocess.check_call(['git', 'checkout', '-b', 'master'])
    pkio.py_path(_OUT_DIR).ensure_dir()
    pkio.py_path('.gitignore').write(_OUT_DIR + '/\n')
    _git_commit('init')


def _init_venv():
    """Ensure all venv files are committed"""
    from pykern import pkio

    venv = pkio.py_path(_VENV).ensure_dir()
    venv.join('.gitignore').write('!*\n')


def _rsmanifest():
    from pykern import pkjson
    from pykern.pkcli import rsmanifest
    import cpuinfo
    import datetime
    import subprocess

    m = rsmanifest.read_all()
    m['sim'] = {
        'run': {
            'datetime': datetime.datetime.utcnow().isoformat(),
            'cpu_info': cpuinfo.get_cpu_info(),
            'python': subprocess.check_output(['pyenv', 'which', 'python']).rstrip(),
        },
    }
    pkjson.dump_pretty(m, filename=rsmanifest.BASENAME)
