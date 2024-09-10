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


class _WebRequestHandler(tornado.web.RequestHandler):
    async def get(self, *args, **kwargs):
        # method is argument to request object, which is just self
        await ReqBase.http_request(self)

    async def post(self, *args, **kwargs):
        await ReqBase.http_request(self)

    async def put(self, *args, **kwargs):
        await ReqBase.http_request(self)

    def write_error(self, status_code, *args, **kwargs):
        if status_code >= 500 and (e := kwargs.get("exc_info")):
            pkdlog("exception={} stack={}", e[1], pkdexc(e))
        super().write_error(status_code, *args, **kwargs)


class _WebRequestRouter:

    async def get(self, *args, **kwargs):
        await self._pk_get(self.__authenticate())

    async def post(self, *args, **kwargs):
        await self._pk_post(self.__authenticate())

    async def put(self, *args, **kwargs):
        await self._pk_put(self.__authenticate())

    def write_error(self, status_code, *args, **kwargs):
        if status_code >= 500 and (e := kwargs.get("exc_info")):
            pkdlog("exception={} stack={}", e[1], pkdexc(e))
        super().write_error(status_code, *args, **kwargs)

    def _pk_authenticate(self, token, *args, **kwargs):
        if token != self.pk_secret():
            raise self._pk_error_forbidden()

    async def _pk_post(self, path, *args, **kwargs):
        def _result(value):
            return PKDict(result=value).pksetdefault(state="ok")

        try:
            # content type and separate parser so can be backwards compatible
            r = pkjson.load_any(self.request.body)
            # note that args may be empty (but must be PKDict), since uri has path
            if not isinstance(a := r.get("args"), PKDict):
                raise AssertionError(f"invalid post path={path} args={a}")
            if not (m := r.get("method")):
                raise AssertionError(f"missing method path={path} args={a}")
            self.write(_result(await getattr(self, "_pk_post_" + m)(path, a)))
        except Exception as e:
            pkdlog(
                "uri={} body={} exception={} stack={}",
                self.request.path,
                self.request.body,
                e,
                pkdexc(),
            )
            # version and content type
            self.write({state: "error"})


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
                    log_function=self.http_log,
                ),
                xheaders=True,
            ).listen(p, i)
            pkdlog("name={} ip={} port={}", http_cfg.get("name"), p, i)
            await asyncio.Event().wait()

        if self._http_server:
            raise AssertionError("http_server may only be called once")
        self._http_server = True
        self.run(_do())

    def http_log(self, handler, which="end", fmt="", args=None):
        def _remote_peer(request):
            # https://github.com/tornadoweb/tornado/issues/2967#issuecomment-757370594
            # implementation may change; Code in tornado.httputil check connection.
            if c := request.connection:
                # socket is not set on stream for websockets.
                if hasattr(c, "stream") and hasattr(c.stream, "socket"):
                    return "{}:{}".format(*c.stream.socket.getpeername())
            i = request.headers.get("proxy-for", request.remote_ip)
            return f"{i}:0"

        r = handler.request
        f = "{} ip={} uri={}"
        a = [which, _remote_peer(r), r.uri]
        if fmt:
            f += " " + fmt
            a += args
        elif which == "start":
            f += " proto={} {} ref={} ua={}"
            a += [
                r.method,
                r.version,
                r.headers.get("Referer") or "",
                r.headers.get("User-Agent") or "",
            ]
        else:
            f += " status={} ms={:.2f}"
            a += [
                handler.get_status(),
                r.request_time() * 1000.0,
            ]
        pkdlog(f, *a)

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
    return asyncio.create_task(coro)


async def sleep(secs):
    await asyncio.sleep(secs)


def _init():
    global _cfg
    if _cfg:
        return
    _cfg = pkconfig.init(
        debug=(False, bool, "enable debugging for asyncio"),
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
