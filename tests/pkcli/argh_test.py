"""Test for pkcli argh argument parsing.

:copyright: Copyright (c) 2023 RadiaSoft, LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_kwarg_to_positional(capsys):
    from pykern import pkcli
    from pykern.pkunit import pkre, pkeq
    import sys

    p = "p"
    k = "k"
    sys.argv = [
        "argh_test",
        "argh_test",
        "kwarg-to-positional",
        p,
        "--keyword-arg",
        k,
    ]
    r = pkcli.main("pykern")
    pkeq(r, 0)
    pkre(str({"positional_arg": p, "keyword_arg": k}), str(capsys.readouterr()[0]))
