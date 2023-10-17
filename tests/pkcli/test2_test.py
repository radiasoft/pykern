# -*- coding: utf-8 -*-
"""pkcli.test test

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_cases(capsys):
    from pykern import pkunit, pkio
    from pykern.pkcli import test
    from pykern.pkcollections import PKDict
    import re

    # Wait for #410 which would support this
    expect = PKDict({"1": "coroutine_test.py FAIL .*FAILED due to warnings"})
    for d in pkunit.case_dirs():
        try:
            test.default_command(".")
        except Exception:
            pass
        o, e = capsys.readouterr()
        pkio.write_text("stdout.txt", o)
        pkio.write_text("stderr.txt", e)
        pkunit.pkre(expect[d.basename], o)
