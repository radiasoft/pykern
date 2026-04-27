"""test web mirror

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


def test_mirror():
    from pykern import pkunit
    from pykern.pkcli import web

    with pkunit.save_chdir_work():
        d = pkunit.data_dir()
        h = _Server(d)
        h.start()
        try:
            web.mirror(f"http://localhost:{h.port}/en", "out")
        finally:
            h.stop()
        _check_output(pkunit.work_dir().join("out"))


def _check_output(out):
    from pykern import pkunit

    pkunit.pkok(out.join("index.html").exists(), "index.html missing")
    i = out.join("index.html").read()
    pkunit.pkre("hello", i)
    pkunit.pkok("googletagmanager" not in i, "analytics not stripped")
    pkunit.pkok("gtag(" not in i, "inline analytics not stripped")
    pkunit.pkok(out.join("about/index.html").exists(), "about page missing")
    pkunit.pkok(
        not out.join("contact/index.html").exists(), "contact page should be skipped"
    )
    pkunit.pkok(out.join("css/style.css").exists(), "css asset missing")
    a = out.join("about/index.html").read()
    pkunit.pkre(r"\.\./index\.html", a)


class _Server:
    def __init__(self, root):
        import functools
        import http.server
        import threading

        h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
        self._srv = http.server.HTTPServer(("localhost", 0), h)
        self.port = self._srv.server_address[1]
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._srv.shutdown()
