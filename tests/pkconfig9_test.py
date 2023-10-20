# -*- coding: utf-8 -*-
"""Tests error message formatting for config value resolution

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_init(pkconfig_setup):
    pkconfig_setup()
    from pykern import pkunit

    with pkunit.pkexcept(r"Error prefix; key=x, value=\(False"):
        from p1.append_error import cfg
