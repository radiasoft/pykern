# -*- coding: utf-8 -*-
u"""xlsx_test case

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
import pykern.xlsx

PATH = 'workbook.xlsx'
w = pykern.xlsx.Workbook(path=PATH)
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
        fmt='bold',
    ),
    two=t.cell(
        35.337,
        fmt='percent',
        link='n',
    ),
    three=t.cell(
        ('n',),
        fmt='decimal',
    ),
).pkupdate(defaults=PKDict(num_fmt='currency'))
t.footer(
    one='L',
    two=None,
    three=t.cell(
        'R',
        fmt='bold',
    )
)
w.save()
