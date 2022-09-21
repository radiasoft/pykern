# -*- coding: utf-8 -*-
"""test removal of script dir from sys.path

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_sys_path():
    from pykern import pkcli, pkunit, pkdebug
    import sys, os.path

    # py.test adds pwd to sys.path so we have to remove for this test to work
    sys.path.pop(0)
    d = os.path.dirname(os.path.realpath(sys.argv[0]))
    pkunit.pkeq(d, sys.path[0])
    try:
        pkcli.main("pykern")
    except Exception:
        pass
    pkunit.pkne(d, sys.path[0])
