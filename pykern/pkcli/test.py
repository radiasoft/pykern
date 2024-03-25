# -*- coding: utf-8 -*-
"""run test files in separate processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkio
from pykern import pksubprocess
from pykern import pkunit
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import os
import pykern.pkcli
import re
import sys


SUITE_D = "tests"
_COROUTINE_NEVER_AWAITED = re.compile("RuntimeWarning: coroutine .+ was never awaited")
_FAILED_ON_WARNINGS = "\nFAILED due to:\n"
_TEST_SKIPPED = re.compile(r"^.+\s+SKIPPED\s+\(.+\)$", flags=re.MULTILINE)
_TEST_PY = re.compile(r"_test\.py$")


_cfg = pkconfig.init(
    max_failures=(5, int, "maximum number of test failures before exit"),
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

    Writes failures to ``<base>_test.log``

    Args:
        args (str): test dirs, files, options
    Returns:
        str: passed=N if all passed, else raises `pkcli.Error`

    """
    return _Test(args).result


class _Test:
    def __init__(self, args):
        self.count = 0
        self.failures = []
        self._args(args)
        for t in self.paths:
            self.count += 1
            self._run_one(t)
            if len(self.failures) >= _cfg.max_failures:
                sys.stdout.write(
                    f"too many failures={len(self.failures)} aborting\n",
                )
                break
        if self.count == 0:
            pykern.pkcli.command_error("no tests found")
        self._assert_failures()
        self.result = f"passed={self.count}"

    def _args(self, tests):
        def _file(path):
            if self.skip_past:
                if self.skip_past in path:
                    self.skip_past = None
                return
            self.paths.append(path)

        def _find(paths):
            i = re.compile(r"(?:_work|_data)/")
            cwd = pkio.py_path()
            for t in _resolve_test_paths(paths, cwd):
                t = pkio.py_path(t)
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
                self.flags.extend(("-k", value))
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
        self.flags = []
        self.skip_past = None
        for t in tests:
            if "=" in t:
                _flag(*(t.split("=")))
            else:
                p.append(t)
        self.paths = []
        _find(p)

    def _assert_failures(self):
        if len(self.failures) <= 0:
            return
        # Avoid dumping too many test logs
        for o in self.failures[:5]:
            sys.stdout.write(pkio.read_text(o))
        sys.stdout.flush()
        pykern.pkcli.command_error(
            f"FAILED={len(self.failures)} passed={self.count - len(self.failures)}",
        )

    def _remove_work_dir(self, test_file):
        w = _TEST_PY.sub(pkunit.WORK_DIR_SUFFIX, test_file)
        if w != test_file:
            pkio.unchecked_remove(w)

    def _run_one(self, test_f):
        def _env(restartable):
            res = os.environ.copy()
            res.update(
                {
                    pkunit.TEST_FILE_ENV: str(pkio.py_path(test_f)),
                    pkunit.RESTARTABLE: "1" if restartable else "",
                }
            )
            return res

        def _except(exc, output, restartable):
            if isinstance(exc, RuntimeError):
                if "exit(5)" in exc.args[0]:
                    # 5 means test was skipped
                    # see http://doc.pytest.org/en/latest/usage.html#possible-exit-codes
                    return "skipped"
                if t and "exit(2)" in exc.args[0]:
                    # 2 means KeyboardInterrupt
                    # POSIT: pkunit.restart_or_fail uses this
                    return "restart"
            return _fail(output)

        def _skipped(ouput):
            return _TEST_SKIPPED.findall(ouput)

        def _fail(output):
            self.failures.append(output)
            return f"FAIL {output}"

        def _remove_incorrect_passing(content):
            for pattern in (
                r"=+ (\d+) passed.*=+",
                r"PASSED",
            ):
                content = _sub(content, pattern)
            return content


        def _sub(content, pattern):
            if re.search(pattern, content):
                return re.sub(pattern, "", content)
            return content

        def _try(output, restartable):
            try:
                sys.stdout.write(test_f)
                sys.stdout.flush()
                pksubprocess.check_call_with_signals(
                    ["py.test", "--tb=native", "-v", "-s", "-rs", test_f] + self.flags,
                    output=output,
                    env=_env(restartable),
                )
                o = pkio.read_text(output)
                if m :=  _COROUTINE_NEVER_AWAITED.search(o):
                    pkio.write_text(
                        output,
                        _remove_incorrect_passing(o) + _FAILED_ON_WARNINGS + m.group(0) + "\n",
                    )
                    return _fail(output)
                if _TEST_SKIPPED.search(o):
                    return "\n".join(["pass"] + _skipped(o))
                return "pass"
            except Exception as e:
                return _except(e, output, restartable)

        o = test_f.replace(".py", ".log")
        for t in range(4 if _cfg.restartable else 0, -1, -1):
            self._remove_work_dir(test_f)
            pkio.unchecked_remove(o)
            m = _try(o, t > 0)
            sys.stdout.write(" " + m + "\n")
            if m != "restart":
                return
