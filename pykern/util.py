# -*- coding: utf-8 -*-
"""db configuration

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import os.path
import sys

#: Relative to current directory only in dev mode
_DEFAULT_ROOT = "run"


def cfg_db_dir(db_root_env_name):
    """Generate pkconfig parser function with errors for db's env var name

    Args:
        db_root_env_name (str): env var name for run dir root

    Returns:
        function: parser function for pkconfig.init
    """
    _NOT_ABS_ERROR = "{}: " + f"{db_root_env_name} must be absolute"
    _NO_DIR_ERROR = "{}: " + f"{db_root_env_name} must be a directory and exist"

    def cfg_db_dir_parser(v):
        """Config value or root package's parent or cwd with `_DEFAULT_ROOT`"""
        if not os.path.isabs(v):
            pkconfig.raise_error(_NOT_ABS_ERROR.format(v))
        if not os.path.isdir(v):
            pkconfig.raise_error(_NO_DIR_ERROR.format(v))
        return pkio.py_path(v)

    return cfg_db_dir_parser


def init_db_dir(package_object):
    """Initialize run dir

    Args:
        package_object (object): python object who's root will hold the run dir

    Returns:
        py.path.local: absolute path to run dir
    """
    r = (
        pkio.py_path(
            sys.modules[pkinspect.root_package(package_object)].__file__,
        )
        .dirpath()
        .dirpath()
    )
    # Check to see if we are in our dev directory. This is a hack,
    # but should be reliable.
    if not r.join("setup.py").check():
        # Don't run from an install directory
        r = pkio.py_path(".")
    return pkio.mkdir_parent(r.join(_DEFAULT_ROOT))
