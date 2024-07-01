"""test projex upgrade

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_upgrade():
    import subprocess
    from pykern import pkunit, pkio
    from pykern.pkcli import projex

    for d in pkunit.case_dirs():
        subprocess.check_call(["git", "init", "."])
        pkio.write_text("projex.out", projex.upgrade_tree())
        # base_pkconfig setup.py
