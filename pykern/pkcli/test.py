# -*- coding: utf-8 -*-
u"""run test files in separate processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict


def default_command(*args):
    """Run tests one at a time with py.test.

    Searches in ``tests`` sub-directory if not provided a
    list of tests.

    Arguments are directories or files, which are searched for _test.py
    files.

    An argument which is ``case=<pattern>``, is passed to pytest
    as ``-k <pattern>``.

    Writes failures to ``<base>_test.log``

    Args:
        args (str): test dirs, files, options
    Returns:
        str: passed=N if all passed, else raises `pkcli.Error`
    """
    from pykern import pkcli
    from pykern import pkconfig
    from pykern import pksubprocess
    from pykern import pkio
    from pykern import pkunit
    import os
    import sys

    cfg = pkconfig.init(
        max_failures=(5, int, 'maximum number of test failures before exit'),
    )
    e = PKDict(os.environ)
    n = 0
    f = []
    c = []
    paths, flags = _args(args)
    for t in paths:
        n += 1
        o = t.replace('.py', '.log')
        m = 'pass'
        try:
            sys.stdout.write(t)
            sys.stdout.flush()
            pksubprocess.check_call_with_signals(
                ['py.test', '--tb=native', '-v', '-s', '-rs', t] + flags,
                output=o,
                env=PKDict(
                    os.environ,
                ).pkupdate({pkunit.TEST_FILE_ENV: t}),
#TODO(robnagler) not necessary
#                recursive_kill=True,
            )
        except Exception as e:
            if isinstance(e, RuntimeError) and 'exit(5)' in e.args[0]:
                # 5 means test was skipped
                # see http://doc.pytest.org/en/latest/usage.html#possible-exit-codes
                m = 'skipped'
            else:
                m = 'FAIL {}'.format(o)
                f.append(o)
        sys.stdout.write(' ' + m + '\n')
        if len(f) >= cfg.max_failures:
            sys.stdout.write('too many failures={} aborting\n'.format(len(f)))
            break
    if n == 0:
        pkcli.command_error('no tests found')
    if len(f) > 0:
        # Avoid dumping too many test logs
        for o in f[:5]:
            sys.stdout.write(pkio.read_text(o))
        sys.stdout.flush()
        pkcli.command_error('FAILED={} passed={}'.format(len(f), n - len(f)))
    return 'passed={}'.format(n)


def _args(tests):
    paths = []
    flags = []
    for t in tests:
        if '=' in t:
            a, b = t.split('=')
            if a == 'case':
                flags.extend(('-k', b))
            else:
                pkcli.command_error('unsupported option={}'.format(t))
        else:
            paths.append(t)
    return _find(paths), flags


def _find(paths):
    from pykern import pkio
    import re

    i = re.compile(r'(?:_work|_data)/')
    res = []
    cwd = pkio.py_path()
    for t in paths or ('tests',):
        t = pkio.py_path(t)
        if t.check(file=True):
            res.append(str(cwd.bestrelpath(t)))
            continue
        for p in pkio.walk_tree(t, re.compile(r'_test\.py$')):
            p = str(cwd.bestrelpath(p))
            if not i.search(p):
                res.append(p)
    return res
