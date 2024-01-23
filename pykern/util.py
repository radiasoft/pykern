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


def is_pure_text(bytes_data, chunk_size):
    """Uses heuristics to guess whether file is pure text. If fails
    to utf-8 decode the bytes, checks if chunk was at the boundary of
    a valid truncated character

    Args:
        bytes_data (bytes): bytes data
        chunk_size (int): size of bytes data

    Returns:
        bool: True if bytes_data is likely pure text, false if likely binary
    """
    if len(bytes_data) < chunk_size:
        return _decode(bytes_data, lambda: False)
    b, e = bytes_data[:chunk_size], bytes_data[chunk_size:]
    return _decode(b, lambda: _check_if_boundary(b, e))


def _check_if_boundary(bytes_data, extra_chars):
    for i in range(len(extra_chars)):
        try:
            bytes_data += bytes([extra_chars[i]])
            bytes_data.decode("utf-8", "strict")
            return True
        except UnicodeDecodeError:
            continue
    return False


def _decode(data, decode_failure_callback):
    try:
        data.decode("utf-8", "strict")
        return True
    except UnicodeDecodeError:
        return decode_failure_callback()
