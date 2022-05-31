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

    for d in pykern.pkunit.case_dirs():
        p = 'workbook.xlsx'
        m = pykern.pkrunpy.run_path_as_module('case.py')
        with zipfile.ZipFile(m.PATH, 'r') as z:
            z.extractall()


'''
            for i in z.infolist():
                if i.filename == 'xl/workbook.xml' or 'sheets/sheet' in i.filename:
                    b = pkio.py_path(i.filename).basename
                    pkunit.file_eq(
                        expect_path=b,
                        actual=z.read(i),
                    )
'''
