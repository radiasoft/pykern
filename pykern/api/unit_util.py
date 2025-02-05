"""Support for `pykern.api` tests

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# Defer as many pykern imports as possible to defer pkconfig runing
from pykern.pkcollections import PKDict
import os
import signal
import time

_AUTH_TOKEN = "http_unit_auth_secret"


class Setup:
    """Usage::

        async with http_unit.Setup(api_classes=(_class())) as c:
            from pykern.pkcollections import PKDict
            from pykern import pkunit

            e = PKDict(ping="pong")
            pkunit.pkeq(e.pkupdate(counter=1), await c.call_api("echo", e))
            pkunit.pkeq(e.pkupdate(counter=2), await c.call_api("echo", e))

    May be subclassed to start multiple servers.
    """

    def __init__(self, **server_config):
        # Must be first
        self._global_config()
        self.http_config = self._http_config()
        self.server_config = self._server_config(server_config)
        self.server_pid = self._server_process()
        time.sleep(2)
        self.client = self._client()

    def destroy(self):
        """Destroy client and kill attributes ``*_pid`` attrs"""

        self.client.destroy()
        for p in filter(lambda x: x.endswith("_pid"), dir(self)):
            try:
                os.kill(getattr(self, p), signal.SIGKILL)
            except Exception:
                pass

    def _client(self):
        """Creates a client to be used for requests.

        Called in `__init__`.

        Returns:
            object: http client, set to ``self.client``
        """
        from pykern.api import client

        return client.Client(self.http_config.copy())

    def _client_awaitable(self):
        """How to connect to client

        Awaited in `__aenter__`.

        Returns:
            Awaitable: coroutine to connect to client
        """
        return self.client.connect(PKDict(token=_AUTH_TOKEN))

    def _global_config(self, **kwargs):
        """Initializes os.environ and pkconfig

        Called first.

        Args:
            kwargs (dict): merged into environ and config (from subclasses)
        """

        c = PKDict(
            PYKERN_PKDEBUG_WANT_PID_TIME="1",
            **kwargs,
        )
        os.environ.update(**c)
        from pykern import pkconfig

        pkconfig.reset_state_for_testing(c)

    def _http_config(self):
        """Initializes ``self.http_config``

        Returns:
            PKDict: configuration to be shared with client and server
        """
        from pykern import pkconst, util

        return PKDict(
            # any uri is fine
            api_uri="/api_unit",
            # just needs to be >= 16 word (required by http) chars; apps should generate this randomly
            tcp_ip=pkconst.LOCALHOST_IP,
            tcp_port=util.unbound_localhost_tcp_port(),
        )

    def _server_config(self, init_config):
        """Config to be passed to `pykern.api.server.start` in `server_start`

        A simple `pykern.api.auth_api.AuthAPI` implementation is defaulted if not in ``init_config.api_classes``.

        Args:
            init_config (dict): what was passed to `__init__`
        Returns:
            PKDict: configuration for `server_start`
        """

        def _api_classes(init_classes):
            from pykern import pkdebug
            from pykern.api import auth_api

            class AuthAPI(auth_api.AuthAPI):

                def token(self):
                    return _AUTH_TOKEN

            return init_classes + [AuthAPI]

        rv = PKDict(init_config) if init_config else PKDict()
        rv.pksetdefault(
            api_classes=(),
            attr_classes=(),
            coros=(),
            http_config=PKDict,
        )
        rv.http_config.pksetdefault(**self.http_config)
        rv.api_classes = _api_classes(list(rv.api_classes))
        return rv

    def _server_process(self):
        """Call `server_start` in separate process

        Override this method to start multiple servers, saving pids in
        attributes that end in ``_pid`` so that `destroy` will kill
        them.

        Returns:
            int: pid of process

        """
        from pykern import pkdebug

        if rv := os.fork():
            return rv
        try:
            pkdebug.pkdlog("start server")
            self._server_start()
        except Exception as e:
            pkdebug.pkdlog("exception={} stack={}", e, pkdebug.pkdexc())
        finally:
            os._exit(0)

    def _server_start(self):
        """Calls api.server.start with ``self.server_config``"""
        from pykern.api import server

        server.start(**self.server_config)

    async def __aenter__(self):
        await self._client_awaitable()
        return self.client

    async def __aexit__(self, *args, **kwargs):
        self.destroy()
        return False
