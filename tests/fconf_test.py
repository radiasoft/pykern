# -*- coding: utf-8 -*-
u"""test fconf

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest

def test_parser():
    from pykern import pkunit, fconf, pkio, pkjson
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp

    for d in pkunit.case_dirs():
        p = fconf.Parser(pkio.sorted_glob('*.py') + pkio.sorted_glob('*.yml'))
        r = p.evaluate()
        r.macros = [f'{p.name}({",".join(p.params)})' for p in p.macros.values()]
        pkjson.dump_pretty(r, filename='res.json')