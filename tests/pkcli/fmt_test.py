# -*- coding: utf-8 -*-
"""test fmt

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from multiprocessing.dummy import active_children
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import pytest


def test_run():
    from pykern import pkunit
    from pykern import pkio
    from pykern.pkcli import fmt

    pkunit.data_dir().join("file1.py").copy(pkunit.empty_work_dir().join("file1.py"))
    actual_path = pkunit.work_dir().join("file1.py")
    fmt.run(actual_path)
    pkunit.file_eq(
        expect_path=pkunit.data_dir().join("file1_expect.py"), actual_path=actual_path
    )

    for d in pkunit.case_dirs():
        fmt.run(d)


def test_diff():
    from pykern import pkunit
    from pykern import pkio
    from pykern.pksubprocess import check_call_with_signals

    actual_path = pkunit.work_dir().join('file1_diff_expect.py')
    check_call_with_signals([
            "pykern",
            "fmt",
            "diff",
            f"{pkunit.data_dir().join('file1.py')}"
        ],
        output=f"{actual_path}"
    )
    # compare all but first two lines of expect and actual diff
    expect = pkio.read_text(pkunit.data_dir().join('file1_diff_expect.txt')).split('\n')[2:]
    actual = pkio.read_text(actual_path).split('\n')[2:]
    pkunit.pkeq(expect, actual)


def test_check():
    from pykern import pkunit
    from pykern import pkio
    from pykern.pkcli import fmt

    pkunit.pkok(fmt.check(pkunit.data_dir().join('file1.py')), 'expect check to return True')
