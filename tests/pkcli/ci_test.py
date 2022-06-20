# -*- coding: utf-8 -*-
"""test ci

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import re
import pytest


def test_run():
    from pykern.pkcli import ci
    from pykern import pkio
    from pykern import pkunit

    for d in pkunit.case_dirs("case"):
        try:
            ci.run()
            res = "run ok\n"
        except Exception as e:
            res = f"run failed={e}\n"
        pkio.write_text('res', res)


def test_check_prints():
    from pykern.pkcli import ci, test
    from pykern import pkio
    from pykern import pkunit
    from pykern import pksetup

    r = re.compile( f"/{test.SUITE_D}/.*{pkunit.DATA_DIR_SUFFIX}/|/{pksetup.PACKAGE_DATA}/|pkdebug")
    for d in pkunit.case_dirs("check_prints"):
        try:
            ci.check_prints(exclude=r)
            pkio.write_text('res', '')
        except Exception as e:
            pkio.write_text('res', str(e))
