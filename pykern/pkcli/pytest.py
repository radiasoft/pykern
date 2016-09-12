# -*- coding: utf-8 -*-
u"""DEPRECATED

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import os


def default_command(*args, **kwargs):
    """DEPRECATED: just run py.test"""
    os.execvp('py.test', ('py.test',) + args)
