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
    from pykern import pkconfig
    from pykern import pksubprocess
    from pykern.pkcli import fmt
    from pykern import pkio
    from pykern import pkunit
    import os
    import sys

    cfg = pkconfig.init(
        max_failures=(5, int, "maximum number of test failures before exit"),
    )
    e = PKDict(os.environ)
    n = 0
    f = []
    c = []
    paths, flags = _args(args)
    for t in paths:
        n += 1
        o = t.replace(".py", ".log")
        _remove_work_dir(t)
        m = "pass"
        try:
            sys.stdout.write(t)
            sys.stdout.flush()
            pksubprocess.check_call_with_signals(
                ["py.test", "--tb=native", "-v", "-s", "-rs", t] + flags,
                output=o,
                env=PKDict(
                    os.environ,
                ).pkupdate({pkunit.TEST_FILE_ENV: str(pkio.py_path(t))}),
                # TODO(robnagler) not necessary
                #                recursive_kill=True,
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
        if len(f) >= cfg.max_failures:
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
    return "passed={}".format(n)


def _args(tests):
    paths = []
    flags = []
    s = None
    for t in tests:
        if "=" in t:
            a, b = t.split("=")
            if len(b) <= 0:
                pykern.pkcli.command_error(f"empty value for option={t}")
            elif a == "case":
                flags.extend(("-k", b))
            elif a == "skip_past":
                s = b
            else:
                pykern.pkcli.command_error(f"unsupported option={t}")
        else:
            paths.append(t)
    return _find(paths, s), flags


def _find(paths, skip_past):
    from pykern import pkio

    res = []

    def _file(path):
        nonlocal skip_past
        if skip_past:
            if skip_past in path:
                skip_past = None
            return
        res.append(path)

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
    return res


def _remove_work_dir(test_file):
    from pykern import pkio
    from pykern import pkunit

    w = _TEST_PY.sub(pkunit.WORK_DIR_SUFFIX, test_file)
    if w != test_file:
        pkio.unchecked_remove(w)


def _resolve_test_paths(paths, current_dir):
    if not paths:
        p = current_dir
        if p.basename != SUITE_D:
            p = SUITE_D
        paths = (p,)
    return paths
