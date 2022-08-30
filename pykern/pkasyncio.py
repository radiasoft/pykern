"""Wrapper on asyncio and tornado

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern.pkdebug import pkdlog, pkdp
import asyncio
import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web

cfg = None


class Loop:
    def __init__(self):
        self.coroutines = []

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
            p = http_cfg.get("tcp_port", cfg.server_port)
            i = http_cfg.get("tcp_ip", cfg.server_ip)
            tornado.httpserver.HTTPServer(
                tornado.web.Application(
                    http_cfg.uri_map,
                    debug=http_cfg.get("debug", pkconfig.channel_in("dev")),
                ),
                xheaders=True,
            ).listen(p, i)
            pkdlog("ip={} port={}", p, i)
            await asyncio.Event().wait()

        self.run(_do())

    def run(self, *coros):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self.coroutines.extend(coros)
            return
        raise AssertionError("cannot call after event loop has started")

    def start(self):
        async def _do():
            await asyncio.gather(*self.coroutines)

        assert self.coroutines, "nothing to await"
        asyncio.run(_do(), debug=cfg.debug)


async def sleep(secs):
    await asyncio.sleep(secs)


def _cfg_port(value):
    v = int(value)
    l = 3000
    u = 32767
    assert l <= v <= u, "value must be from {} to {}".format(l, u)
    return v


def _init():
    global cfg
    if cfg:
        return
    cfg = pkconfig.init(
        debug=(pkconfig.channel_in("dev"), bool, "enable debugging for asyncio"),
        server_ip=("127.0.0.1", str, "ip to listen on"),
        server_port=("9001", _cfg_port, "port to listen on"),
    )


_init()
