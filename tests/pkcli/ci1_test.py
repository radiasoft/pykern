# -*- coding: utf-8 -*-
"""test ci

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pkg_resources
from pykern.pkdebug import pkdp
import re
import pytest


def test_check_prints_dot_prefix():
    from pykern.pkcli import ci, test
    from pykern import pkunit
    from pykern import pksetup

    ci._EXCLUDE_FILES = re.compile(
        f"/{test.SUITE_D}/.*{pkunit.DATA_DIR_SUFFIX}/"
        + f"|/{pksetup.PACKAGE_DATA}/"
        + r"|pkdebug[^/]*\.py$"
        + r"|\.*/"
    )

    for d in pkunit.case_dirs("ignore_dot_prefix"):
        with pkunit.pkexcept_to_file():
            ci.check_prints()

    for d in pkunit.case_dirs("ignore_data"):
        with pkunit.pkexcept_to_file():
            ci.check_prints()
