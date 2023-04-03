# -*- coding: utf-8 -*-
"""test restartable

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_restarable():
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcli import test

    test._cfg.max_failures = 3
    for test._cfg.restartable in (False, True):
        with pkunit.save_chdir_work() as d:
            pkunit.data_dir().join("tests").copy(d.join("tests"))
            with pkunit.pkexcept(
                "FAILED=1" if test._cfg.restartable else "FAILED=2",
            ):
                test.default_command()
