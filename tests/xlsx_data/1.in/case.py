"""xlsx_test case

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import pykern.xlsx
import decimal

PATH = "case1.xlsx"
w = pykern.xlsx.Workbook(path=PATH)
s = w.sheet(title="one")
s.table(title="types").row(
    int=1, str="a", float=1.2, bool=True, decimal=decimal.Decimal(0.1)
)
t = s.table(title="t1", defaults=PKDict(round_digits=2))
t.header(
    ("Left", "Middle"),
    three="Right",
    four="Very End",
)
t.row(
    Left=t.cell(
        ["+", ["n"], 100],
        fmt="bold",
    ),
    Middle=t.cell(
        35.337,
        fmt="percent",
        link="n",
    ),
    three=t.cell(
        ("%", ["n"], 1),
        fmt="decimal",
    ),
    four=t.cell(
        ("IF", ["<=", ["n"], 2], "green", "red"),
    ),
).pkupdate(defaults=PKDict(num_fmt="currency"))
t.footer(
    Left="L",
    Middle=None,
    three=t.cell(
        "R",
        fmt="bold",
    ),
    four=None,
)
t.footer(Left="No Totals", Middle="", three=None, four=None).pkupdate(
    defaults=PKDict(border=None),
)
w.save()
