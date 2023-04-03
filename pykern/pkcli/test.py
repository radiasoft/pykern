# -*- coding: utf-8 -*-
"""run test files in separate processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import pykern.pkcli
import re


SUITE_D = "tests"

_TEST_PY = re.compile(r"_test\.py$")


_cfg = None


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
        from pykern import pkconfig
        from pykern import pksubprocess
        from pykern.pkcli import fmt
        from pykern import pkio
        from pykern import pkunit
        import os
        import sys

        global _cfg
        if not _cfg:
            _cfg = pkconfig.init(
                max_failures=(5, int, "maximum number of test failures before exit"),
                max_restarts=(
                    5,
                    int,
                    "maximum number of test restarts before forcing failure",
                ),
            )
        n = 0
        f = []
        c = []
        self._args(args)
        for t in self.paths:
            n += 1
            o = t.replace(".py", ".log")
            self._remove_work_dir(t)
            m = "pass"
            try:
                sys.stdout.write(t)
                sys.stdout.flush()
                pksubprocess.check_call_with_signals(
                    ["py.test", "--tb=native", "-v", "-s", "-rs", t] + self.flags,
                    output=o,
                    env=PKDict(
                        os.environ,
                    ).pkupdate({pkunit.TEST_FILE_ENV: str(pkio.py_path(t))}),
                )
            except Exception as e:
                if isinstance(e, RuntimeError) and "exit(5)" in e.args[0]:
                    # 5 means test was skipped
                    # see http://doc.pytest.org/en/latest/usage.html#possible-exit-codes
                    m = "skipped"
                else:
                    m = "FAIL {}".format(o)
                    f.append(o)
            sys.stdout.write(" " + m + "\n")
            if len(f) >= _cfg.max_failures:
                sys.stdout.write("too many failures={} aborting\n".format(len(f)))
                break
        if n == 0:
            pykern.pkcli.command_error("no tests found")
        if len(f) > 0:
            # Avoid dumping too many test logs
            for o in f[:5]:
                sys.stdout.write(pkio.read_text(o))
            sys.stdout.flush()
            pykern.pkcli.command_error("FAILED={} passed={}".format(len(f), n - len(f)))
        self.result = "passed={}".format(n)

    def _args(self, tests):
        def _file(path):
            if self.skip_past:
                if self.skip_past in path:
                    self.skip_past = None
                return
            self.paths.append(path)

        def _find(paths):
            from pykern import pkio

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

        paths = []
        self.flags = []
        self.skip_past = None
        for t in tests:
            if "=" in t:
                _flag(*(t.split("=")))
            else:
                paths.append(t)
        self.paths = []
        _find(paths)

    def _remove_work_dir(self, test_file):
        from pykern import pkio
        from pykern import pkunit

        w = _TEST_PY.sub(pkunit.WORK_DIR_SUFFIX, test_file)
        if w != test_file:
            pkio.unchecked_remove(w)
