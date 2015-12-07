# -*- coding: utf-8 -*-
u"""Set some config

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkconfig

def alpha():
    return {}


def beta():
    return {}


def dev():
    return {
        'p1': {
            'm1': {
                'dict1': {
                    'd1': 'replace1',
                    'd3': 'new3',
                },
                'list2': ['first1'],
                'p3': '55',
                'req8': 99,
            },
        },
    }


def prod():
    return {}
