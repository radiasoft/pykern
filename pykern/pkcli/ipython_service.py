# -*- coding: utf-8 -*-
"""Manage IPython notebook services.

:copyright: Copyright (c) 2014-2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp

import argh
import datetime
import os
import pwd
import re
import socket
import subprocess
import time

import py.path
from pykern import pkcli
from pykern import pkio

PORT_MODULUS = 100
APP_PORT_BASE = {
    'xrw': 8000,
    'iota': 8000 + 1 * PORT_MODULUS,
    'ips_test': 30000,
}


def dev(notebook_dir='.', port=8000):
    """Start notebook running in specified dir and port.

    Users the "default" profile.

    Args:
        notebook_dir (str): what directory to execute in ['.']
        port (int): port to run on [8000]
    """
    port = int(port)
    app_dir = py.path.local(notebook_dir)
    app = 'default'
    _init_app_profile(
        app_dir=app_dir,
        application=app,
        base_url='/',
        ip='0.0.0.0',
        port=int(port),
        want_password=False,
    )
    with pkio.save_chdir(app_dir):
        os.execlp('ipython', 'ipython', 'notebook', '--profile=' + app)


def init(application):
    "Initialize application instance directory"
    _, rc, app_dir = _args(application, True)
    _init_app_profile(
        app_dir=app_dir,
        application=application,
        base_url='/{}/'.format(os.getenv('USER')),
        ip='127.0.0.1',
        port=_computed_port(application),
        want_password=True,
    )
    _init_start(app_dir, rc)
    return 'Initialized ipython app: ' + app_dir


def password(application):
    "Update password for application"
    import IPython
    p = IPython.lib.security.passwd()
    cfg = _ipython_cfg(application)
    with open(cfg, 'r') as f:
        s = f.read()
    s, count = re.subn(
        pattern=r"(\nc.NotebookApp.password\s*=\s*')[^']+",
        repl=r'\g<1>' + p,
        string=s,
        count=1)
    assert count == 1
    with open(cfg, 'w') as f:
        f.write(s)


def port(application):
    "return the port the service is running on or its computed value"
    # Allows for a change in static configuration
    port = _running_on_port(application)
    if port != 0:
        return port
    return _computed_port(application)


def start(application):
    "start ipython nbserver on port in ~/<application>"
    screen, rc, app_dir = _args(application)
    _assert_not_running(application)
    cmd = ['screen', '-d', '-m', '-S', screen, 'bash', '--rcfile', rc]
    with pkio.save_chdir(app_dir):
        subprocess.check_call(cmd)
    return '{}: IPython process started'.format(application)


def stop(application):
    "stop ipython nbserver on port in ~/<application>"
    screen, rc, app_dir = _args(application)
    if not _running_on_port(application):
        return application + ' not running, cannot stop'
    p = subprocess.Popen(['screen', '-list'], stdout=subprocess.PIPE)
    out = str(p.communicate()[0])
    r = re.compile(r'\b\d+\.' + screen + r'\b')
    for m in r.finditer(out):
        cmd = ['screen', '-S', m.group(0), '-X', 'quit']
        with pkio.save_chdir(app_dir):
            subprocess.call(cmd)
    for _ in range(3):
        if _running_on_port(application) == 0:
            return
        time.sleep(0.1)
    pkcli.command_error('{}: unable to stop all screens', screen)


def _args(application, is_init=False):
    if application not in APP_PORT_BASE:
        pkcli.command_error('{}: unknown application')
    home = _home()
    if not os.path.isdir(home):
        pkcli.command_error('{}: home directory does not exist', home)
    app_dir = os.path.join(home, application)
    rc = os.path.join(app_dir, '.startrc')
    screen_name = 'ipython-' + application
    if os.access(rc, os.R_OK):
        if is_init:
            pkcli.command_error(
                '{}: rc file found, {} already initialized', rc, application)
    elif not is_init:
        pkcli.command_error('{}: cannot find .startrc (need to call "init"?)', rc)
    return screen_name, rc, app_dir


def _assert_not_running(application):
    port = _running_on_port(application)
    if port != 0:
        pkcli.command_error('{}: server is already running on this port', port)


def _computed_port(application):
    return APP_PORT_BASE[application] + (int(os.getenv('UID', os.geteuid())) % PORT_MODULUS)


def _extract_port(application):
    cfg = _ipython_cfg(application)
    if not os.access(cfg, os.R_OK):
        return 0
    with open(cfg, 'r') as f:
        match = re.search(r'\nc\.NotebookApp\.port\s*=\s*(\d+)', f.read())
    if match is None:
        pkcli.command_error('{}: c.NotebookApp.port not found in config file', cfg)
    return int(match.group(1))


def _init_app_profile(**kwargs):
    _ipython_install()
    pkio.mkdir_parent(kwargs['app_dir'])
    subprocess.check_call(
        ['ipython', 'profile', 'create', kwargs['application']],
        stderr=open('/dev/null', 'w'))
    _init_ipython_cfg(kwargs)


def _init_ipython_cfg(kwargs):
    kwargs['password'] = "c.NotebookApp.password = 'not initialized'\n" if kwargs['want_password'] else ''
    _write(
        _ipython_cfg(kwargs['application']),
        '''# ipython notebook for {application}
c = get_config()
c.IPKernelApp.pylab = None
c.NotebookApp.base_kernel_url = '{base_url}'
c.NotebookApp.base_url = '{base_url}'
c.NotebookApp.ip = '{ip}'
c.NotebookApp.open_browser = False
{password}c.NotebookApp.port = {port}
''',
        kwargs,
    )

def _home():
    return os.getenv('HOME')


def _init_start(app_dir, rc):
    _write(
        os.path.join(app_dir, 'start.sh'),
        '''#!/bin/bash
cd $(dirname $0)
ipython notebook --profile=$(basename $(pwd))
''')
    _write(
        rc,
        '''#!/bin/bash
cd "$(dirname $BASH_SOURCE)"
ipython_notebook_service_dir="$(pwd)"
cd
# simulate bash
test -r /etc/profile && source /etc/profile
for f in ~/.bash_profile ~/.bash_login ~/.profile; do
    if test -r ; then
        source $f
	break
    fi
done
test -r ~/.bashrc && source ~/.bashrc
cd "$ipython_notebook_service_dir"
unset ipython_notebook_service_dir
sh start.sh
''')


def _ipython_install():
    need = False
    try:
        import IPython
    except ImportError:
        need = True
    if not need:
        need = _ipython_major_version() < 3
    if not need:
        return
    import pip
    # IPython 4 is completely different, not ready to upgrade.
    pip.main(['install', 'ipython[all]==3.2.1'])


def _ipython_cfg(application):
    return os.path.join(
        _home(),
        '.ipython',
        'profile_' + application,
        'ipython_notebook_config.py')


def _ipython_major_version():
    import IPython
    import distutils.version
    return distutils.version.StrictVersion(IPython.__version__).version[0];


def _running_on_port(application):
    port = _extract_port(application)
    if port == 0:
        return 0
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
    except socket.error as msg:
        return 0
    return port


def _write(file_name, to_format, keywords=None):
    s = re.sub(
        pattern=r'\n',
        repl=u'\n# Generated by ' + __file__ + ' on ' + datetime.datetime.now().ctime() + '\n',
        string=to_format,
        count=1)
    if keywords is not None:
        s = s.format(**keywords)
    with open(file_name, 'w') as f:
        f.write(s)
