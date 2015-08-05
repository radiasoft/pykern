# -*- coding: utf-8 -*-
u"""Manage IPython notbook services

:copyright: Copyright (c) 2014-2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import argh
import datetime
import os
import pwd
import re
import socket
import subprocess
import time

from pykern.pkdebug import pkdp, pkdc
from pykern import pkcli

PORT_MODULUS = 100
APP_PORT_BASE = {
    'xrw': 8000,
    'iota': 8000 + 1 * PORT_MODULUS,
    'ips_test': 30000}
bin_file = {}


def init(user, application):
    "Initialize user application instance directory"
    appdir, rc = _args(user, application, True)
    _ipython_install()
    subprocess.check_call(_cmd(user, ['mkdir', appdir]))
    subprocess.check_call(
        _cmd(user, ['ipython', 'profile', 'create', application]),
        stderr=open('/dev/null', 'w'))
    _init_ipython_cfg(user, application)
    _init_start(user, appdir, rc)
    return 'Initialized ipython app: ' + appdir


def password(user, application):
    "Update user's password for application"
    import IPython
    p = IPython.lib.security.passwd()
    cfg = _ipython_cfg(user, application)
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
    _chown(cfg, user)


def port(user, application):
    "return the port the service is running on or its computed value"
    # Allows for a change in static configuration
    port = _running_on_port(user, application)
    if port != 0:
        return port
    return _computed_port(user, application)


def start(user, application):
    "start ipython nbserver for user on port in ~/<application>"
    screen, rc, _ = _args(user, application)
    _assert_not_running(user, application)
    cmd = _cmd(user, ['screen', '-d', '-m', '-S', screen, _bin(user, 'bash'), '--rcfile', rc])
    subprocess.check_call(cmd)
    return


def stop(user, application):
    "stop ipython nbserver for user on port in ~/<application>"
    screen, rc, _ = _args(user, application)
    if _running_on_port(user, application):
        p = subprocess.Popen(_cmd(user, ['screen', '-list']), stdout=subprocess.PIPE)
        out = str(p.communicate()[0])
        r = re.compile(r'\b\d+\.' + screen + r'\b')
        for m in r.finditer(out):
            cmd = _cmd(user, ['screen', '-S', m.group(0), '-X', 'quit'])
            subprocess.call(cmd)
        for _ in range(3):
            if _running_on_port(user, application) == 0:
                return
            time.sleep(0.1)
        raise ValueError('unable to stop all screens named ' + screen)
    else:
        print application + ' not running for ' + user
    return


def _args(user, application, init=False):
    if application not in APP_PORT_BASE:
        raise ValueError('unknown application: ' + application)
    home = _home(user)
    if not os.path.isdir(home):
        raise ValueError('invalid user or no home directory: ' + user)
    appdir = os.path.join(home, application)
    rc = os.path.join(appdir, '.startrc')
    if os.access(rc, os.R_OK):
        if init:
            raise ValueError('already initialized, rc file found: ' + rc)
    else:
        if init:
            return appdir, rc
        raise ValueError('cannot find .startrc: ' + rc)
    os.chdir(appdir)
    return 'ipython-' + application, rc


def _assert_not_running(user, application):
    port = _running_on_port(user, application)
    if port != 0:
        raise ValueError('server is running on port ' + str(port) + ' for ' + user)


def _bin(user, prog):
    k = ' '.join((user, prog))
    if k not in bin_file:
        m = re.search('^/', prog)
        if m is None:
            # Get global command (as root), not as user, to avoid local overrides
            p = subprocess.Popen(
                ['/bin/bash', '--login', '-c', 'type -p ' + prog],
                stdout=subprocess.PIPE)
            bin = str(p.communicate()[0]).rstrip()
            assert os.access(bin, os.X_OK), 'unable to find command: ' + prog
            bin_file[k] = bin
        else:
            bin_file[k] = prog
    return bin_file[k]


def _chown(file_name, user):
    if _is_root():
        subprocess.check_call([_bin(user, 'chown'), user + ':' + user, file_name])


def _cmd(user, cmd):
    return cmd
#####TODO remove
    if is_list:
        cmd[0] = _bin(user, cmd[0])
    if _is_root():
        if is_list:
            cmd = ' '.join(cmd)
        cmd = ['/bin/su', '-', user, '-c', cmd]
    return cmd


def _computed_port(user, application):
####TODO os.geteuid
    p = pwd.getpwnam(user)
    return APP_PORT_BASE[application] + (p.pw_uid % PORT_MODULUS)


def _extract_port(user, application):
    cfg = _ipython_cfg(user, application)
    if not os.access(cfg, os.R_OK):
        return 0
    with open(cfg, 'r') as f:
        match = re.search(r'\nc\.NotebookApp\.port\s*=\s*(\d+)', f.read())
    if match is None:
        raise ValueError('c.NotebookApp.port not found in ', cfg)
    return int(match.group(1))


def _init_ipython_cfg(user, application):
    _write(
        user,
        _ipython_cfg(user, application),
        '''# ipython notebook for {app}
c = get_config()
c.NotebookApp.password = '{password}'
c.NotebookApp.port = {port}
c.NotebookApp.base_url = '/{user}/'
c.NotebookApp.base_kernel_url = '/{user}/'
c.NotebookApp.open_browser = False
c.IPKernelApp.pylab = None
''',
        {
            'app': application,
            'password': u'not initialized',
            'port': _computed_port(user, application),
            'user': user
        })

def _home(user):
    return os.path.expanduser('~' + user)


def _init_start(user, appdir, rc):
    _write(
        user,
        os.path.join(appdir, 'start.sh'),
        '''#!/bin/bash
cd $(dirname $0)
ipython notebook --profile=$(basename $(pwd))
''')
    _write(
        user,
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
        import distutils.version
        need = distutils.version.StrictVersion(IPython.__version__).version[0] < 3
    if not need:
        return
    import pip
    pip.main(['install', 'ipython[all]>=3'])


def _ipython_cfg(user, application):
    return os.path.join(
        _home(user),
        '.ipython',
        'profile_' + application,
        'ipython_notebook_config.py')


def _is_root():
    return os.getuid() == 0


def _running_on_port(user, application):
    port = _extract_port(user, application)
    if port == 0:
        return 0
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
    except socket.error as msg:
        return 0
    return port


def _write(user, file_name, to_format, keywords=None):
    s = re.sub(
        pattern=r'\n',
        repl=u'\n# Generated by ' + __file__ + ' on ' + datetime.datetime.now().ctime() + '\n',
        string=to_format,
        count=1)
    if keywords is not None:
        s = s.format(**keywords)
    with open(file_name, 'w') as f:
        f.write(s)
    _chown(file_name, user)
