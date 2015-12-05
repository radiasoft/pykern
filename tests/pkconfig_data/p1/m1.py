# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp

from pykern import pkconfig

def _custom_p6(v):
    import dateutil.parser
    return dateutil.parser.parse(v)

cfg = pkconfig.init(
    dict1={
        'd1': ('default1', str, 'first param of dict1'),
        'd2': ('default2', str, 'second param of dict1'),
    },
    list2=(['first1'], list, 'second param is list'),
    p3=(1313, int, 'third param is int'),
    p6=(None, _custom_p6, 'sixth param is a custom parser'),
    list7=(['default7'], list, 'seventh param is a list '),
    req8=pkconfig.Required(int, 'an eighth required parameter'),
    sub_params9=dict(
        sub9_1=(None, int, 'sub param is first of ninth group'),
        sub9_2=dict(
            sub9_2_1=(44, int, 'sub 9.2.1')
        ),
    ),
)
