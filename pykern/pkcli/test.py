"""run test files in separate processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkconst
from pykern import pkio
from pykern import pkunit
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import os
import pykern.pkcli
import re
import signal
import subprocess
import sys
import time


SUITE_D = "tests"
_COROUTINE_NEVER_AWAITED = re.compile(
    "(.+ coroutine \S+ was never awaited.*)", flags=re.MULTILINE
)
_TEST_SKIPPED = re.compile(r"^.+\s+SKIPPED\s+\(.+\)$", flags=re.MULTILINE)
_TEST_PY = re.compile(r"_test\.py$")

_FAIL_MSG = "FAIL"

_PASS_MSG = "pass"

_SKIPPED_MSG = "skipped"

_MAX_RESTARTS = 3

_RESTART_MSG = "restart"

_START_MSG = "start"

_WAIT_LOOP_SLEEP = 0.1

_cfg = pkconfig.init(
    ignore_warnings=(False, bool, "override pytest's output of all warnings"),
    max_failures=(
        5,
        pkconfig.parse_positive_int,
        "maximum number of test failures before exit",
    ),
    max_procs=(1, pkconfig.parse_positive_int, "maximum number of parallel test runs"),
    restartable=(
        False,
        bool,
        "allow pkunit.restart_or_fail to restart",
    ),
)


def default_command(*args):
    """Run tests one at a time with py.test.

    Searches in ``tests`` sub-directory if not provided a
    list of tests or not in tests/ already

    Arguments are directories or files, which are searched for _test.py
    files.

    An argument which is ``case=<pattern>``, is passed to pytest
    as ``-k <pattern>``.

    ``skip_past=<last_to_ignore>`` causes collection to ignore all
    files up to and including ``<last_to_ignore>``` (may be partial
    match of the test file).

    ``max_procs=2`` starts two cases simultaneously. Default is 1,
    or config value `PYKERN_PKCLI_TEST_MAX_PROCS` if set.

    Writes failures to ``<base>_test.log``

    Args:
        args (str): test dirs, files, options
    Returns:
        str: passed=N if all passed, else raises `pkcli.Error`

    """
    return _Runner(args).result


class _Case:
    def __init__(self, rel_path, runner):
        super().__init__()
        self.runner = runner
        self.rel_path = rel_path
        self.abs_path = pkio.py_path(rel_path)
        self.tries = _MAX_RESTARTS if _cfg.restartable else 1
        self.run()

    def is_done(self, aborting):
        if (e := self.process.poll()) is None:
            return None
        return self._exit(e, aborting)

    def pkdebug_str(self):
        return f"{self.__class__.__name__}({self.rel_path})"

    def run(self):
        self.tries -= 1
        self.restartable = self.tries > 0
        self.process = self._start()

    def _exit(self, returncode, aborting):
        def _msg():
            if 0 == returncode:
                return _PASS_MSG
            if 5 == returncode:
                # 5 means test was skipped
                # see http://doc.pytest.org/en/latest/usage.html#possible-exit-codes
                return _SKIPPED_MSG
            if not aborting and self.restartable and 2 == returncode:
                # 2 means KeyboardInterrupt
                # POSIT: pkunit.restart_or_fail uses this
                return _RESTART_MSG
            return _FAIL_MSG

        def _skipped(ouput):
            return _TEST_SKIPPED.findall(ouput)

        self.runner.signal_cascade.processes.remove(self.process)
        self.process = None
        o = pkio.read_text(self.output_path)
        self.skipped = _skipped(o) if _TEST_SKIPPED.search(o) else []
        if m := re.findall(_COROUTINE_NEVER_AWAITED, o):
            with self.output_path.open(mode="a") as f:
                f.write("".join(f"ERROR: {x}\n" for x in m))
                # never restartable, it's always a defect
                return _FAIL_MSG
        self.exit = _msg()
        return self.exit

    def _start(self):
        def _env():
            res = os.environ.copy()
            res.update(
                {
                    pkunit.TEST_FILE_ENV: str(self.abs_path),
                    pkunit.RESTARTABLE: "1" if self.restartable else "",
                }
            )
            return res

        def _ignore_warnings():
            if not _cfg.ignore_warnings:
                return []
            rv = []
            for w in (
                # https://docs.python.org/3/library/warnings.html#default-warning-filter
                "DeprecationWarning",
                "PendingDeprecationWarning",
                "ImportWarning",
                "ResourceWarning",
            ):
                rv.extend(("-W", f"ignore::{w}"))
            return rv

        def _remove_work_dir():
            w = _TEST_PY.sub(pkunit.WORK_DIR_SUFFIX, self.rel_path)
            if w != self.rel_path:
                pkio.unchecked_remove(w)

        def _process():
            c = (
                ["pytest"]
                + _ignore_warnings()
                + [
                    "--tb=native",
                    "-v",
                    "-s",
                    "-rs",
                    self.rel_path,
                ]
                + self.runner.pytest_flags
            )
            v = _env()
            with self.output_path.open("w") as o, open(os.devnull) as i:
                return subprocess.Popen(
                    c,
                    stdin=i,
                    stdout=o,
                    stderr=subprocess.STDOUT if o else None,
                    env=v,
                    close_fds=True,
                )

        self.output_path = self.abs_path.new(ext=".log")
        _remove_work_dir()
        pkio.unchecked_remove(self.output_path)
        rv = _process()
        self.runner.signal_cascade.processes.add(rv)
        return rv


class _Runner:
    def __init__(self, args):

        def _too_many_failures():
            if len(self.failures) < _cfg.max_failures:
                return False
            self._info(
                None,
                [
                    f"too many failures={len(self.failures)} aborting"
                    + (
                        "; waiting for processes to finish"
                        if self.max_procs > 1 and self.cases
                        else ""
                    ),
                ],
            )
            return True

        self._args(args)
        if not self.rel_paths:
            pykern.pkcli.command_error("no tests found")
        c = 0
        self.failures = []
        self.cases = set()
        with _SignalCascade() as self.signal_cascade:
            for p in self.rel_paths:
                c += 1
                self._run(p)
                if a := _too_many_failures():
                    break
            while self._wait_for_one(aborting=a):
                pass
        self._assert_failures(self.failures, c)
        self.result = f"passed={c}"

    def _args(self, tests):
        def _file(path):
            if self.skip_past:
                if self.skip_past in path:
                    self.skip_past = None
                return
            self.rel_paths.append(path)

        def _find(paths):
            i = re.compile(r"(?:_work|_data)/")
            cwd = pkio.py_path()
            for t in _resolve_test_paths(paths, cwd):
                t = pkio.py_path(t)
                if not t.exists():
                    pykern.pkcli.command_error("test={} does not exist", t)
                if t.check(file=True):
                    _file(str(cwd.bestrelpath(t)))
                    continue
                for p in pkio.walk_tree(t, _TEST_PY):
                    p = str(cwd.bestrelpath(p))
                    if not i.search(p):
                        _file(p)

        def _flag(name, value):
            if len(value) <= 0:
                pykern.pkcli.command_error(f"empty value for option={name}")
            elif name == "case":
                self.pytest_flags.extend(("-k", value))
            elif name == "max_procs":
                try:
                    self.max_procs = int(value)
                except Exception:
                    self.max_procs = -1
                if self.max_procs <= 0:
                    pykern.pkcli.command_error(
                        f"max_procs={value} must be a positive integer"
                    )
            elif name == "skip_past":
                if self.skip_past:
                    pykern.pkcli.command_error(
                        f"skip_past={value} passed twice (skip_past={self.skip_past})"
                    )
                self.skip_past = value
            else:
                pykern.pkcli.command_error(f"unsupported option={name}")

        def _resolve_test_paths(paths, current_dir):
            if not paths:
                p = current_dir
                if p.basename != SUITE_D:
                    p = SUITE_D
                paths = (p,)
            return paths

        p = []
        self.pytest_flags = []
        self.max_procs = _cfg.max_procs
        self.skip_past = None
        for t in tests:
            if "=" in t:
                _flag(*(t.split("=")))
            else:
                p.append(t)
        self.rel_paths = []
        _find(p)

    def _assert_failures(self, failures, count):
        if len(failures) <= 0:
            return
        # Avoid dumping too many test logs
        for c in failures[: _cfg.max_failures]:
            self._info(None, [pkio.read_text(c.output_path)])
        pykern.pkcli.command_error(
            f"FAILED={len(failures)} passed={count - len(failures)}",
        )

    def _exit(self, case, msg):
        if rv := msg != _RESTART_MSG:
            self.cases.remove(case)
            if msg == _FAIL_MSG:
                self.failures.append(case)
        self._info(case, [msg] + case.skipped)
        case.skipped = None
        return rv

    def _info(self, case, lines):
        if case is None:
            if not lines[-1].endswith("\n"):
                # other output on its own line, ensure newline at end
                lines[-1] += "\n"
        else:
            if lines[0] == _FAIL_MSG:
                # add the failure context
                lines[0] += f" {case.output_path}"
            if self.max_procs > 1:
                # line by line when multiprocess
                lines[0] = case.rel_path + " " + lines[0]
            elif lines[0] == _START_MSG:
                # starting a case
                lines[0] = case.rel_path
            else:
                # completing a case
                lines[0] = " " + lines[0]
                lines[-1] += "\n"
        o = "\n".join(lines)
        if self.max_procs > 1 and not o.endswith("\n"):
            o += "\n"
        pkconst.builtin_print(o, end="")
        # TODO(robnagler) is this necessary?
        sys.stdout.flush()

    def _run(self, rel_path):
        c = _Case(rel_path, self)
        self.cases.add(c)
        self._info(c, [_START_MSG])
        if len(self.cases) >= self.max_procs:
            self._wait_for_one()

    def _wait_for_one(self, aborting=False):
        while self.cases:
            for c in self.cases:
                if (m := c.is_done(aborting)) is None:
                    continue
                if self._exit(c, m):
                    return True
                c.run()
            time.sleep(_WAIT_LOOP_SLEEP)
        return False


class _SignalCascade:
    _SIGNALS = (signal.SIGTERM, signal.SIGINT)
    _IGNORE_HANDLERS = frozenset((None, signal.SIG_IGN, signal.SIG_DFL))

    def __init__(self):
        self.processes = set()

    def __enter__(self):
        self._prev_handlers = PKDict({s: signal.getsignal(s) for s in self._SIGNALS})
        for s in self._prev_handlers.keys():
            signal.signal(s, self._handler)
        return self

    def __exit__(self, type, value, traceback):
        for s, h in self._prev_handlers.items():
            signal.signal(s, h)

    def _handler(self, sig, frame):
        for p in self.processes:
            try:
                p.send_signal(sig)
            except Exception:
                pass
        if (h := self._prev_handlers.get(sig)) not in self._IGNORE_HANDLERS:
            h(sig, frame)
