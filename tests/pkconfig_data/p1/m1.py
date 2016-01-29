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

@pkconfig.parse_none
def _some_key(v):
    if v is None:
        return 999
    return int(v)

cfg = pkconfig.init(
    dict1=({
        'd1': 'default1',
        'd2': 'default2',
    }, dict, 'first param is dict'),
    list2=(['second1'], list, 'second param is list'),
    p3=(1313, int, 'third param is int'),
    p4=('{P1_M1_P3}0', int, 'fourth param is 10x p3'),
    p5=('{HOME}', str, 'value of $HOME'),
    p6=(None, _custom_p6, 'sixth param is a custom parser'),
    list7=(['default7'], list, 'seventh param is a list '),
    req8=pkconfig.Required(int, 'an eighth required parameter'),
    sub_params9=dict(
        sub9_1=(None, int, 'sub param is first of ninth group'),
        sub9_2=dict(
            sub9_2_1=(44, int, 'sub 9.2.1')
        ),
    ),
    dynamic_default10=(None, _some_key, 'sub dynamic default by parsing None'),
)
