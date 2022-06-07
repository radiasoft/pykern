# -*- coding: utf-8 -*-
u"""Wrapper for Python formatter (currently, ``black``) to update and to validate a repository.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import pykern.pksubprocess
import pykern.pkunit

def run(path):
    """
        Run black formatter on path

        Args:
            path - string path to file or dir
    """
    pykern.pksubprocess.check_call_with_signals(['black', f'{path}'])


def _diff(path):
    pykern.pksubprocess.check_call_with_signals([
        'black',
        '--diff',
        '--no-color',
        f'{path}'
    ])



def check_diff(path):
    try:
        pykern.pksubprocess.check_call_with_signals([
            'black',
            '--check',
            f'{path}'
        ])
    except RuntimeError as e:
        if str(e) == 'error exit(1)':
            _diff(path)
