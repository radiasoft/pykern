"""Wrapper on asyncio and tornado

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkconst
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp
import asyncio
import inspect
import re
import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web

_cfg = None

_background_tasks = set()


class Loop:
    def __init__(self):
        _init()
        self._coroutines = []
        self._http_server = False

    def http_server(self, http_cfg):
        """Instantiate a tornado web server

        Under the covers Tornado uses the asyncio event loop so asyncio methods
        can be mixed with Tornado methods.

        Using asyncio methods, e.g. `asyncio.run`, is preferred over
        Tornado methods, e.g.  `tornado.ioloop.IOLoop.current` to
        reduce dependency on Tornado. Using this module should allow
        the code to be portable to other http server frameworks.

        ``http_config.uri_map`` maps URI expressions to classes, which
        is passed directly to `tornado.web.Application`.

        Args:
            http_cfg (PKDict): quest_start, uri_map, debug, tcp_ip, tcp_port,

        """

        async def _do():
            # TODO(e-carlin): pull in the one in job_supervisor.py
            p = http_cfg.get("tcp_port", _cfg.server_port)
            i = http_cfg.get("tcp_ip", _cfg.server_ip)
            tornado.httpserver.HTTPServer(
                tornado.web.Application(
                    http_cfg.uri_map,
                    debug=http_cfg.get("debug", _cfg.debug),
                    log_function=http_cfg.get("log_function", self.http_log),
                ),
                xheaders=True,
            ).listen(p, i)
            pkdlog("name={} ip={} port={}", http_cfg.get("name"), i, p)
            await asyncio.Event().wait()

        if self._http_server:
            raise AssertionError("http_server may only be called once")
        self._http_server = True
        self.run(_do())

    def http_log(self, handler, which="end", fmt="", args=None):
        r = handler.request
        f = "{} ip={} uri={}"
        a = [which, self.remote_peer(r), r.uri]
        if fmt:
            f += " " + fmt
            a += args
        if which == "start":
            f += " proto={} {} ref={} ua={}"
            a += [
                r.method,
                r.version,
                r.headers.get("Referer") or "",
                r.headers.get("User-Agent") or "",
            ]
        elif which == "end":
            f += " status={} ms={:.2f}"
            a += [
                handler.get_status(),
                r.request_time() * 1000.0,
            ]
        pkdlog(f, *a)

    def remote_peer(self, request):
        # https://github.com/tornadoweb/tornado/issues/2967#issuecomment-757370594
        # implementation may change; Code in tornado.httputil check connection.
        if c := request.connection:
            # socket is not set on stream for websockets.
            if getattr(c, "stream", None) and (s := getattr(c.stream, "socket", None)):
                return "{}:{}".format(*s.getpeername())
        i = request.headers.get("proxy-for", request.remote_ip)
        return f"{i}:0"

    def run(self, *coros):
        for c in coros:
            if not inspect.iscoroutine(c):
                raise AssertionError(f"must be a coroutine arg={c} coros={coros}")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self._coroutines.extend(coros)
            return
        raise AssertionError("cannot call after event loop has started")

    def start(self):
        async def _do():
            await asyncio.gather(*self._coroutines)

        if not self._coroutines:
            raise AssertionError("no coroutines registered; must have at least one")
        asyncio.run(_do(), debug=_cfg.debug)


@pkconfig.parse_none
def cfg_ip(value):
    if value is None:
        return "0.0.0.0" if pkconfig.in_dev_mode() else pkconst.LOCALHOST_IP
    return value


def cfg_port(value):
    v = int(value)
    l = 3000
    u = 32767
    if not l <= v <= u:
        pkconfig.raise_error(f"value must be from {l} to {u}")
    return v


def create_task(coro):
    """Create a task

    Keeps a global reference to the task so to avoid the garbage
    collector running before the task is run.
    https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
    """
    t = asyncio.create_task(coro)
    _background_tasks.add(t)
    t.add_done_callback(_background_tasks.discard)
    return t


async def sleep(secs):
    await asyncio.sleep(secs)


def _init():
    global _cfg
    if _cfg:
        return
    _cfg = pkconfig.init(
        debug=(pkconfig.in_dev_mode(), bool, "enable debugging for asyncio"),
        server_ip=(
            None,
            cfg_ip,
            "ip to listen on",
        ),
        server_port=("9001", cfg_port, "port to listen on"),
        verify_tls=(
            not pkconfig.channel_in("dev"),
            bool,
            "validate TLS certificates on requests; for self-signed set to False",
        ),
    )
