# -*- coding: utf-8 -*-
u"""conforming case_dirs

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest

def test_case_dirs():
    from pykern import pkunit
    from pykern.pkdebug import pkdp

    pkdp('case_dirs: {}', pkunit.case_dirs())
    for d in pkunit.case_dirs():

        pkdp('D: {}', d)
        pkdp('D base: {}', d.basename)
        if d.basename != 'xlsx':
            i = d.join('in.txt').read()
            pkdp('I: {}', i)
            pkdp('d.basename: {}', d.basename)
            pkunit.pkeq(d.basename + '\n', i)
            d.join('out.txt').write(i)

def test_xlsx_to_csv_conversion():
    from pykern import pkunit
    from pykern.pkdebug import pkdp

    for d in pkunit.case_dirs():
        pkdp('xlsx ? D: {}', d)
