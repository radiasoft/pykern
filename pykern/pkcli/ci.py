# -*- coding: utf-8 -*-
"""Functions for continuous integration

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp, pkdlog
from pykern import pkunit
from pykern.pkcli import test
from pykern import pksetup
import re


_FILE_TYPE = re.compile(r".py$")
_EXCLUDE_FILES = re.compile(
    f".*(?:{pkunit.DATA_DIR_SUFFIX}|{pkunit.WORK_DIR_SUFFIX})/"
    + f"|^\\w+/{pksetup.PACKAGE_DATA}/"
    + r"|pkdebug[^/]*\.py$"
    + r"|(?:^|/)\."
)
_PRINT = re.compile(r"(?:\s|^)(?:pkdp|print)\(")


def check_prints():
    """Recursively check repo for print and pkdp calls

    Args:
        exclude (regex): path pattern to exclude from check
    """
    from pykern import pkio
    from pykern import pkcli

    res = []
    p = pkio.py_path()
    for f in pkio.walk_tree(p, _FILE_TYPE):
        f = p.bestrelpath(f)
        if re.search(_EXCLUDE_FILES, f):
            continue
        for i, l in enumerate(pkio.read_text(f).split("\n"), start=1):
            if re.search(_PRINT, l):
                res.append(f"{f}:{i} {l}")
    if res:
        pkcli.command_error("{}", "\n".join(res))


def run():
    """Run the continuous integration checks and tests
    * Checks formatting
    * Runs test suite
    """
    from pykern.pkcli import fmt, test
    from pykern import pkio

    check_prints()
    fmt.diff(pkio.py_path())
    test.default_command()
