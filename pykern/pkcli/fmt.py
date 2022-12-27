# -*- coding: utf-8 -*-
"""Wrapper for Python formatter (currently, ``black``) to update and to validate a repository.

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp, pkdlog
import py
import pykern.pksubprocess


def run(*paths):
    """Run black formatter on `path`

    Args:
        *paths (strs or py.paths): strings or py.paths to file or directory
    """
    _black(paths)


def diff(*paths):
    """Run diff on file comparing formatted vs. current file state

    Args:
        *paths (strs or py.paths): strings or py.paths to file or directory
    """
    _black(paths, "--diff", "--check", "--no-color")


def check(*paths):
    """Returns True if there would be diff else return False

    Args:
        *paths (strs or py.paths): strings or py.paths to file or directory
    """
    try:
        _black(paths, "--check")
    except RuntimeError as e:
        if str(e) == "error exit(1)":
            pykern.pkcli.command_error(
                "paths={} need to be formatted", tuple(str(p) for p in paths)
            )
        raise


def _black(paths, *args):
    """Helper function invokes black with options

    Args:
         *paths (strs or py.paths): strings or py.paths to file or directory
         *args (strs): options to be passed to black
    """
    from pykern import pkunit
    from pykern.pkcli import test
    from pykern import pksetup

    pykern.pksubprocess.check_call_with_signals(
        [
            "black",
            "--quiet",
            "--extend-exclude",
            f"/{test.SUITE_D}/.*{pkunit.DATA_DIR_SUFFIX}/|/{pksetup.PACKAGE_DATA}/",
            *args,
            *paths,
        ],
    )
