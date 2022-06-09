# -*- coding: utf-8 -*-
"""test fmt

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from multiprocessing.dummy import active_children
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import pytest



def test_check():
    from pykern import pkunit
    from pykern import pkio
    from pykern.pkcli import fmt

    for d in pkunit.case_dirs("check"): #TODO (gurhar1133) need more checks (both diff and no diff)
        try:
            fmt.check(d)
            pkio.write_text('res', 'check ok\n')
        except Exception as e:
            pkio.write_text('res', f'check exception=failed\n')


def test_diff():
    from pykern import pkunit
    from pykern import pkio
    from pykern.pksubprocess import check_call_with_signals

    #TODO (gurhar1133) need to use case_dirs("diff") with diff and no diff cases
    #TODO (gurhar1133) also need diff.in and diff.out instead of file1_diff_expect.py/txt
    return

    actual_path = pkunit.work_dir().join('file1_diff_expect.py')
    check_call_with_signals([
            "pykern",
            "fmt",
            "diff",
            f"{pkunit.data_dir().join('single_file.in/file1.py')}"
        ],
        output=f"{actual_path}"
    )
    # compare all but first two lines of expect and actual diff
    expect = pkio.read_text(pkunit.data_dir().join('file1_diff_expect.txt')).split('\n')[2:]
    actual = pkio.read_text(actual_path).split('\n')[2:]
    pkunit.pkeq(expect, actual)


def test_run():
    from pykern import pkunit
    from pykern import pkio
    from pykern.pkcli import fmt

    for d in pkunit.case_dirs('fmt_dir'):
        fmt.run(d)
