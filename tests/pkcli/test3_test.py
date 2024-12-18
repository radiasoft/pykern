"""test too many failures with max_procs

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_restarable():
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcli import test

    # force stop on first failure
    test._cfg.max_failures = 1
    for p in (1, 2, 3):
        with pkunit.save_chdir_work() as d:
            pkunit.data_dir().join("tests").copy(d.join("tests"))
            with pkunit.pkexcept(
                f"FAILED=1 passed={2 if p > 2 else 1}",
            ):
                test.default_command(f"max_procs={p}")
