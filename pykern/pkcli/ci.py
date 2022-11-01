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
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
import re

_PRINT = re.compile(r"(?:\s|^)(?:pkdp|print)\(")
_PRINT_OK = re.compile(r"^\s*#\s*(?:pkdp|print)\(")


def check_eof_newline():
    """Recursively check repo for files missing newline at end of file.

    Files matching _CHECK_EOF_NEWLINE_FILE_EXTS and not matching
    _CHECK_EOF_NEWLINE_EXCLUDE_FILES will be checked.
    """
    _check_files("check_eof_newline")


def check_prints():
    """Recursively check repo for (naked) print and pkdp calls.

    Files matching _CHECK_PRINTS_FILE_EXTS and not matching
    _CHECK_PRINTS_EXCLUDE_FILES will be checked.

    See the
    `DesignHints <https://github.com/radiasoft/pykern/wiki/DesignHints#output-for-programmers-logging>_`
    wiki for an explanation of why this check is necessary.

    If you really need a print, use `pykern.pkconst.builtin_print`.
    """
    _check_files("check_prints")


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


def _check_files(case):
    def _check_eof_newline(file_path, res):
        if pkio.read_text(file_path).split("\n")[-1] != "":
            res.append(f"{file_path}")

    def _check_prints(file_path, res):
        for j, l in enumerate(pkio.read_text(file_path).split("\n"), start=1):
            if re.search(_PRINT, l) and not re.search(_PRINT_OK, l):
                res.append(f"{file_path}:{j} {l}")

    def _error(m):
        pkcli.command_error("{}: {}", case, m)

    d = PKDict(
        check_eof_newline=PKDict(
            check_func=_check_eof_newline,
            exclude_files=re.compile(
                r"/static/js/ext/|node_modules/|^run/|tests/|^venv/"
            ),
            include_files=re.compile(r"\.(html|jinja|js|json|md|py|tsx|yml)$"),
        ),
        check_prints=PKDict(
            check_func=_check_prints,
            exclude_files=re.compile(
                f".*(?:{pkunit.DATA_DIR_SUFFIX}|{pkunit.WORK_DIR_SUFFIX})/"
                + f"|^\\w+/{pksetup.PACKAGE_DATA}/"
                + r"|pkdebug[^/]*\.py$"
                + r"|(?:^|/)\."
                + r"|^run/"
                + r"|^venv/"
            ),
            include_files=re.compile(r".py$"),
        ),
    )[case]

    r = []
    p = pkio.py_path()
    n = 0
    for f in pkio.walk_tree(p, d.include_files):
        f = p.bestrelpath(f)
        if re.search(d.exclude_files, f):
            continue
        n += 1
        d.check_func(f, r)

    if n == 0:
        _error("no files found")
    if r:
        _error("\n".join(r))
