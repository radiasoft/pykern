# -*- coding: utf-8 -*-
u"""run test files in separate processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict


def default_command(*tests):
    """Run tests one at a time with py.test.

    Searches in ``tests`` sub-directory if not provide a
    list of tests.

    Writes failures to ``<base>_test.log``

    Args:
        tests (str): name of tests [all files ``tests``]
    Returns:
        str: passed=N if all passed, else raises `argh.CommandError`
    """
    from pykern import pkcli
    from pykern import pksubprocess
    from pykern import pkio
    from pykern import pkunit
    import os
    import sys

    e = PKDict(os.environ)
    n = 0
    f = 0
    for t in _find(tests):
        n += 1
        o = t.replace('.py', '.log')
        m = 'pass'
        try:
            sys.stdout.write(t)
            sys.stdout.flush()
            pksubprocess.check_call_with_signals(
                ('py.test', '--tb=native', t),
                output=o,
                env=PKDict(
                    os.environ,
                ).pkupdate({'pkunit.TEST_FILE_ENV': t})
            )
        except Exception:
            m = 'FAIL {}'.format(o)
            f += 1
        sys.stdout.write(' ' + m + '\n')
    if f > 0:
        if n == 1:
            sys.stdout.write(pkio.read_text(o))
        sys.stdout.flush()
        pkcli.command_error('FAILED={} passed={}\n'.format(f, n - f))
    return 'passed={}'.format(n)


def _find(tests):
    from pykern import pkio
    import re

    i = re.compile(r'(?:_work|_data)/')
    res = []
    cwd = pkio.py_path()
    for t in tests or ('tests',):
        t = pkio.py_path(t)
        if t.check(file=True):
            res.append(str(cwd.dirpath().bestrelpath(p)))
            continue
        for p in pkio.walk_tree(t, re.compile(r'_test\.py$')):
            p = str(cwd.bestrelpath(p))
            if not i.search(p):
                res.append(p)
    return res