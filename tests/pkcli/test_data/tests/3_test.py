# -*- coding: utf-8 -*-
"""Skips first case

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import time

_NOT_SKIPPED = "test_skip not skipped"


@pytest.mark.skip(reason="always skips")
def test_skip():
    from pykern import pkunit
    from pykern.pkdebug import pkdlog, pkdp

    pkunit.pkfail(_NOT_SKIPPED)


def test_skip_output():
    import py.path
    from pykern import pkunit
    
    p = py.path.local(__file__).dirpath("3_test.log")
    with open(p, 'r') as file:
        c = file.read()
        if "FAILED" in c: pkunit.pkfail("test_skip failed")