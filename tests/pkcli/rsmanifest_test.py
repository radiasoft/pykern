# -*- coding: utf-8 -*-
u"""test pykern.pkcli.rsmanifest

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_add_code():
    from pykern import pkio
    from pykern import pkjson
    from pykern import pkunit
    from pykern.pkunit import pkok, pkeq, pkre
    from pykern.pkdebug import pkdp
    from pykern.pkcli import rsmanifest
    import re

    with pkunit.save_chdir_work(is_pkunit_prefix=True) as d:
        rsmanifest.add_code('A', 'b', 'c', 'd', pyenv='v')
        j = pkjson.load_any(pkio.py_path(rsmanifest.USER_FILE).read())
        pkok(20170101.0  < float(j.version), 'version must be after 2017')
        pkeq('A', j.codes.v.a.name)
        pkeq('b', j.codes.v.a.version)
        rsmanifest.add_code('a', 'bb', 'cc', 'dd')
        j = pkjson.load_any(pkio.expand_user_path(rsmanifest.USER_FILE).read())
        pkeq('A', j.codes.v.a.name)
        pkeq('a', j.codes[''].a.name)
        pkeq('bb', j.codes[''].a.version)
        pkre('20.*T.*Z', j.codes[''].a.installed)


def test_read_all():
    from pykern import pkio
    from pykern import pkjson
    from pykern import pkunit
    from pykern.pkunit import pkok, pkeq, pkre
    from pykern.pkdebug import pkdp
    from pykern.pkcli import rsmanifest
    import re

    with pkunit.save_chdir_work(is_pkunit_prefix=True) as d:
        rsmanifest.add_code(
            'code1',
            version='1.1',
            uri='http://x.com',
            source_d='/tmp',
            pyenv='py2',
        )
        v = pkjson.load_any(pkio.py_path(rsmanifest.USER_FILE)).version
        pkjson.dump_pretty(
            {'version': v, 'image': {'type': 'docker'}},
            filename=rsmanifest.CONTAINER_FILE,
        )
        m = rsmanifest.read_all()
        pkeq(v, m.version)
        pkeq('docker', m.image.type)
        pkeq('1.1', m.codes.py2.code1.version)
