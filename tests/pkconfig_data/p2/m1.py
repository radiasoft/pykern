# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp

from pykern import pkconfig

cfg = pkconfig.init(
    anything=(13, int, 'an int param'),
)
