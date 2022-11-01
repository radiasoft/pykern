# -*- coding: utf-8 -*-
"""test ci

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkunit
from pykern.pkcli import ci
from pykern.pkdebug import pkdp


def test_check_eof_newline():
    for _ in pkunit.case_dirs("check_eof_newline"):
        with pkunit.ExceptToFile():
            ci.check_eof_newline()


def test_check_prints():
    for _ in pkunit.case_dirs("check_prints"):
        with pkunit.ExceptToFile():
            ci.check_prints()


def test_run():
    for _ in pkunit.case_dirs("run"):
        with pkunit.ExceptToFile():
            ci.run()
