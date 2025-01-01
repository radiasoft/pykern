"""HTTP server & client

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc, pkdformat
import asyncio
import inspect
import msgpack
import pykern.pkasyncio
import pykern.pkcollections
import pykern.pkconfig
import pykern.quest
import re
import tornado.httpclient
import tornado.web
import tornado.websocket


#: Http auth header name
_AUTH_HEADER = "Authorization"

#: http auth header scheme bearer
_AUTH_HEADER_SCHEME_BEARER = "Bearer"

#: POSIT: Matches anything generated by `unique_key`
_UNIQUE_KEY_CHARS_RE = r"\w+"

#: validates auth secret (only word chars)
_AUTH_SECRET_RE = re.compile(f"^{_UNIQUE_KEY_CHARS_RE}$")

#: Regex to test format of auth header and extract token
_AUTH_HEADER_RE = re.compile(
    _AUTH_HEADER_SCHEME_BEARER + r"\s+(" + _UNIQUE_KEY_CHARS_RE + ")",
    re.IGNORECASE,
)

_VERSION_HEADER = "X-PyKern-HTTP-Version"

_VERSION_HEADER_VALUE = "1"

_API_NAME_RE = re.compile(rf"^{pykern.quest.API.METHOD_PREFIX}(\w+)")


def server_start(api_classes, attr_classes, http_config, coros=()):
    """Start the `_HTTPServer` in asyncio

    Args:
        api_classes (Iterable): `pykern.quest.API` subclasses to be dispatched
        attr_classes (Iterable): `pykern.quest.Attr` subclasses to create API instance
        http_config (PKDict): auth_secret and `pkasyncio.Loop.http_server` arg
        coros (Iterable): list of coroutines to be passed to `pkasyncio.Loop.run`
    """
    l = pykern.pkasyncio.Loop()
    _HTTPServer(l, api_classes, attr_classes, http_config)
    if coros:
        l.run(*coros)
    l.start()


class APICallError(pykern.quest.APIError):
    """Raised for an object not found"""

    def __init__(self, exception):
        super().__init__("exception={}", exception)


class APIDisconnected(pykern.quest.APIError):
    """Raised when remote server closed or other error"""

    def __init__(self):
        super().__init__("")


class APIForbidden(pykern.quest.APIError):
    """Raised for forbidden or protocol error"""

    def __init__(self):
        super().__init__("")


class APINotFound(pykern.quest.APIError):
    """Raised for an object not found"""

    def __init__(self, api_name):
        super().__init__("api_name={}", api_name)


class HTTPClient:
    """Wrapper for `tornado.httpclient.AsyncHTTPClient`

    Maybe called as an async context manager

    `http_config.request_config` is deprecated.

    Args:
        http_config (PKDict): tcp_ip, tcp_port, api_uri, auth_secret
    """

    def __init__(self, http_config):
        # TODO(robnagler) tls with verification(?)
        self.uri = (
            f"ws://{http_config.tcp_ip}:{http_config.tcp_port}{http_config.api_uri}"
        )
        self.auth_secret = _auth_secret(http_config.auth_secret)
        self._connection = None
        self._destroyed = False
        self._call_id = 0
        self._pending_calls = PKDict()

    async def call_api(self, api_name, api_args):
        """Make a request to the API server

        Args:
            api_name (str): what to call on the server
            api_args (PKDict): passed verbatim to the API on the server.
        Returns:
            str: value of `api_result`.
        Raises:
           APIError: if there was an raise in the API or on a server protocol violation
           Exception: other exceptions that `AsyncHTTPClient.fetch` may raise, e.g. NotFound
        """

        def _send():
            self._call_id += 1
            c = PKDict(api_name=api_name, api_args=api_args, call_id=self._call_id)
            rv = _ClientCall(c)
            self._pending_calls[rv.call_id] = rv
            self._connection.write_message(_pack_msg(c), binary=True)
            return rv

        # TODO(robnagler) backwards compatibility
        if not self._connection:
            # will check destroyed
            await self.connect()
            if self._destroyed:
                return
        return await _send().reply_get()

    async def connect(self):
        if self._destroyed:
            raise AssertionError("destroyed")
        if self._connection:
            raise AssertionError("already connected")
        self._connection = await tornado.websocket.websocket_connect(
            tornado.httpclient.HTTPRequest(
                self.uri,
                headers={
                    _AUTH_HEADER: f"{_AUTH_HEADER_SCHEME_BEARER} {self.auth_secret}",
                    _VERSION_HEADER: _VERSION_HEADER_VALUE,
                },
                method="GET",
            ),
            # TODO(robnagler) accept in http_config. share defaults with sirepo.job.
            max_message_size=int(2e8),
            ping_interval=120,
            ping_timeout=240,
        )
        asyncio.create_task(self._read_loop())

    def destroy(self):
        """Must be called"""
        if self._destroyed:
            return
        self._destroyed = True
        if self._connection:
            self._connection.close()
            self._connection = None
        x = self._pending_calls
        self._pending_calls = None
        for c in x.values():
            c.reply_q.put_nowait(None)

    async def __aenter__(self):
        await self.connect()
        if self._destroyed:
            raise APIDisconnected()
        return self

    async def __aexit__(self, *args, **kwargs):
        self.destroy()
        return False

    async def _read_loop(self):
        def _unpack(msg):
            r, e = _unpack_msg(msg)
            if e:
                pkdlog("unpack msg error={} {}", e, self)
                return None
            return r

        m = r = None
        try:
            if self._destroyed:
                return
            while m := await self._connection.read_message():
                if self._destroyed:
                    return
                if not (r := _unpack(m)):
                    break
                # Remove from pending
                if not (c := self._pending_calls.pkdel(r.call_id)):
                    pkdlog("call_id not found reply={} {}", r, self)
                    # TODO(robnagler) possibly too harsh, but safer for now
                    break
                c.reply_q.put_nowait(r)
                m = r = None
        except Exception as e:
            pkdlog("exception={} reply={} stack={}", e, r, pkdexc())
        try:
            if not self._destroyed:
                self.destroy()
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())

    def __repr__(self):
        def _calls():
            return ", ".join(
                (
                    f"{v.api_name}#{v.call_id}"
                    for v in sorted(
                        self._pending_calls.values(), key=lambda x: x.call_id
                    )
                ),
            )

        def _destroyed():
            return "DESTROYED, " if self._destroyed else ""

        return f"{self.__class__.__name__}({_destroyed()}call_id={self._call_id}, calls=[{_calls()}])"


class _ClientCall(PKDict):
    def __init__(self, call_msg):
        super().__init__(**call_msg)
        # TODO(robnagler) should be one for regular replies
        self.reply_q = tornado.queues.Queue()
        self._destroyed = False

    async def reply_get(self):
        rv = await self.reply_q.get()
        if self._destroyed:
            raise APIDisconnected()
        self.reply_q.task_done()
        self.destroy()
        if rv is None:
            raise APIDisconnected()
        if rv.api_error:
            raise pykern.quest.APIError(rv.api_error)
        return rv.result

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        self.reply_q = None


class _HTTPServer:

    def __init__(self, loop, api_classes, attr_classes, http_config):
        def _api_class_funcs():
            for c in api_classes:
                for n, o in inspect.getmembers(c, predicate=inspect.isfunction):
                    yield PKDict(api_class=c, api_func=o, api_func_name=n)

        def _api_map():
            rv = PKDict()
            for a in _api_class_funcs():
                n = a.api_func_name
                if not ((m := _API_NAME_RE.search(n)) and n in a.api_class.__dict__):
                    continue
                a.api_name = m.group(1)
                if a.api_name in rv:
                    raise AssertionError(
                        "duplicate api={a.api_name} class={a.api_class.__name__}"
                    )
                if not inspect.iscoroutinefunction(a.pkdel("api_func")):
                    raise AssertionError(
                        "api_func={n} is not async class={a.api_class.__name__}"
                    )
                rv[a.api_name] = a
            return rv

        h = http_config.copy()
        self.loop = loop
        self.api_map = _api_map()
        self.attr_classes = attr_classes
        self.auth_secret = _auth_secret(h.pkdel("auth_secret"))
        h.uri_map = ((h.api_uri, _ServerHandler, PKDict(server=self)),)
        self.api_uri = h.pkdel("api_uri")
        h.log_function = self._log_end
        self._ws_id = 0
        loop.http_server(h)

    def handle_get(self, handler):
        def _authenticate(headers):
            if not (h := headers.get(_AUTH_HEADER)):
                return "no auth token"
            if not (m := _AUTH_HEADER_RE.search(h)):
                return "auth token format invalid"
            if m.group(1) != self.auth_secret:
                return "auth token mismatch"
            return None

        def _validate_version(headers):
            if not (v := headers.get(_VERSION_HEADER)):
                return f"missing {_VERSION_HEADER} header"
            if v != _VERSION_HEADER_VALUE:
                return f"invalid version {v}"
            return None

        try:
            self._log(handler, "start")
            h = handler.request.headers
            if e := _authenticate(h):
                k = PKDict(status_code=403, reason="Forbidden")
            elif e := _validate_version(h):
                k = PKDict(status_code=412, reason="Precondition Failed")
            else:
                return True
            handler.pykern_context.error = e
            handler.send_error(**k)
            return False
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())
            self._log(handler, "error", "exception={}", [e])
            return False

    def handle_open(self, handler):
        try:
            self._ws_id += 1
            handler.pykern_context.ws_id = self._ws_id
            return _ServerConnection(self, handler, ws_id=self._ws_id)
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())
            self._log(handler, "error", "exception={}", [e])
            return None

    def _log(self, handler, which, fmt="", args=None):
        def _add(key, value):
            nonlocal f, a
            if value is not None:
                f += (" " if f else "") + key + "={}"
                a.append(value)

        f = ""
        a = []
        if x := getattr(handler, "pykern_context", None):
            _add("error", x.pkdel("error"))
            _add("ws_id", x.get("ws_id"))
        if fmt:
            f = f + " " + fmt
            a.extend(args)
        self.loop.http_log(handler, which, f, a)

    def _log_end(self, handler):
        self._log(handler, "end")


class _ServerConnection:

    def __init__(self, server, handler, ws_id):
        self.ws_id = ws_id
        self.server = server
        self.handler = handler
        self._destroyed = False
        self.remote_peer = server.loop.remote_peer(handler.request)
        self._log("open")

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        self.handler.close()
        self.handler = None

    def handle_on_close(self):
        if self._destroyed:
            return
        self.handler = None
        self._log("on_close")
        # TODO(robnagler) deal with open requests

    async def handle_on_message(self, msg):
        def _api(call):
            if n := call.get("api_name"):
                if rv := self.server.api_map.get(n):
                    return rv
            else:
                n = "<missing>"
            self._log("error", call, "api not found={}", [n])
            _reply(c, APINotFound(n))
            return None

        async def _call(call, api, api_args):
            with pykern.quest.start(api.api_class, self.server.attr_classes) as qcall:
                try:
                    return await getattr(qcall, api.api_func_name)(api_args)
                except Exception as e:
                    pkdlog("exception={} call={} stack={}", call, e, pkdexc())
                    return APICallError(e)

        def _reply(call, obj):
            try:
                if not isinstance(obj, Exception):
                    r = PKDict(result=obj, api_error=None)
                elif isinstance(obj, pykern.quest.APIError):
                    r = PKDict(result=None, api_error=str(obj))
                else:
                    r = PKDict(result=None, api_error=f"unhandled_exception={obj}")
                r.call_id = call.call_id
                self.handler.write_message(_pack_msg(r), binary=True)
            except Exception as e:
                pkdlog("exception={} call={} stack={}", call, e, pkdexc())
                self.destroy()

        c = None
        try:
            c, e = _unpack_msg(msg)
            if e:
                self._log("error", None, "msg unpack error={}", [e])
                self.destroy()
                return None
            self._log("start", c)
            if not (a := _api(c)):
                return
            r = await _call(c, a, c.api_args)
            if self._destroyed:
                return
            _reply(c, r)
            self._log("end", c)
            c = None
        except Exception as e:
            pkdlog("exception={} call={} stack={}", e, c, pkdexc())
            _reply(c, e)

    def _log(self, which, call=None, fmt="", args=None):
        if fmt:
            fmt = " " + fmt
        pkdlog(
            "{} ip={} ws={}#{}" + fmt,
            which,
            self.remote_peer,
            self.ws_id,
            call and call.call_id,
            *(args if args else ()),
        )


class _ServerHandler(tornado.websocket.WebSocketHandler):
    def initialize(self, server):
        self.pykern_server = server
        self.pykern_context = PKDict()
        self.pykern_connection = None

    async def get(self, *args, **kwargs):
        if not self.pykern_server.handle_get(self):
            return
        return await super().get(*args, **kwargs)

    async def on_message(self, msg):
        # WebSocketHandler only allows one on_message at a time.
        asyncio.create_task(self.pykern_connection.handle_on_message(msg))

    def on_close(self):
        if self.pykern_connection:
            self.pykern_connection.handle_on_close()
            self.pykern_connection = None

    def open(self):
        self.pykern_connection = self.pykern_server.handle_open(self)


def _auth_secret(value):
    if value:
        if len(value) < 16:
            raise ValueError("auth_secret too short len={len(value)} (<16)")
        if not _AUTH_SECRET_RE.search(value):
            raise ValueError("auth_secret contains non-word chars")
        return value
    if pykern.pkconfig.in_dev_mode():
        return "default_dev_secret"
    raise ValueError("must supply http_config.auth_secret")


def _pack_msg(content):
    import datetime

    def _datetime(obj):
        if isinstance(obj, datetime.datetime):
            return int(obj.timestamp())
        return obj

    p = msgpack.Packer(autoreset=False, default=_datetime)
    p.pack(content)
    # TODO(robnagler) getbuffer() would be better
    return p.bytes()


def _unpack_msg(content):
    try:
        u = msgpack.Unpacker(
            object_pairs_hook=pykern.pkcollections.object_pairs_hook,
        )
        u.feed(content)
        rv = u.unpack()
    except Exception as e:
        return None, f"msgpack exception={e}"
    if not isinstance(rv, PKDict):
        return None, f"msg not dict type={type(rv)}"
    if "call_id" not in rv:
        return None, "msg missing call_id keys={list(rv.keys())}"
    i = rv.call_id
    if not isinstance(i, int):
        return None, f"msg call_id non-integer type={type(i)}"
    if i <= 0:
        return None, f"msg call_id non-positive call_id={i}"
    return rv, None
