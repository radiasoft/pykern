"""test pkcli.xlsx

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_to_csv():
    from pykern import pkunit

    for d in pkunit.case_dirs():
        from pykern.pkcli import xlsx

        xlsx.to_csv("in.xlsx")
