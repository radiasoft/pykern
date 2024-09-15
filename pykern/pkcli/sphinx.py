"""Generate documentation with Sphinx

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import email.utils
import importlib.metadata
import pykern.pkcli
import pykern.pkcollections
import pykern.pkio
import pykern.pkresource
import pykern.pksubprocess
import re
import toml

_DOCS_SUBDIR = "docs"


def prepare(package):
    """Create conf.py and run ``sphinx-apidoc``

    conf.py is generated from `package` metadata so `package` must be
    installed.

    Args:
        package (str): package to build

    """

    def _conf(substitutions):
        rv = pykern.pkio.read_text(pykern.pkresource.file_path("sphinx-conf.py"))
        for k, v in substitutions.items():
            rv = rv.replace("$" + k, v)
        return rv

    def _parse_metadata():
        try:
            return _vars(importlib.metadata.metadata(package))
        except importlib.metadata.PackageNotFoundError as e:
            pykern.pkcli.command_error(
                f"unable to import package={package}; run pip install ."
            )

    def _vars(metadata):
        return _year(
            PKDict(
                author=email.utils.parseaddr(metadata["Author-email"])[0],
                name=metadata["Name"],
                version=metadata["Version"],
            ),
        )

    def _year(rv):
        m = re.search(r"^(\d{4})\d{4}\.\d+$", rv.version)
        if m:
            return rv.pkupdate(year=m.group(1))
        pykern.pkcli.command_error(
            f"unable to parse version={rv.version} package={rv.name}"
        )

    d = pykern.pkio.py_path(_DOCS_SUBDIR)
    if not d.check(dir=True):
        pykern.pkcli.command_error(
            f"missing directory={d.basename}; run from Python root directory"
        )
    v = _parse_metadata()
    pykern.pkio.write_text(d.join("conf.py"), _conf(v))
    pykern.pksubprocess.check_call_with_signals(
        ("sphinx-apidoc", "--force", "--module-first", "-o", d.basename, v.name),
    )


def build(builder="html"):
    """`prepare` and run ``sphinx-build`` for html

    Reads ``pyproject.toml`` to get project name. Creates ``_build_<builder>`` subdirectory
    with the output.

    Args:
        builder (str): types of builders. See `Sphinx builder list <https://www.sphinx-doc.org/en/master/usage/builders/index.html>`_ [html]

    """

    try:
        t = toml.load("pyproject.toml")
    except Exception as e:
        if pykern.pkio.exception_is_not_found(e):
            pykern.pkcli.command_error(
                "pyproject.toml not found; convert setup.py (if exists) or run from Python root directory"
            )
        raise
    prepare(t["project"]["name"])
    pykern.pksubprocess.check_call_with_signals(
        (
            "sphinx-build",
            "-M",
            builder,
            _DOCS_SUBDIR,
            f"_build_{builder}",
            # --fail-on-warning not yet in this version
            "-W",
        ),
    )
