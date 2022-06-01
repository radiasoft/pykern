# -*- coding: utf-8 -*-
u"""xlsx_test case

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
import pykern.xlsx

PATH = 'case2.xlsx'
w = pykern.xlsx.Workbook(path=PATH)
s = w.sheet(title='s1')
t = s.table(title='t1', defaults=PKDict(round_digits=0, num_fmt='currency'))
t.header(
    name='Name',
    count='Count',
)
x = list()
for i in range(1, 5):
    t.row(
        name=f'c{i}',
        count=t.cell(i, link='count'),
    )
t.footer(
    name='Total',
    count=t.cell(['*', 'count'], link='prod')
)
s = w.sheet(title='s2')
t = s.table(title='t2', defaults=PKDict(round_digits=0, num_fmt='currency'))
t.row(
    prod=['prod'],
    prod_number=t.cell(['prod'], fmt='text'),
)
w.save()
