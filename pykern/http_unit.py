"""support for `pykern.http` tests

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# Defer imports for unit tests

# any uri is fine
_URI = "/http_unit"

# just needs to be >= 16 word (required by http) chars; apps should generate this randomly
#
_AUTH_SECRET = "http_unit_auth_secret"


class Setup:

    def __init__(self, api_classes, attr_classes=(), coros=()):
        import os, time
        from pykern.pkcollections import PKDict

        def _client(http_config):
            from pykern import pkdebug, http

        def _config():
            c = PKDict(
                PYKERN_PKDEBUG_WANT_PID_TIME="1",
            )
            os.environ.update(**c)
            from pykern import pkconfig

            pkconfig.reset_state_for_testing(c)

        def _http_config():
            from pykern import pkconst, pkunit

            return PKDict(
                api_uri=_URI,
                auth_secret=_AUTH_SECRET,
                tcp_ip=pkconst.LOCALHOST_IP,
                tcp_port=pkunit.unbound_localhost_tcp_port(),
            )

        def _server(http_config):
            from pykern import pkdebug, http

            p = os.fork()
            if p != 0:
                return p
            try:
                pkdebug.pkdlog("start server")
                http.server_start(
                    attr_classes=attr_classes,
                    api_classes=api_classes,
                    http_config=http_config,
                    coros=coros,
                )
            except Exception as e:
                pkdebug.pkdlog("server exception={} stack={}", e, pkdebug.pkdexc())
            finally:
                os._exit(0)

        _config()
        h = _http_config()
        self.server_pid = _server(h)
        time.sleep(1)
        from pykern import http

        self.client = http.HTTPClient(h)

    def destroy(self):
        import os, signal

        os.kill(self.server_pid, signal.SIGKILL)

    def __enter__(self):
        return self.client

    def __exit__(self, *args, **kwargs):
        self.client.destroy()
        return False
