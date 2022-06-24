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

    ci._EXCLUDE_FILES = re.compile(
        re.sub(
            f"/{test.SUITE_D}/.*(?:{pkunit.DATA_DIR_SUFFIX}|{pkunit.WORK_DIR_SUFFIX})/",
            f"/{test.SUITE_D}/.*{pkunit.DATA_DIR_SUFFIX}/",
            ci._EXCLUDE_FILES.pattern
        )
    )

    for d in pkunit.case_dirs():
        with pkunit.pkexcept_to_file():
            ci.check_prints()
