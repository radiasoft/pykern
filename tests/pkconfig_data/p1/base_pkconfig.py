# -*- coding: utf-8 -*-
u"""Default config

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

def alpha():
    return {}


def beta():
    return {}


def dev():
    return {
        'p1': {
            'm1': {
                'p6': '2012-12-12T12:12:12Z',
            },
        },
    }


def prod():
    return {}
