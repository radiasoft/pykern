"""Wrapper for subprocess.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkdebug import pkdc, pkdexc, pkdp, pkdlog
import os
import signal
import six
import subprocess
import threading

#: Caught signals
_SIGNALS = (signal.SIGTERM, signal.SIGINT)


def check_call_with_signals(cmd, output=None, env=None, msg=None, recursive_kill=False):
    """Run cmd, writing to output.

    stdin is `os.devnull`.

    Passes SIGTERM and SIGINT on to the child process. If `output`
    is a string, it will be opened in write ('w') mode.

    Args:
        cmd (list): passed to subprocess verbatim
        output (file or str): where to write stdout and stderr
        env (dict): environment to use
        recursive_kill (bool): EXPERIMENTAL: kill all process children, recursively
    """
    assert (
        _is_main_thread()
    ), "subprocesses which require signals need to be started in main thread"
    p = None
    prev_signal = dict([(sig, signal.getsignal(sig)) for sig in _SIGNALS])
    pid = None
    all_pids = set()

    def signal_handler(sig, frame):
        try:
            if p:
                p.send_signal(sig)
        except Exception:
            # Nothing we can do, still want to cascade
            pass
        finally:
            ps = prev_signal[sig]
            if ps in (None, signal.SIG_IGN, signal.SIG_DFL):
                return
            ps(sig, frame)

    def wait_pid():
        """Iteratively and recursively gather all children

        mpiexec sets a session, and doesn't cascade signals so processes
        can stay running after an exit.
        """
        # always SIGKILL the process we started
        all_pids.add(pid)
        if not recursive_kill:
            # simple process running
            return p.wait()

        import psutil, time

        # EXPERIMENTAL
        z = psutil.Process(pid)
        t = 0.1
        while True:
            all_pids.update(
                (c.pid for c in z.children(recursive=True)),
            )
            x, s = os.waitpid(pid, os.WNOHANG)
            if x != 0:
                break
            time.sleep(t)
            # first sleep is very fast, just in case a fast
            # process starts. Then polling less frequently
            # helps avoid thrashing, especially with mpi.
            t = 0.5
        return s

    try:
        stdout = output
        if isinstance(output, six.string_types):
            stdout = open(output, "w")
        stderr = subprocess.STDOUT if stdout else None
        for sig in _SIGNALS:
            signal.signal(sig, signal_handler)
        p = subprocess.Popen(
            cmd,
            stdin=open(os.devnull),
            stdout=stdout,
            stderr=stderr,
            env=env,
        )
        pid = p.pid
        if msg:
            msg("{}: started: {}", pid, cmd)
        s = wait_pid()
        p = None
        if s != 0:
            raise RuntimeError("error exit({})".format(s))
        if msg:
            msg("{}: normal exit(0): {}", pid, cmd)
    except Exception as e:
        if msg:
            msg("{}: exception: {} {}", pid, cmd, pkdexc())
        raise
    finally:
        for sig in _SIGNALS:
            signal.signal(sig, prev_signal[sig])
        if p is not None:
            if msg:
                msg("{}: terminating: {}", pid, cmd)
            try:
                p.terminate()
                time.sleep(0.1)
            except Exception:
                pass
        for x in all_pids:
            try:
                os.kill(x, signal.SIGKILL)
                # maybe we didn't catch all the children so try this
                os.killpg(x, signal.SIGKILL)
            except Exception:
                pass
        if stdout != output:
            stdout.close()


def _is_main_thread():
    """Need to determine if the main thread for setting signals

    Returns:
        bool: if running in the main thread
    """
    if hasattr(threading, "main_thread"):
        # Python 3
        return threading.current_thread() == threading.main_thread()
    # Python 2: See http://stackoverflow.com/a/23207116
    return threading.current_thread().__class__ == threading._MainThread
