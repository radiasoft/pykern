# -*- coding: utf-8 -*-
"""Continuous integration (CI) support

To execute all checks and tests in a CI script, use::

    pykern ci run

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcli
from pykern import pkio
from pykern import pksetup
from pykern import pkunit
from pykern.pkdebug import pkdp, pkdlog
import re

_CHECK_EOF_NEWLINE_EXCLUDE_FILES = re.compile(
    r"/ext/|node_modules/|^run/|tests/[\w\d/]+_work/|^venv/"
)
_CHECK_EOF_NEWLINE_FILE_EXTS = re.compile(r"\.(html|jinja|js|json|md|py|tsx|yml)$")
_CHECK_PRINTS_EXCLUDE_FILES = re.compile(
    f".*(?:{pkunit.DATA_DIR_SUFFIX}|{pkunit.WORK_DIR_SUFFIX})/"
    + f"|^\\w+/{pksetup.PACKAGE_DATA}/"
    + r"|pkdebug[^/]*\.py$"
    + r"|(?:^|/)\."
    + r"|^run/"
    + r"|^venv/"
)
_CHECK_PRINTS_FILE_EXTS = re.compile(r".py$")
_PRINT = re.compile(r"(?:\s|^)(?:pkdp|print)\(")
_PRINT_OK = re.compile(r"^\s*#\s*(?:pkdp|print)\(")


def check_eof_newline():
    """Recursively check repo for files missing newline at end of file.

    Files matching _CHECK_EOF_NEWLINE_FILE_EXTS and not matching
    _CHECK_EOF_NEWLINE_EXCLUDE_FILES will be checked.
    """

    def _error(msg):
        pkcli.command_error("check_eof_newline: {}", msg)

    res = []
    p = pkio.py_path()
    n = 0
    for f in pkio.walk_tree(p, _CHECK_EOF_NEWLINE_FILE_EXTS):
        f = p.bestrelpath(f)
        if re.search(_CHECK_EOF_NEWLINE_EXCLUDE_FILES, f):
            continue
        n += 1
        l = pkio.read_text(f).split("\n")
        if l[-1] != "":
            res.append(f"{f}")
    if n == 0:
        _error("no files found")
    if res:
        _error("\n".join(res))


def check_prints():
    """Recursively check repo for (naked) print and pkdp calls.

    See the
    `DesignHints <https://github.com/radiasoft/pykern/wiki/DesignHints#output-for-programmers-logging>_`
    wiki for an explanation of why this check is necessary.

    If you really need a print, use `pykern.pkconst.builtin_print`.
    """

    def _error(msg):
        pkcli.command_error("check_prints: {}", msg)

    res = []
    p = pkio.py_path()
    n = 0
    for f in pkio.walk_tree(p, _CHECK_PRINTS_FILE_EXTS):
        f = p.bestrelpath(f)
        if re.search(_CHECK_PRINTS_EXCLUDE_FILES, f):
            continue
        n += 1
        for i, l in enumerate(pkio.read_text(f).split("\n"), start=1):
            if re.search(_PRINT, l) and not re.search(_PRINT_OK, l):
                res.append(f"{f}:{i} {l}")
    if n == 0:
        _error("no files found")
    if res:
        _error("\n".join(res))


def run():
    """Run the continuous integration checks and tests:

    #. Runs `check_prints`
    #. Checks formatting
    #. Runs `pykern.pkcli.test.default_command`
    """
    from pykern.pkcli import fmt, test
    from pykern import pkio

    check_eof_newline()
    check_prints()
    fmt.diff(pkio.py_path())
    test.default_command()
