"""pkcli.test test

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def setup_module(module):
    import os

    # Our CI (radiasoft/download/installers/python-ci sets these to 1,
    # but we do not want restarts or to stop out due to max failures
    os.environ.update(
        PYKERN_PKCLI_TEST_MAX_FAILURES="5",
        PYKERN_PKCLI_TEST_RESTARTABLE="0",
    )


def test_simple(capsys):
    from pykern import pkunit
    from pykern.pkcli import test

    with pkunit.save_chdir_work() as d:
        t = d.join("tests")
        pkunit.data_dir().join("tests").copy(t)
        with pkunit.pkexcept("FAILED=1 passed=2", "all tests"):
            test.default_command()
        o, e = capsys.readouterr()
        pkunit.pkre("1_test.py pass", o)
        pkunit.pkre("2_test.py FAIL", o)
        t.join("2_test.py").rename(t.join("2_test.py-"))
        # tests 1 & 3 together
        pkunit.pkre("passed=2", test.default_command())
        o, e = capsys.readouterr()
        pkunit.pkre("1_test.py pass", o)
        pkunit.pkre(
            "3_test.py pass\ntests/3_test.py::test_skip SKIPPED .always skips.",
            o,
        )
        # tests 1 and 3 individually
        pkunit.pkre("passed=1", test.default_command("tests/1_test.py"))
        o, e = capsys.readouterr()
        pkunit.pkre("1_test.py pass", o)
        pkunit.pkre("passed=1", test.default_command("tests/3_test.py"))
        o, e = capsys.readouterr()
        pkunit.pkre("3_test.py pass.*test_skip SKIPPED", o)
        # test 2 and 3 together
        t.join("2_test.py-").rename(t.join("2_test.py"))
        t.join("1_test.py").rename(t.join("1_test.py-"))
        with pkunit.pkexcept("FAILED=1 passed=1"):
            test.default_command()
        o, e = capsys.readouterr()
        pkunit.pkre("2_test.py FAIL", o)
        pkunit.pkre("x = 1 / 0", o)
        pkunit.pkre("test_skip SKIPPED", o)


def test_tests_dir(capsys):
    from pykern import pkio, pkdebug
    from pykern import pkunit
    from pykern.pkcli import test

    with pkunit.save_chdir_work() as d:
        pkunit.data_dir().join("tests").copy(d.join("tests"))
        with pkunit.pkexcept("FAILED=1 passed=2"):
            test.default_command()
        with pkunit.pkexcept("FAILED=1 passed=1"):
            test.default_command("skip_past=1_test")
        # to avoid confusing output with SKIPPED
        capsys.readouterr()
