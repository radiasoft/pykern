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
    dict1=({'d1': 'default1', 'd2': 'default2'}, dict, 'first param is dict'),
    list2=(['first1'], list, 'second param is list'),
    p3=(1313, int, 'third param is int'),
    p4=('!{{ list2[0] }}!', str, 'four param is string with jinja template'),
    p5=('{{ p3 }}', float, 'fifth param is same as p3, but a float')
    p6=(None, _custom_p6, 'sixth param is a custom parser')
    list7=(['default7'], list, 'seventh param is a list '),
)
