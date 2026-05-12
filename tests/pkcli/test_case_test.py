"""tests for file::case node ID syntax in pkcli.test

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_file_case(capsys):
    from pykern import pkunit, pkio
    from pykern.pkcli import test

    for d in pkunit.case_dirs():
        with pkunit.ExceptToFile():
            pkunit.pkre(
                pkio.read_text(d.join("pkre")).strip(),
                test.default_command(*pkio.read_text(d.join("args")).split()),
            )
