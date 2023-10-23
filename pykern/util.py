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
_DEV_ONLY_FILES = ("setup.py", "pyproject.toml")


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
    """Returns run dir root for dev mode. Creates if doesn't exist. Assumes file
    structure where project's __init__.py lives in <project_name>/<project_name>/

    Args:
        package_object (object): python object whose root_package will hold the run dir

    Returns:
        py.path.local: absolute path to run dir
    """

    def _check_dev_files(root):
        """Looks for files at the root of a python project that are not installed when the package is installed"""
        return any([root.join(f).check() for f in _DEV_ONLY_FILES])

    assert pkconfig.in_dev_mode(), "run dir root must be configured except in dev"
    r = (
        pkio.py_path(
            sys.modules[pkinspect.root_package(package_object)].__file__,
        )
        .dirpath()
        .dirpath()
    )
    a = pkio.py_path(
        sys.modules[pkinspect.root_package(package_object)].__file__,
    )
    b = a.dirpath()
    c = b.dirpath()
    if not _check_dev_files(r):
        # Don't run from an install directory
        r = pkio.py_path()
    return pkio.mkdir_parent(r.join(_DEFAULT_ROOT))
