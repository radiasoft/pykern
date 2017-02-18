# -*- coding: utf-8 -*-
u"""test pykern.pkcli.rsmanifest

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_add_code():
    from pykern import pkcollections
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkunit import pkok, pkeq, pkre
    from pykern.pkdebug import pkdp
    from pykern.pkcli import rsmanifest
    import re

    with pkunit.save_chdir_work() as d:
        rsmanifest.add_code('A', 'b', 'c', 'd', virtual_env='v')
        pkdp(pkio.expand_user_path(rsmanifest.USER_FILE))
        j = pkcollections.json_load_any(pkio.expand_user_path(rsmanifest.USER_FILE).read())
        pkok(20170101.0  < float(j.version), 'version must be after 2017')
        pkeq('A', j.codes.v.a.name)
        pkeq('b', j.codes.v.a.version)
        rsmanifest.add_code('a', 'bb', 'cc', 'dd')
        j = pkcollections.json_load_any(pkio.expand_user_path(rsmanifest.USER_FILE).read())
        pkeq('A', j.codes.v.a.name)
        pkeq('a', j.codes[''].a.name)
        pkeq('bb', j.codes[''].a.version)
        pkre('20.*T.*Z', j.codes[''].a.installed)
