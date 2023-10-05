# -*- coding: utf-8 -*-
"""RuntimeWarning test

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_warning(capsys):
    from pykern import pkunit

    with pkunit.save_chdir_work() as d:
        t = d.join("tests")
        pkunit.data_dir().join("tests").copy(t)
        with pkunit.pkexcept("FAILED=1 passed=0"):
            test.default_command()
        o, e = capsys.readouterr()
        pkunit.pkre("1_test.py Invalid RuntimeWarning Fail", o)
