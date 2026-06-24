"""test web mirror

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_mirror():
    from pykern import pkunit, pkyaml
    from pykern.pkcli import web

    for d in pkunit.case_dirs():
        a = pkyaml.load_file("test.yaml")
        with pkunit.WebServer(d) as s:
            web.mirror(
                s.url + a.url_prefix,
                str(d.join("out")),
                contact_mailto=a.get("contact_mailto"),
            )
