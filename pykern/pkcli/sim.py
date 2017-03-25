# -*- coding: utf-8 -*-
u"""wrapper for running simulations

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


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

    #TODO(robnagler) need to .gitignore output files
    venv = py.path.local('rs-venv')
    env = os.environ.copy()
    env['PATH'] = str(venv.join('bin')) + ':' + env['PATH']
    env['PYTHONUSERBASE'] = str(venv)
    subprocess.check_call(args, env=env)


def _init():
    import requests
    import subprocess
    import os
    import py.path
    import datetime
    from pykern import pkcli

    #TODO(robnagler) configure bitbucket locally for each repo
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

    #TODO(robnagler) do every run(?)
    subprocess.check_call(['git', 'add', '.'])
    subprocess.check_call(['git', 'commit', '-m', 'init'])
    subprocess.check_call(['git', 'push', '-u', 'origin', 'master'])
