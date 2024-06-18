"""test that links with the same name have to have same fmt

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import pykern.xlsx

PATH = "case3.xlsx"
w = pykern.xlsx.Workbook(path=PATH)
s = w.sheet(title="s1")
t = s.table(title="t1")
for i in range(3):
    t.row(
        count=t.cell(i, link="count"),
    )
i += 1
t.row(
    # different fmt than the above
    count=t.cell(i, link="count", fmt="text"),
)
w.save()
