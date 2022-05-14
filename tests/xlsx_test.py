# -*- coding: utf-8 -*-
u"""test xlsx

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest

def test_1():
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    from pykern import xlsx
    from pykern.pkcollections import PKDict

    with pkunit.save_chdir_work():
        w = xlsx.Workbook(path='1.xlsx')
        s = w.sheet(title='one')
        t = s.table(title='t1', defaults=PKDict(round_digits=2))
        t.header(
            one='Left',
            two='Middle',
            three='Right',
        )
        t.row(
            one=t.cell(
                ['+', 'n', 100],
                fmt='currency',
            ),
            two=t.cell(
                35.337,
                fmt='currency',
                link='n',
            ),
            three=t.cell(
                ('n',),
                fmt='currency',
            ),
        )
        t.footer(
            one='L',
            two=None,
            three='R',
        )
        w.save()
        pkunit.file_eq(expect_path=pkunit.data_dir().join('1.csv'))
