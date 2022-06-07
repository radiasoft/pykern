# -*- coding: utf-8 -*-
u"""run black formatter on file/dir

:copyright: Copyright (c) 2013-2018 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import pykern.pksubprocess


def edit(path):
    cmd = ['black', f'{path}']
    pykern.pksubprocess.check_call_with_signals(cmd)


def diff(path, path_expect=None):
    cmd = ['git', 'diff', '--no-index', f'{path}']
    if path_expect:
        cmd.append(f'{path_expect}')
    edit(path)
    pykern.pksubprocess.check_call_with_signals(cmd)
