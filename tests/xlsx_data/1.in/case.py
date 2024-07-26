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
    # test all the parseable types
    int=375,
    str="a fairly long string",
    float=7.77123,
    bool=True,
    none=None,
    decimal=decimal.Decimal(3.142),
)
t = s.table(title="t1", defaults=PKDict(round_digits=2))
t.header(
    ("Left", "Middle"),
    three="Right",
    four="Very End",
)
t.row(
    Left=t.cell(
        ["*", ["-", 100, ["-", ["n"]]], 1],
        fmt="bold",
    ),
    Middle=t.cell(
        35.337,
        fmt="percent",
        link="n",
    ),
    three=t.cell(
        ["%", ["n"], 1],
        fmt="decimal",
    ),
    four=t.cell(
        ("IF", ["<=", ["n"], 2], "red", "green"),
    ),
).pkupdate(defaults=PKDict(num_fmt="currency"))
t.row(
    Left=["MAX", 999],
    Middle=["MAX", 111, 222],
    three=["MIN", 333, 444],
    four=["IF", 0, ["/", 1, 0], 99],
).pkupdate(defaults=PKDict(num_fmt="currency"))
t.row(
    Left=["AND", True, ["<=", 1, 2]],
    Middle=["OR", False, [">", 3, 4]],
    three=["NOT", ["<=", 6, 7]],
    four="no op",
)
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
