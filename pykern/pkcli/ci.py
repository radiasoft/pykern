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


_FILE_TYPE = re.compile(r'.py$')
_EXCLUDE_FILES = re.compile(
    f"/{test.SUITE_D}/.*(?:{pkunit.DATA_DIR_SUFFIX}|{pkunit.WORK_DIR_SUFFIX})/"
    + f"|/{pksetup.PACKAGE_DATA}/"
    + r"|/pykern/pkdebug\.py$"
)
_PRINT = re.compile(r'(?:\s|^)(?:pkdp|print)\(')


def check_prints():
    """Recursively check repo for print and pkdp calls

    Args:
        exclude (regex): path pattern to exclude from check
    """
    from pykern import pkconst
    from pykern import pkio
    from pykern import pkcli

    res = []
    for f in pkio.walk_tree(pkio.py_path(), _FILE_TYPE):
        if re.search(_EXCLUDE_FILES, str(f)):
            if not (pkunit.module_under_test and '/ci_work/' in str(f)):
                pkconst.builtin_print('f:', f)
                continue
        for i, l in enumerate(pkio.read_text(f).split('\n'), start=1):
            if re.search(_PRINT, l):
                res.append(f'{f.basename}:{i} {l}')
    res = '\n'.join(res)
    if res:
        pkcli.command_error(res)


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
