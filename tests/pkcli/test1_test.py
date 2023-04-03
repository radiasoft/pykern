# -*- coding: utf-8 -*-
"""test restartable

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_restarable():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing({"PYKERN_PKCLI_TEST_RESTARTABLE": "1"})

    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcli import test

    with pkunit.save_chdir_work() as d:
        pkunit.data_dir().join("tests").copy(d.join("tests"))
        with pkunit.pkexcept("FAILED=1 passed=1"):
            test.default_command()
