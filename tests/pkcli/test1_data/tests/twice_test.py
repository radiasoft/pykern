# -*- coding: utf-8 -*-
"""restarts twice

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_twice():
    from pykern import pkunit
    from pykern import pkio
    from pykern import pkdebug

    p = pkio.py_path().join("twice")
    if p.exists():
        # success
        return
    p.write("test_twice")
    pkunit.restart_or_fail("restart infinitely")
