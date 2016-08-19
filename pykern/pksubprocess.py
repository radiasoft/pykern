# -*- coding: utf-8 -*-
u"""Wrapper for subprocess.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdp
import os
import signal
import subprocess
import threading

#: Caught signals
_SIGNALS = (signal.SIGTERM, signal.SIGINT)


def check_call_with_signals(cmd, output=None, env=None, msg=None):
    """Run cmd, writing to output.

    stdin is `os.devnull`.

    Passes SIGTERM and SIGINT on to the child process.

    Args:
        cmd (list): passed to subprocess verbatim
        output (file): where to write stdout and stderr
        env (dict): environment to use
    """
    assert _is_main_thread(), \
        'subprocesses which require signals need to be started in main thread'
    p = None
    prev_signal = dict([(sig, signal.getsignal(sig)) for sig in _SIGNALS])
    stderr = subprocess.STDOUT if output else None

    def signal_handler(sig, frame):
        if p:
            p.send_signal(sig)
        ps = prev_signal[sig]
        if ps in (None, signal.SIG_IGN, signal.SIG_DFL):
            return
        ps(sig, frame)

    pid = None
    try:
        for sig in _SIGNALS:
            signal.signal(sig, signal_handler)
        p = subprocess.Popen(
            cmd,
            stdin=open(os.devnull),
            stdout=output,
            stderr=stderr,
            env=env,
        )
        pid = p.pid
        if msg:
            msg('{}: started: {}', pid, cmd)
        rc = p.wait()
        p = None
        if rc != 0:
            raise RuntimeError('error exit({})'.format(rc))
        if msg:
            msg('{}: normal exit(0): {}', pid, cmd)
    except BaseException as e:
        if msg:
            msg('{}: exception: {} {}', pid, cmd, pkdexc())
        raise
    finally:
        for sig in _SIGNALS:
            signal.signal(sig, prev_signal[sig])
        if not p is None:
            if msg:
                msg('{}: terminating: {}', pid, cmd)
            p.terminate()


def _is_main_thread():
    """Need to determine if the main thread for setting signals

    Returns:
        bool: if running in the main thread
    """
    if hasattr(threading, 'main_thread'):
        # Python 3
        return threading.current_thread() == threading.main_thread()
    # Python 2: See http://stackoverflow.com/a/23207116
    return threading.current_thread().__class__ == threading._MainThread
