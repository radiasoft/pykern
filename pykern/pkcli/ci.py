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


def check_prints():
    """Recursively check repo for pring and pkdp calls"""
    from pykern import pkconst
    from pykern import pkio

    fails = False
    for f in pkio.walk_tree(pkio.py_path(), _FILE_TYPE):
        if _match(re.compile(_EXCLUDE_FILES), str(f)):
            continue

        s = pkio.read_text(str(f))
        for i, l in enumerate(s.split('\n')):
            if _match(_PRINT, l):
                fails = True
                pkconst.builtin_print(f'{f} pkdp/print on line: {i + 1} :-> {l}')
    return fails


def run():
    """Run the continuous integration checks and tests
        * Checks formatting
        * Runs test suite
    """
    from pykern.pkcli import fmt, test
    from pykern import pkio

    if check_prints():
        raise AssertionError('Checks fail due to pkdp/print present')
    fmt.diff(pkio.py_path())
    test.default_command()


def _match(regex, string):
    if re.search(regex, string):
        return True
    return False
