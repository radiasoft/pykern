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
    pass
    # from pykern import pkunit
    # from pykern import pkio
    # from pykern.pkcli import fmt

    # pkunit.data_dir().join('file1.py').copy(pkunit.empty_work_dir().join('file1.py'))
    # actual_path = pkunit.work_dir().join('file1.py')
    # fmt.diff(actual_path, pkunit.data_dir().join('file1_expect.py'))


def test_diff2():
    pass
    # from pykern import pkunit
    # from pykern import pkio
    # from pykern.pkcli import fmt

    # pkunit.data_dir().join('file1.py').copy(pkunit.empty_work_dir().join('file1.py'))
    # actual_path = pkunit.work_dir().join('file1.py')
    # with pkunit.pkexcept(RuntimeError):
    #     fmt.diff(actual_path, pkunit.data_dir().join('fmt_dir_expect/y.py'))
