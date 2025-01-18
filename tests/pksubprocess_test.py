# -*- coding: utf-8 -*-
"""Unit test for `pykern.pksubprocess`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import os
import pytest
import shutil


@pytest.mark.skipif(
    not shutil.which("setsid"),
    reason="no setsid command",
)
def test_check_call_with_signals():
    from pykern import pksubprocess
    from pykern import pkunit, pkcompat, pkdebug
    import os
    import signal
    import subprocess
    import time

    messages = []

    def msg(*args):
        s = args[0]
        messages.append(s.format(*args[1:]))

    signals = []

    def signal_handler(sig, frame):
        signals.append(sig)

    with pkunit.save_chdir_work():
        with open("true.out", "w+") as o:
            pksubprocess.check_call_with_signals(["true"], output=o)
            o.seek(0)
            actual = o.read()
            assert "" == actual, 'Expecting empty output "{}"'.format(actual)

        with open("echo.out", "w+") as o:
            messages = []
            tag = "xyzzy"
            pksubprocess.check_call_with_signals(["echo", tag], output=o, msg=msg)
            o.seek(0)
            actual = o.read()
            assert tag in actual, '"{}" not in output "{}"'.format(tag, actual)
            assert "started" in messages[0], '"started" not in messages[0] "{}"'.format(
                messages[0]
            )
            assert (
                "normal exit" in messages[1]
            ), '"normal exit" not in messages[1] "{}"'.format(messages[1])

        with open("kill.out", "w+") as o:
            messages = []
            signals = []
            signal.signal(signal.SIGTERM, signal_handler)
            with open("kill.sh", "w") as f:
                # Need to wait before sending signal, because subprocess needs to allow
                # this process (parent) to run
                f.write(
                    f"""
sleep .2
kill -TERM {os.getpid()}
sleep 5
echo FAIL
"""
                )
            cmd = ["sh", "kill.sh"]
            exc = None
            try:
                pksubprocess.check_call_with_signals(cmd, output=o, msg=msg)
            except RuntimeError as e:
                exc = e
            except BaseException as e:
                pkunit.pkfail("unexpected exception={}", e)
            o.seek(0)
            actual = o.read()
            pkunit.pkeq("", actual)
            pkunit.pkok(
                signal.SIGTERM in signals, '"SIGTERM" not in signals "{}"', signals
            )
            pkunit.pkre("error exit", messages[1])
            if exc is None:
                pkunit.pkfail("exception was not raised")

        with open("kill.out", "w+") as o:
            messages = []
            signals = []
            signal.signal(signal.SIGTERM, signal_handler)
            with open("kill.sh", "w") as f:
                f.write(
                    f"""
setsid bash -c "sleep 1; echo FAIL; setsid sleep 1313 & disown" &
disown
sleep .2
kill -TERM {os.getpid()}
sleep 5
echo FAIL
"""
                )
            cmd = ["bash", "kill.sh"]
            exc = None
            try:
                pksubprocess.check_call_with_signals(
                    cmd,
                    output=o,
                    msg=msg,
                    recursive_kill=True,
                )
            except RuntimeError as e:
                exc = e
            except BaseException as e:
                pkunit.pkfail("unexpected exception={}", e)
            time.sleep(2)
            o.seek(0)
            actual = o.read()
            assert "" == actual, 'Expecting empty output "{}"'.format(actual)
            assert signal.SIGTERM in signals, '"SIGTERM" not in signals "{}"'.format(
                signals
            )
            assert (
                "error exit" in messages[1]
            ), '"error exit" not in messages[1] "{}"'.format(messages[1])
            p = pkcompat.from_bytes(
                subprocess.check_output(
                    ["ps", "axfj"],
                    stdin=open(os.devnull),
                    stderr=subprocess.STDOUT,
                ),
            )
            assert "sleep 1313" not in p, "sleep did not terminate: {}".format(p)
