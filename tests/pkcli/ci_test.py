# -*- coding: utf-8 -*-
"""test ci

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp


def test_check_eof_newline():
    _test("check_eof_newline")


def test_check_prints():
    _test("check_prints")


def test_run():
    _test("run")


def _test(case_dir):
    from pykern import pkunit
    from pykern.pkcli import ci

    for _ in pkunit.case_dirs(case_dir):
        with pkunit.ExceptToFile():
            getattr(ci, case_dir)()
