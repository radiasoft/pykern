"""support for `pykern.http` tests

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# Defer imports for unit tests


class Setup:

    def __init__(self, api_classes, attr_classes=(), coros=()):
        import os, time
        from pykern.pkcollections import PKDict

        def _global_config():
            c = PKDict(
                PYKERN_PKDEBUG_WANT_PID_TIME="1",
            )
            os.environ.update(**c)
            from pykern import pkconfig

            pkconfig.reset_state_for_testing(c)

        def _http_config():
            from pykern import pkconst, pkunit

            return PKDict(
                # any uri is fine
                api_uri="/http_unit",
                # just needs to be >= 16 word (required by http) chars; apps should generate this randomly
                auth_secret="http_unit_auth_secret",
                tcp_ip=pkconst.LOCALHOST_IP,
                tcp_port=pkunit.unbound_localhost_tcp_port(),
            )

        def _server():
            from pykern import pkdebug, http

            if rv := os.fork():
                return rv
            try:
                pkdebug.pkdlog("start server")
                http.server_start(
                    attr_classes=attr_classes,
                    api_classes=api_classes,
                    http_config=self.http_config.copy(),
                    coros=coros,
                )
            except Exception as e:
                pkdebug.pkdlog("server exception={} stack={}", e, pkdebug.pkdexc())
            finally:
                os._exit(0)

        _global_config()
        self.http_config = _http_config()
        self.server_pid = _server()
        time.sleep(1)
        from pykern import http

        self.client = http.HTTPClient(self.http_config.copy())

    def destroy(self):
        import os, signal

        os.kill(self.server_pid, signal.SIGKILL)

    def __enter__(self):
        return self.client

    def __exit__(self, *args, **kwargs):
        self.client.destroy()
        return False
