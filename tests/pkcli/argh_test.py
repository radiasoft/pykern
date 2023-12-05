# -*- coding: utf-8 -*-
"""pytest for `pykern.pkcli.argh_test`

:copyright: Copyright (c) 2023 RadiaSoft, LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_kwarg_to_positional():
    from pykern.pkunit import pkre
    from pykern.pkcollections import PKDict
    import subprocess

    p = "p"
    k = "k"
    pkre(
        str(PKDict(positional_arg=p, keyword_arg=k)),
        subprocess.check_output(
            ("pykern", "argh_test", "kwarg-to-positional", p, "--keyword-arg", k),
            text=True,
        ),
    )
