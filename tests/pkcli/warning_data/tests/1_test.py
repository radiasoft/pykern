# -*- coding: utf-8 -*-
u"""fails due to RuntimeWarning

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from pykern.pkdebug import pkdp

def test_1():
    import warnings

    warnings.warn("coroutine foo was never awaited", RuntimeWarning)
