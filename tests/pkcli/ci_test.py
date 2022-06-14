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

    # print(pkunit.data_dir())
    for d in pkunit.case_dirs():
        print('d', d)
        ci.run(d)
    # assert 0, "should fail for now"
