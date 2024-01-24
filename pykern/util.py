# -*- coding: utf-8 -*-
"""Support routines, including run dir resolution.

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
    """Parser function for absolute dir config value

    Args:
        value (str): string absolute path to dir

    Returns:
        py.path.Local absolute path to dir
    """
    if not os.path.isabs(value):
        pkconfig.raise_error("must be absolute")
    if not os.path.isdir(value):
        pkconfig.raise_error("must be a directory and exist")
    return pkio.py_path(value)


def dev_run_dir(package_object):
    """Resolves run directory if in development mode and creates it if it doesn't exist.

    Note that this assumes a file structure like pykern's where <project_name>'s __init__.py
    lives in <project_name>/<project_name>/

    Args:
        package_object (object): A python object whose root package we are resolving the run directory for

    Returns:
        py.path.local: The absolute path to the run directory.

    Raises:
        AssertionError: Raised when not in development mode
    """

    def _check_dev_files(root):
        """Check for files that only exist in development"""
        return any([root.join(f).check() for f in _DEV_ONLY_FILES])

    if not pkconfig.in_dev_mode():
        raise AssertionError("run dir root must be configured except in dev")
    r = (
        pkio.py_path(
            sys.modules[pkinspect.root_package(package_object)].__file__,
        )
        .dirpath()
        .dirpath()
    )
    if not _check_dev_files(r):
        # Don't run from an install directory
        r = pkio.py_path()
    return pkio.mkdir_parent(r.join(_DEFAULT_ROOT))


def is_pure_text(value, test_size=512):
    """Guesses if value is pure text by attempting to
    utf-8 decode it. If decode fails, checks if test_size was
    at the boundary of a valid truncated character

    Args:
        value (bytes): bytes data
        test_size (int): size of bytes chunk being tested

    Returns:
        bool: True if bytes_data is likely pure text, false if likely binary
    """

    def _try(chunk):
        try:
            chunk.decode("utf-8", "strict")
            return True
        except UnicodeDecodeError:
            return False

    if b"\x00" in value:
        return False
    if len(value) <= test_size:
        return _try(value)
    b = value[:test_size]
    # 4 is maximum length of a utf8 char so if a char
    # is truncated by test_size, we need to probe back
    # a bit to find the end of the char.
    for _ in range(4):
        if _try(b):
            return True
        if len(b) <= 1:
            return False
        b = b[:-1]
    return False
