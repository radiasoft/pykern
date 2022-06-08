# -*- coding: utf-8 -*-
"""test fmt

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
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
    from pykern.pkcli import fmt

    fmt.diff(pkunit.data_dir().join('file1.py'))


def test_check():
    from pykern import pkunit
    from pykern import pkio
    from pykern.pkcli import fmt

    pkunit.pkok(fmt.check(pkunit.data_dir().join('file1.py')), 'expect check to return True')
