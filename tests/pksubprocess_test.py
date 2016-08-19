# -*- coding: utf-8 -*-
u"""Unit test for `pykern.pksubprocess`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_check_call_with_signals():
    from pykern import pksubprocess
    from pykern import pkunit
    import os
    import signal

    messages = []
    def msg(*args):
        s = args[0]
        messages.append(s.format(*args[1:]))

    signals = []
    def signal_handler(sig, frame):
        signals.append(sig)

    with pkunit.save_chdir_work():
        with open('true.out', 'w+') as o:
            pksubprocess.check_call_with_signals(['true'], output=o)
            o.seek(0)
            actual = o.read()
            assert '' == actual, \
                'Expecting empty output "{}"'.format(actual)

        with open('echo.out', 'w+') as o:
            messages = []
            tag = 'xyzzy'
            pksubprocess.check_call_with_signals(['echo', tag], output=o, msg=msg)
            o.seek(0)
            actual = o.read()
            assert tag in actual, \
                '"{}" not in output "{}"'.format(tag, actual)
            assert 'started' in messages[0], \
                '"started" not in messages[0] "{}"'.format(messages[0])
            assert 'normal exit' in messages[1], \
                '"normal exit" not in messages[1] "{}"'.format(messages[1])

        with open('kill.out', 'w+') as o:
            messages = []
            signals = []
            signal.signal(signal.SIGTERM, signal_handler)
            with open('kill.sh', 'w') as f:
                f.write('kill -TERM {}\nsleep 10'.format(os.getpid()))
            cmd = ['sh', 'kill.sh']
            with pytest.raises(RuntimeError):
                pksubprocess.check_call_with_signals(cmd, output=o, msg=msg)
            o.seek(0)
            actual = o.read()
            assert '' == actual, \
                'Expecting empty output "{}"'.format(actual)
            assert signal.SIGTERM in signals, \
                '"SIGTERM" not in signals "{}"'.format(signals)
            assert 'error exit' in messages[1], \
                '"error exit" not in messages[1] "{}"'.format(messages[1])
