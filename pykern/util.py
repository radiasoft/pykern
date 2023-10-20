# -*- coding: utf-8 -*-
"""utils for pykern

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import os.path
import sys


_DEFAULT_ROOT = "run"
_DEV_DIR_FILES = ("setup.py", "pyproject.toml")


def cfg_absolute_dir(value):
    """Parser function for run dir config value

    Args:
        value (str): string absolute path to run dir

    Returns:
        py.path.Local absolute path to run dir
    """
    if not os.path.isabs(value):
        pkconfig.raise_error("must be absolute")
    if not os.path.isdir(value):
        pkconfig.raise_error("must be a directory and exist")
    return pkio.py_path(value)


def dev_run_dir(package_object):
    """Initialize run dir

    Args:
        package_object (object): python object whose root_package will hold the run dir

    Returns:
        py.path.local: absolute path to run dir
    """

    assert pkconfig.in_dev_mode(), "run dir root must be configured except in dev"
    r = (
        pkio.py_path(
            sys.modules[pkinspect.root_package(package_object)].__file__,
        )
        .dirpath()
        .dirpath()
    )
    a = pkio.py_path(sys.modules[pkinspect.root_package(package_object)].__file__,)
    b = a.dirpath()
    c = b.dirpath()
    assert 0, f"a={a} b={b} c={c}"
    # Check to see if we are in our dev directory. This is a hack,
    # but should be reliable.
    if not any([r.join(f).check() for f in _DEV_DIR_FILES]):
        # Don't run from an install directory
        r = pkio.py_path()
    return pkio.mkdir_parent(r.join(_DEFAULT_ROOT))
