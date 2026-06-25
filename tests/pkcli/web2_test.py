"""integration test for web mirror against a live site


PYKERN_PKCLI_WEB2_TEST_ARGS='url=https://sirepo.wpengine.com/en contact_mailto=info@sirepo.com' pykern test web2_test.py

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import os
import pytest


def test_mirror():
    from pykern.pkcollections import PKDict
    from pykern import pkunit
    from pykern.pkcli import web

    def _args():
        v = os.environ.get("PYKERN_PKCLI_WEB2_TEST_ARGS")
        if not v:
            pytest.skip("PYKERN_PKCLI_WEB2_TEST_ARGS not set")
        a = PKDict(dict(x.split("=", 1) for x in v.split()))
        if "contact_mailto" in a and not a.contact_mailto.startswith("mailto:"):
            a.contact_mailto = "mailto:" + a.contact_mailto
        return a

    a = _args()
    d = pkunit.empty_work_dir()
    pkunit.pkre(
        r"wrote \d+ pages",
        web.sirepo_wp_mirror(
            a.url,
            str(d),
            rules_file=(
                pkunit.data_dir().join(f"{a.rules_file}.yaml")
                if a.get("rules_file")
                else None
            ),
            contact_mailto=a.get("contact_mailto"),
        ),
    )
    pkunit.pkok(
        list(d.visit(fil=lambda p: p.ext == ".css")),
        "no CSS files downloaded",
    )
    pkunit.pkok(
        "window.location" not in d.join("index.html").read(),
        "index.html contains app redirect",
    )
