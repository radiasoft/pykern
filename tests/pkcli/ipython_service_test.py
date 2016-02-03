# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkcli.ipython_service`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp

import pytest
import subprocess

pytest.importorskip('IPython')
x = ''
try:
    x = subprocess.Popen(
        ['screen', '-v'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout.read()
except:
    pass
if ' version ' not in x:
    pytest.skip('ipython_service needs "screen"')

import os
import os.path
import re
import requests
import signal
import time


from pykern import pkio
from pykern import pkunit
from pykern.pkcli import ipython_service

_UID = 99
_USER = 'xyz'
_APP = 'ips_test'
_PORT = ipython_service.APP_PORT_BASE[_APP] + _UID
_SCREEN_PID_RE = re.compile(r'([0-9]+)\.ipython-{}'.format(_APP))

def test_1(monkeypatch):
    """Validate init, start, and stop"""
    with pkunit.save_chdir_work() as home:
        monkeypatch.setenv('HOME', home)
        monkeypatch.setenv('UID', str(_UID))
        monkeypatch.setenv('USER', _USER)
        _init(home, monkeypatch)
        _start()
        _stop()
        _password(monkeypatch)


def test_deviance(monkeypatch):
    with pkunit.save_chdir_work():
        monkeypatch.setenv('HOME', os.getcwd())
        pid=os.fork()
        if not pid:
            ipython_service.dev(port=_PORT)
            raise AssertionError('failed to start service')
        _request()
        os.kill(pid, signal.SIGKILL)
        for _ in range(3):
            try:
                os.waitpid(pid, os.WNOHANG)
                return
            except OSError:
                time.sleep(1)
        raise AssertionError('unable to kill ipython pid={}'.format(pid))


def _init(home, monkeypatch):
    """Tests init"""
    import IPython
    monkeypatch.setattr(IPython, '__version__', '2.1')
    import pip
    save = []
    def do_save(*args, **kwargs):
        save.append({'args': args, 'kwargs': kwargs})
    monkeypatch.setattr(pip, 'main', do_save)
    ipython_service.init(_APP)
    assert re.search(r'ipython.*3', save[0]['args'][0][1]), \
        'pip.main is called to install version 3'
    with pkio.save_chdir(_APP):
        assert os.path.isfile('.startrc')
        assert os.path.isfile('start.sh')


def _password(monkeypatch):
    pw = 'big-secret'
    import IPython
    monkeypatch.setattr(IPython.lib.security, 'passwd', lambda: pw)
    ipython_service.password(_APP)
    t = pkio.read_text('.ipython/profile_{}/ipython_notebook_config.py'.format(_APP))
    assert re.search(r"password = '{}'".format(pw), t), \
        'ipython config should be changed by password()'


def _request():
    url = 'http://localhost:{}/{}'.format(_PORT, _USER)
    for tries in range(4):
        time.sleep(1)
        try:
            return requests.get(url)
        except requests.exceptions.ConnectionError:
            pass
    raise AssertionError('{}: unable to connect to server'.format(url))


def _screen_kill():
    seen = {}
    while True:
        pid = _screen_pid()
        if not pid:
            break
        if pid not in seen:
            seen[pid] = signal.SIGTERM
        else:
            assert seen[pid] != signal.SIGKILL, \
                '{}: unable to kill pid of screen'.format(pid)
            time.sleep(1)
            seen[pid] = signal.SIGKILL
        os.kill(int(pid), signal.SIGTERM)


def _screen_pid():
    p = subprocess.Popen(
        ['screen', '-list'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out, _ = p.communicate()
    m = _SCREEN_PID_RE.search(out)
    return m.group(1) if m else None


def _start():
    """Tests start"""
    _screen_kill()
    ipython_service.start(_APP)
    os.system('ps -ax')
    r = _request()
    assert requests.codes.ok == r.status_code, \
        'Screen should start and respond to http requests'
    try:
        ipython_service.start(_APP)
    except Exception as e:
        assert re.search(r'already running', str(e)), \
            'Two calls to start should result in an exception'
        return
    raise AssertionError('Second call to start did not fail')


def _stop():
    assert _screen_pid(), \
        'screen must be running'
    ipython_service.stop(_APP)
    for tries in range(3):
        if not _screen_pid():
            tries = None
            break
        time.sleep(1)
    if tries:
        assert not _screen_pid(), \
            'screen is still running'
    assert re.search('not running', ipython_service.stop(_APP)), \
        'Two calls to stop should be ok, but result in a message'
