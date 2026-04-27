"""test web mirror

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


def test_mirror():
    from pykern import pkunit
    from pykern.pkcli import web

    def _check_output(out):
        pkunit.pkok(out.join("index.html").exists(), "index.html missing")
        i = out.join("index.html").read()
        pkunit.pkre("hello", i)
        pkunit.pkok("googletagmanager" not in i, "analytics not stripped")
        pkunit.pkok("gtag(" not in i, "inline analytics not stripped")
        pkunit.pkok(out.join("about/index.html").exists(), "about page missing")
        pkunit.pkok(
            not out.join("contact/index.html").exists(),
            "contact page should be skipped",
        )
        pkunit.pkok(out.join("css/style.css").exists(), "css asset missing")
        a = out.join("about/index.html").read()
        pkunit.pkre(r'href="\.\.\/"', a)

    o = pkunit.empty_work_dir().join("out")
    with pkunit.WebServer() as s:
        web.mirror(s.url + "/en", str(o))
    _check_output(o)
