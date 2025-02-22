"""test ci

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_all():
    from pykern import pkunit
    from pykern.pkcli import ci

    for d in pkunit.case_dirs():
        with pkunit.ExceptToFile():
            getattr(ci, d.basename.split("-")[0])()
