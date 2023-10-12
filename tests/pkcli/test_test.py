# -*- coding: utf-8 -*-
"""pkcli.test test

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_simple(capsys):
    from pykern import pkunit
    from pykern.pkcli import test

    with pkunit.save_chdir_work() as d:
        t = d.join("tests")
        pkunit.data_dir().join("tests").copy(t)
        with pkunit.pkexcept("FAILED=1 passed=1"):
            test.default_command("skip_past=0_test")
        o, e = capsys.readouterr()
        pkunit.pkre("1_test.py pass", o)
        pkunit.pkre("2_test.py FAIL", o)
        t.join("2_test.py").rename(t.join("2_test.py-"))
        pkunit.pkre("passed=1", test.default_command("skip_past=0_test"))
        o, e = capsys.readouterr()
        pkunit.pkre("1_test.py pass", o)
        pkunit.pkre("passed=1", test.default_command("tests/1_test.py"))
        o, e = capsys.readouterr()
        pkunit.pkre("1_test.py pass", o)
        t.join("1_test.py").rename(t.join("1_test.py-"))
        with pkunit.pkexcept("FAILED=1 passed=0"):
            test.default_command()
        o, e = capsys.readouterr()
        pkunit.pkre(test.ASYNCIO_FAILURE_MESSAGE, o)


def test_tests_dir():
    from pykern import pkio, pkdebug
    from pykern import pkunit
    from pykern.pkcli import test

    with pkunit.save_chdir_work() as d:
        pkunit.data_dir().join("tests").copy(d.join("tests"))
        with pkunit.pkexcept("FAILED=1 passed=1"):
            test.default_command("skip_past=0_test")
        with pkunit.pkexcept("FAILED=1 passed=0"):
            test.default_command("skip_past=1_test")
