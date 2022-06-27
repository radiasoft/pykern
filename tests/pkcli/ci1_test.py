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

    _unexclude_work_dir()
    for d in pkunit.case_dirs():
        with pkunit.pkexcept_to_file():
            ci.check_prints()


def _unexclude_work_dir():
    from pykern.pkcli import ci
    from pykern import pkunit

    p = ci._EXCLUDE_FILES.pattern.replace(f"|{pkunit.WORK_DIR_SUFFIX}", "")
    assert p != ci._EXCLUDE_FILES.pattern
    ci._EXCLUDE_FILES = re.compile(p, flags=ci._EXCLUDE_FILES.flags)
