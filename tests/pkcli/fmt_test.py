# -*- coding: utf-8 -*-
u"""test fmt

:copyright: Copyright (c) 2019 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import pytest

def test_edit():
    from pykern import pkunit
    from pykern import pkio
    from pykern.pkcli import fmt
    pkunit.data_dir().join('file1.py').copy(pkunit.empty_work_dir().join('file1.py'))
    actual_path = pkunit.work_dir().join('file1.py')
    fmt.edit(actual_path)
    pkunit.file_eq(
        expect_path=pkunit.data_dir().join('file1_expect.py'),
        actual_path=actual_path
    )
    pkunit.data_dir().join('fmt_dir').copy(pkunit.work_dir().join('fmt_dir'))
    actual_path = pkunit.work_dir().join('fmt_dir')
    fmt.edit(actual_path)
    for f in pkio.walk_tree(actual_path):
        pkunit.file_eq(
            expect_path=pkunit.data_dir().join(f'fmt_dir_expect/{f.basename}'),
            actual_path=f
        )



def test_diff():
    from pykern import pkunit
    from pykern import pkio
    from pykern.pkcli import fmt

    pkunit.data_dir().join('file1.py').copy(pkunit.empty_work_dir().join('file1.py'))
    actual_path = pkunit.work_dir().join('file1.py')
    fmt.diff(actual_path, pkunit.data_dir().join('file1_expect.py'))


def test_diff2():
    from pykern import pkunit
    from pykern import pkio
    from pykern.pkcli import fmt

    pkunit.data_dir().join('file1.py').copy(pkunit.empty_work_dir().join('file1.py'))
    actual_path = pkunit.work_dir().join('file1.py')
    with pkunit.pkexcept(RuntimeError):
        fmt.diff(actual_path, pkunit.data_dir().join('fmt_dir_expect/y.py'))