# -*- coding: utf-8 -*-
u"""test xlsx

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest

def test_1():
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    import pykern.pkrunpy
    import pykern.pkunit
    import zipfile

    # If you see a failure, xmllint is helpful:
    #   xmllint --format worksheets/sheet1.xml
    for d in pykern.pkunit.case_dirs():
        p = 'workbook.xlsx'
        m = pykern.pkrunpy.run_path_as_module('case.py')
        with zipfile.ZipFile(m.PATH, 'r') as z:
            z.extractall()
