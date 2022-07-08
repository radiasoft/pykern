# -*- coding: utf-8 -*-
"""Continuous integration (CI) support

To execute all checks and tests in a CI script, use::

    pykern ci run

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
    + r"|^run/"
)
_PRINT = re.compile(r"(?:\s|^)(?:pkdp|print)\(")
_PRINT_OK = re.compile(r"^\s*#\s*(?:pkdp|print)\(")


def check_prints():
    """Recursively check repo for (naked) print and pkdp calls.

    See the
    `DesignHints <https://github.com/radiasoft/pykern/wiki/DesignHints#output-for-programmers-logging>_`
    wiki for an explanation of why this check is necessary.

    If you really need a print, use `pykern.pkconst.builtin_print`.

    Args:
        exclude (regex): path pattern to exclude from check
    ..
    """
    from pykern import pkio
    from pykern import pkcli

    res = []
    p = pkio.py_path()
    for f in pkio.walk_tree(p, _FILE_TYPE):
        f = p.bestrelpath(f)
        pkdp(f)
        if re.search(_EXCLUDE_FILES, f):
            continue
        for i, l in enumerate(pkio.read_text(f).split("\n"), start=1):
            if re.search(_PRINT, l) and not re.search(_PRINT_OK, l):
                res.append(f"{f}:{i} {l}")
    if res:
        pkcli.command_error("{}", "\n".join(res))


def run():
    """Run the continuous integration checks and tests:

    #. Runs `check_prints`
    #. Checks formatting
    #. Runs `pykern.pkcli.test.default_command`
    """
    from pykern.pkcli import fmt, test
    from pykern import pkio

    check_prints()
    fmt.diff(pkio.py_path())
    test.default_command()
