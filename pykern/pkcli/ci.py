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

def check_prints():
    """Recursively check repo for pkdp() calls"""
    from pykern import pksubprocess
    from pykern import pkio
    from pykern import pkcompat

    # proc = subprocess.Popen([
    #         "grep -r -l 'pkdp(' | grep '.py$'",
    #     ],
    #     shell=True,
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.PIPE
    # )

    # stdout, stderr = proc.communicate()
    # print("OUTPUT:\n", pkcompat.from_bytes(stdout), "ERR: ", stderr)

    p = pksubprocess.check_call_with_signals([
            # "grep -r -l 'pkdp(' | grep '.py$'",
            "grep",
            "-rl",
            "pkdp(",
            # "|",
            # "grep",
            # ".py$"
        ],
        out_var=True,
    )
    out, err = p

    res = [f for f in pkcompat.from_bytes(out).split('\n') if re.search(_FILE_TYPE, f)]
    print("FINAL RES: {}", res)

def run():
    """Run the continuous integration checks and tests
        * Checks formatting
        * Runs test suite
    """
    from pykern.pkcli import fmt, test
    from pykern import pkio

    fmt.diff(pkio.py_path())
    test.default_command()
