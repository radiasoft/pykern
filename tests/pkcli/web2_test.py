"""integration test for web mirror against a live site

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import os
import pytest


def test_mirror():
    from pykern.pkcollections import PKDict
    from pykern import pkresource, pkunit
    from pykern.pkcli import web

    def _args():
        v = os.environ.get("PYKERN_PKCLI_WEB2_ARGS")
        if not v:
            pytest.skip("PYKERN_PKCLI_WEB2_ARGS not set")
        return PKDict(dict(a.split("=", 1) for a in v.split()))

    a = _args()
    d = pkunit.empty_work_dir()
    r = web.mirror(
        a.url,
        str(d),
        pkresource.filename(f"web/rules/{a.rules}.yaml", caller_context=web),
    )
    pkunit.pkre(r"wrote \d+ pages", r)
    pkunit.pkok(
        list(d.visit(fil=lambda p: p.ext == ".css")),
        "no CSS files downloaded",
    )
    pkunit.pkok(
        "window.location" not in d.join("index.html").read(),
        "index.html contains app redirect",
    )
