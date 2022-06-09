# -*- coding: utf-8 -*-
"""Wrapper for Python formatter (currently, ``black``) to update and to validate a repository.

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp, pkdlog
import pykern.pksubprocess
import pykern.pkunit


def _black(path, *args, **kwargs):
    """Helper function invokes black with options

    Args:
         *args (strs): options to be passed to black
    """
    if kwargs:
        print('kwargs', kwargs)
    pykern.pksubprocess.check_call_with_signals(["black", "--quiet", *args, f"{path}"], **kwargs)


def run(path):
    """Run black formatter on `path`

    Args:
        path (object): string or py.path to file or directory
    """
    _black(path)


def diff(path):
    """Run diff on file comparing formated vs. current file state

    Args:
        path (object): string or py.path to file or directory
    """
    _black(path, "--diff", "--check","--no-color")


def check(path):
    """Returns True if there would be diff else return False

    Args:
        path (object): string or py.path to file or directory
    """
    try:
        _black(path, "--check")
    except RuntimeError as e:
        if str(e) == "error exit(1)":
            pykern.pkcli.command_error('path={} needs to be formatted', path)
        raise
