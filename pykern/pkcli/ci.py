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
_EXCLUDE_FILES = re.compile( f"/{test.SUITE_D}/.*{pkunit.DATA_DIR_SUFFIX}/|/{test.SUITE_D}/.*_work/|/{pksetup.PACKAGE_DATA}/|pkdebug")
_PRINT = re.compile('\s(pkdp)\(|\s(print)\(')


def check_prints(exclude=_EXCLUDE_FILES):
    """Recursively check repo for print and pkdp calls

    Args:
        exclude (regex): path pattern to exclude from check
    """
    from pykern import pkconst
    from pykern import pkio

    res = ""
    for f in pkio.walk_tree(pkio.py_path(), _FILE_TYPE):
        if re.search(exclude, str(f)):
            continue
        s = pkio.read_text(str(f))
        for i, l in enumerate(s.split('\n')):
            if re.search(_PRINT, l):
                res += f'{f.basename} pkdp/print on line: {i + 1} :-> {l}\n'
    if res:
        pkconst.builtin_print(res)
        raise AssertionError(f'\n{res}\nChecks fail due to pkdp/print present')


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