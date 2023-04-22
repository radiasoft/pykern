# -*- coding: utf-8 -*-
"""test pkconfig.in_dev_mode()

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_in_dev_mode():
    """Validate channel_in()"""
    from pykern import pkconfig

    assert pkconfig.in_dev_mode(), "should be in dev mode"
