# -*- coding: utf-8 -*-
"""test ci

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import re
import pytest


def test_run():
    from pykern.pkcli import ci
    from pykern import pkio
    from pykern import pkunit

    for d in pkunit.case_dirs("run"):
        with pkunit.ExceptToFile():
            ci.run()


def test_check_prints():
    from pykern.pkcli import ci
    from pykern import pkunit

    for d in pkunit.case_dirs("check_prints"):
        with pkunit.ExceptToFile():
            ci.check_prints()
