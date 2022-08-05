# -*- coding: utf-8 -*-
"""test ci

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import re
import pytest


def test_check_prints_dot_prefix():
    from pykern.pkcli import ci, test
    from pykern import pkunit

    for d in pkunit.case_dirs():
        with pkunit.ExceptToFile():
            ci.check_prints()
