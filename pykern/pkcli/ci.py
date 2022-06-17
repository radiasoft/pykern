# -*- coding: utf-8 -*-
"""Functions for continuous integration

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from cgitb import reset
from pykern.pkdebug import pkdp, pkdlog
import pykern.pksubprocess
import re
import subprocess


_FILE_TYPE = re.compile(r'.py$')

"print("
def check_prints():
    """Recursively check repo for pkdp() calls"""
    from pykern import pksubprocess
    from pykern import pkio
    from pykern import pkcompat

    out, err = pksubprocess.check_call_with_signals([
            # "grep -r -l 'pkdp(' | grep '.py$'",
            "grep",
            "-rl",
            "pkdp(\|print(",
            # "/|",
            # "grep",
            # ".py$"
        ],
        out_var=True,
    )
    # print('out', out)
    res = [f for f in pkcompat.from_bytes(out).split('\n') if _fits(f)]
    for r in res:
        print(r)
    # print(pkcompat.from_bytes(out))

def run():
    """Run the continuous integration checks and tests
        * Checks formatting
        * Runs test suite
    """
    from pykern.pkcli import fmt, test
    from pykern import pkio

    fmt.diff(pkio.py_path())
    test.default_command()


def _fits(string):
    # print(string)
    # print(re.search(re.compile('builtin_print\('), string))
    if re.search(_FILE_TYPE, string):
        return True
    return False
