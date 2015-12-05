# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp

import sys

from pykern import pkunit
from pykern import pkrunpy

def test_run_path_as_module():
    m = pkrunpy.run_path_as_module(pkunit.data_dir().join('f1.py'))
    assert m.func1() == sys.modules, \
        'When imported, should be able to call function within module'
