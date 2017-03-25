# -*- coding: utf-8 -*-
u"""wrapper for running simulations

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

_VENV = 'sim-venv'


def default_command(cmd, *args, **kwargs):
    """Wrapper until figure out *args with argh"""
    import sys

    return getattr(sys.modules[__name__], '_'+ cmd)(*args, **kwargs)


def _run(*args):
    """Run a command with the proper local python and path environment

    Args:
        args (tuple): what to run (flags and all)
    """
    import subprocess
    import py.path
    import os

    __git_commit()
    venv = py.path.local(_VENV)
    env = os.environ.copy()
    env['PATH'] = str(venv.join('bin')) + ':' + env['PATH']
    env['PYTHONUSERBASE'] = str(venv)
    subprocess.check_call(args, env=env)


def _init():
    """Create git repo locally and on remote
    """
    from pykern import pkcli
    import datetime
    import os
    import os.path
    import py.path
    import requests
    import subprocess

    if os.path.exists('.git') or os.path.exists('sim-env'):
        pckli.command_error('already initialized (.git directory exists)')
    #TODO(robnagler) configure bitbucket locally for each repo
    __init_venv()
    __init_git()


def _pip(*args):
    """Install a Python package in sim-venv

    Args:
        args (tuple): arguments to pass to pip
    """
    args = ['pip', '--user'] + list(args)
    return _run(*args)


def __git_commit():
    """commit all files"""
    #TODO(robnagler) do every run(?)
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', 'init'])
    subprocess.check_call(['git', 'push', '-u', 'origin', 'master'])


def __init_git():
    """Init git locally and to bitbucket"""
    try:
        gid = subprocess.check_output(['git', 'config', 'user.name']).strip()
    except subprocess.CalledProcessError:
        pckli.command_error('please "git login" first')
    title = py.path.local().basename
    v = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    name='sim-{}-{}'.format(py.path.local().basename, v).lower()
    url = 'https://api.bitbucket.org/2.0/repositories/{}/{}'.format(gid, name)
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
    py.path.local('.gitignore').write('out/\n')
    __git_commit()


def __init_venv():
    """Ensure all venv files are committed"""
    venv = py.path.local(_VENV).ensure_dir()
    venv.join('.gitignore').write('!*\n')
