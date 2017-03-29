# -*- coding: utf-8 -*-
u"""test `pykern.pkconfig`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdp
import os

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
    p4=(None, int, 'fourth param is 10x p3'),
    p5=(os.environ['HOME'], str, 'value of $HOME'),
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
if cfg.p4 is None:
    cfg.p4 = str(cfg.p3) + '0'
