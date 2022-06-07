# -*- coding: utf-8 -*-
u"""Wrapper for Python formatter (currently, ``black``) to update and to validate a repository.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import pykern.pksubprocess


def run(path):
    """
        Run black formatter on path

        Args:
            path - string path to test file or file containing multiple tests
    """
    pykern.pksubprocess.check_call_with_signals(['black', f'{path}'])


def diff(path, path_expect=None):
    cmd = ['git', 'diff', '--no-index', f'{path}']
    if path_expect:
        cmd.append(f'{path_expect}')
    run(path)
    pykern.pksubprocess.check_call_with_signals(cmd)
