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

#: static/js/ext is where Sirepo stores 3rd party library files
_CHECK_FILES = PKDict(
    check_eof_newline=PKDict(
        exclude_files=re.compile(r"/static/js/ext/|node_modules/|^run/|^tests/|^venv/"),
        include_files=re.compile(r"\.(html|jinja|js|json|md|py|tsx|yml)$"),
    ),
    check_main=PKDict(
        exclude_files=re.compile(r".*(_console\.py)|^tests/|^venv/|^pyproject.toml$"),
        include_files=re.compile(r".*(\.py)$"),
    ),
    check_prints=PKDict(
        exclude_files=re.compile(
            rf".*(?:{pkunit.DATA_DIR_SUFFIX}|{pkunit.WORK_DIR_SUFFIX})/"
            + rf"|^\w+/{pksetup.PACKAGE_DATA}/"
            + r"|pkdebug[^/]*\.py$"
            + r"|(?:^|/)\."
            + r"|^run/"
            + r"|^venv/"
            + r"|^pyproject.toml$"
        ),
        include_files=re.compile(r".py$"),
    ),
)

_MAIN = re.compile(r"^if.*__name__")
_PRINT = re.compile(r"(?:[\s\(,]|^)(?:pkdp|print)\(")
_PRINT_OK = re.compile(r"^\s*#\s*(?:pkdp|print)\(")


def check_eof_newline():
    """Recursively check repo for files missing newline at end of file.

    Checks html, jinja, js, json, md, py, tsx, and yml files.
    Excludes external files, tests, and run directory.
    """

    def _c(lines):
        return [] if lines[-1] == "" else [""]

    _check_files("check_eof_newline", _c)


def check_main():
    """Recursively check repo for modules with main programs.

    Checks .py files.
    Excludes ``<project>_console.py``, tests, and venv.
    """

    def _c(lines):
        r = []
        for j, l in enumerate(lines, start=1):
            if re.search(_MAIN, l):
                r.append(f":{j} {l}")
        return r

    _check_files("check_main", _c)


def check_prints():
    """Recursively check repo for (naked) print and pkdp calls.

    Checks .py files, excluding hidden files, pkdebug module, test data/work, run directory,
    package_data and venv.

    See the
    `DesignHints <https://github.com/radiasoft/pykern/wiki/DesignHints#output-for-programmers-logging>_`
    wiki for an explanation of why this check is necessary.

    If you really need a print, use `pykern.pkconst.builtin_print`.
    """

    def _c(lines):
        r = []
        for j, l in enumerate(lines, start=1):
            if re.search(_PRINT, l) and not re.search(_PRINT_OK, l):
                r.append(f":{j} {l}")
        return r

    _check_files("check_prints", _c)


def run():
    """Run the continuous integration checks and tests:

    #. Runs `check_prints`
    #. Checks formatting
    #. Runs `pykern.pkcli.test.default_command`
    """
    from pykern.pkcli import fmt, test
    from pykern import pkio

    check_eof_newline()
    check_main()
    check_prints()
    pkdlog(
        "Checking fmt diff. If a diff is printed below, you can fix this failure by running `pykern fmt run .` from the repo root."
    )
    fmt.diff(*_paths(pkio.py_path()))
    return test.default_command()


def _check_files(case, check_file):
    def _error(m):
        pkcli.command_error("{}: {}", case, m)

    d = _CHECK_FILES[case]
    r = []
    n = 0

    c = pkio.py_path()
    for p in _paths(c):
        for f in pkio.walk_tree(p, d.include_files):
            f = c.bestrelpath(f)
            if re.search(d.exclude_files, f):
                continue
            n += 1
            for l in check_file(pkio.read_text(f).split("\n")):
                r.append(f"{f}{l}")

    if n == 0:
        _error("no files found")
    if r:
        _error("\n".join(r))


def _paths(cwd):
    def _exists(*names):
        return list(filter(lambda n: cwd.join(n).isfile(), names))

    if _exists("README.rst", "README.md") and (
        (x := _exists("setup.py")) or _exists("pyproject.toml")
    ):
        return (
            # POSIT: repo name
            cwd.basename,
            "tests",
            *x,
        )
    return (cwd,)
