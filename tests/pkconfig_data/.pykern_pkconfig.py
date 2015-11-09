# -*- coding: utf-8 -*-
u"""Set some config

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


def alpha():
    return {}


def beta():
    return {}


def dev():
    return {
        'pykern': {
            'pkdebug': {
                'control': 'this will not match anything',
            },
        },
    }


def prod():
    return {}
