"""Wrapper on asyncio and tornado

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern.pkdebug import pkdlog, pkdp
import asyncio
import inspect
import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web

_cfg = None


class Loop:
    def __init__(self):
        _init()
        self._coroutines = []

    def http_server(self, http_cfg):
        """Instantiate a tornado web server

        Under the covers Tornado uses the asyncio event loop so asyncio methods
        can be mixed with Tornado methods.

        To start the server you can call the returned function. Or you can use any of the
        asyncio methods that run the event loop (ex asyncio.run).

        Using asyncio methods (ex asyncio.run()) is prefered over Tornado methods (ex.
        tornado.ioloop.IOLoop.current().start()) to reduce leaking out details of Tornado.

        Args:
            http_cfg (PKDict): object with uri_map and overrides for server defaults
        """

        async def _do():
            # TODO(e-carlin): pull in the one in job_supervisor.py
            p = http_cfg.get("tcp_port", _cfg.server_port)
            i = http_cfg.get("tcp_ip", _cfg.server_ip)
            tornado.httpserver.HTTPServer(
                tornado.web.Application(
                    http_cfg.uri_map,
                    debug=http_cfg.get("debug", _cfg.debug),
                ),
                xheaders=True,
            ).listen(p, i)
            pkdlog("ip={} port={}", p, i)
            await asyncio.Event().wait()

        self.run(_do())

    def run(self, *coros):
        for c in coros:
            if not inspect.iscoroutine(c):
                raise ValueError(f"{c} in coros={coros} is not a coroutine")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self._coroutines.extend(coros)
            return
        raise AssertionError("cannot call after event loop has started")

    def start(self):
        async def _do():
            await asyncio.gather(*self._coroutines)

        assert self._coroutines, "nothing to await"
        asyncio.run(_do(), debug=_cfg.debug)


async def sleep(secs):
    await asyncio.sleep(secs)


def _cfg_port(value):
    v = int(value)
    l = 3000
    u = 32767
    if not l <= v <= u:
        pkconfig.raise_error(f"value must be from {l} to {u}")
    return v


def _init():
    global _cfg
    if _cfg:
        return
    _cfg = pkconfig.init(
        debug=(False, bool, "enable debugging for asyncio"),
        server_ip=(
            "0.0.0.0" if pkconfig.in_dev_mode() else "127.0.0.1",
            str,
            "ip to listen on",
        ),
        server_port=("9001", _cfg_port, "port to listen on"),
    )
