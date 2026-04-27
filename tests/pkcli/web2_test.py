"""integration test for web mirror against a live site

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import os
import pytest


def test_mirror():
    from pykern import pkresource, pkunit
    from pykern.pkcli import web

    def _args():
        v = os.environ.get("PYKERN_PKCLI_WEB2_ARGS")
        if not v:
            pytest.skip("PYKERN_PKCLI_WEB2_ARGS not set")
        return {k: w for k, w in (a.split("=", 1) for a in v.split())}

    a = _args()
    r = pkresource.filename(f'web/rules/{a["rules"]}.yaml', caller_context=web)
    o = pkunit.empty_work_dir().join("out")
    result = web.mirror(a["url"], str(o), r)
    pkunit.pkre(r"wrote \d+ pages", result)
    pkunit.pkok(
        list(o.visit(fil=lambda p: p.ext == ".css")),
        "no CSS files downloaded",
    )
    pkunit.pkok(
        "window.location" not in o.join("index.html").read(),
        "index.html contains app redirect",
    )
