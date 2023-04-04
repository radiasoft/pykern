# -*- coding: utf-8 -*-
"""restarts infinitely

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_always():
    from pykern import pkunit

    pkunit.restart_or_fail("restart infinitely")
