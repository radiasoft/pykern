# -*- coding: utf-8 -*-
"""test ci

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import pytest

def test_run():
    from pykern.pkcli import ci
    from pykern import pkio
    from pykern import pkunit

    for d in pkunit.case_dirs():
        try:
            ci.run()
            res = "run ok\n"
        except Exception as e:
            res = f"run failed={e}\n"
        pkio.write_text('res', res)
