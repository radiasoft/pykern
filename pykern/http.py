"""HTTP server

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc, pkdformat
import inspect
import msgpack
import pykern.pkasyncio
import pykern.pkcollections
import pykern.pkconfig
import pykern.quest
import re
import tornado.web


#: Http auth header name
_AUTH_HEADER = "Authorization"

#: http auth header scheme bearer
_AUTH_HEADER_SCHEME_BEARER = "Bearer"

#: POSIT: Matches anything generated by `unique_key`
_UNIQUE_KEY_CHARS_RE = r"\w+"

#: Regex to test format of auth header and extract token
_AUTH_HEADER_RE = re.compile(
    _AUTH_HEADER_SCHEME_BEARER + r"\s+(" + _UNIQUE_KEY_CHARS_RE + ")",
    re.IGNORECASE,
)

_CONTENT_TYPE_HEADER = "Content-Type"
_CONTENT_TYPE = "application/msgpack"

_VERSION_HEADER = "X-PyKern-HTTP-Version"

_VERSION_HEADER_VALUE = "1"

_API_NAME_RE = re.compile(rf"^{pykern.quest.API.METHOD_PREFIX}(\w+)")


def server_start(api_classes, attr_classes, http_config):
    l = pykern.pkasyncio.Loop()
    _HTTPServer(l, api_classes, attr_classes, http_config)
    l.start()


class Reply:

    def __init__(self, result=None, exc=None, api_error=None):
        def _exception(exc):
            if exc is None:
                pkdlog("ERROR: no reply and no exception")
                return 500
            if isinstance(exc, NotFound):
                return 404
            if isinstance(exc, Forbidden):
                return 403
            pkdlog("untranslated exception={}", exc)
            return 500

        if isinstance(result, Reply):
            self.http_status = result.http_status
            self.content = result.content
        elif result is not None or api_error is not None:
            self.http_status = 200
            self.content = PKDict(
                api_error=api_error,
                api_result=result,
            )
        else:
            self.http_status = _exception(exc)
            self.content = None


class ReplyExc(Exception):
    """Raised to end the request.

    Args:
        pk_args (dict): exception args that specific to this module
        log_fmt (str): server side log data
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        if "pk_args" in kwargs:
            self.pk_args = kwargs["pk_args"]
            del kwargs["pk_args"]
        else:
            self.pk_args = PKDict()
        if args or kwargs:
            kwargs["pkdebug_frame"] = inspect.currentframe().f_back.f_back
            pkdlog(*args, **kwargs)

    def __repr__(self):
        a = self.pk_args
        return "{}({})".format(
            self.__class__.__name__,
            ",".join(
                ("{}={}".format(k, a[k]) for k in sorted(a.keys())),
            ),
        )

    def __str__(self):
        return self.__repr__()


class APIError(ReplyExc):
    """Raised by server/client for application level errors"""

    def __init__(self, api_error_fmt, *args, **kwargs):
        super().__init__(
            pk_args=PKDict(api_error=pkdformat(api_error_fmt, *args, **kwargs)),
        )


class Forbidden(ReplyExc):
    """Raised for forbidden or protocol error"""

    pass


class InvalidResponse(ReplyExc):
    """Raised when the reply is invalid (client)"""

    pass


class NotFound(ReplyExc):
    """Raised for an object not found"""

    pass


class HTTPClient:
    def __init__(self, http_config):
        self._uri = (
            f"http://{http_config.tcp_ip}:{http_config.tcp_port}{http_config.api_uri}"
        )
        self._headers = PKDict(
            {
                _AUTH_HEADER: f"{_AUTH_HEADER_SCHEME_BEARER} {_auth_secret(http_config.auth_secret)}",
                _CONTENT_TYPE_HEADER: _CONTENT_TYPE,
                _VERSION_HEADER: _VERSION_HEADER_VALUE,
            }
        )
        self._tornado = tornado.httpclient.AsyncHTTPClient(force_instance=True)

    async def post(self, api_name, api_arg):
        r = await self._tornado.fetch(
            self._uri,
            body=_pack_msg(PKDict(api_name=api_name, api_arg=api_arg)),
            headers=self._headers,
            method="POST",
        )
        rv, e = _unpack_msg(r)
        if e:
            raise InvalidResponse(*e)
        if rv.api_error:
            raise APIError(
                "api_error={} api_name={} api_arg={}", rv.api_error, api_name, api_arg
            )
        return rv.api_result


class _HTTPRequestHandler(tornado.web.RequestHandler):
    def initialize(self, server):
        self.pykern_http_server = server

    async def get(self):
        await self.pykern_http_server.dispatch(self)

    async def post(self):
        await self.pykern_http_server.dispatch(self)


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
        h.uri_map = ((h.api_uri, _HTTPRequestHandler, PKDict(server=self)),)
        self.api_uri = h.pkdel("api_uri")
        loop.http_server(h)

    async def dispatch(self, handler):
        async def _call(api, api_arg):
            with pykern.quest.start(api.api_class, self.attr_classes) as qcall:
                return await getattr(qcall, api.api_func_name)(api_arg)

        m = None
        try:
            try:
                self.loop.http_log(handler, "start")
                self._authenticate(handler)
                m, e = _unpack_msg(handler.request)
                if e:
                    raise Forbidden(*e)
                if not (a := self.api_map.get(m.api_name)):
                    raise NotFound("unknown api={}", m.api_name)
                r = Reply(result=await _call(a, m.api_arg))
            except APIError as e:
                r = Reply(api_error=e.pk_args.api_error)
            except Exception as e:
                self.loop.http_log(
                    handler,
                    "error",
                    fmt="exception={} msg={} stack={}",
                    args=[e, m, pkdexc()],
                )
                r = Reply(exc=e)
            self._send_reply(handler, r)
        except Exception as e:
            pkdlog("unhandled exception={} stack={}", e, pkdexc())
            raise

    def _authenticate(self, handler):
        def _token(headers):
            if not (h := headers.get(_AUTH_HEADER)):
                return None
            if m := _AUTH_HEADER_RE.search(h):
                return m.group(1)
            return None

        if handler.request.method != "POST":
            raise Forbidden()
        if t := _token(handler.request.headers):
            if t == self.auth_secret:
                return
            raise Forbidden("token mismatch")
        raise Forbidden("no token")

    def _send_reply(self, handler, reply):
        if (c := reply.content) is None:
            m = b""
        else:
            m = _pack_msg(c)
        handler.set_header(_CONTENT_TYPE_HEADER, _CONTENT_TYPE)
        handler.set_header(_VERSION_HEADER, _VERSION_HEADER_VALUE)
        handler.set_header("Content-Length", str(len(m)))
        handler.set_status(reply.http_status)
        handler.write(m)


def _auth_secret(value):
    if value:
        if len(value) < 16:
            raise AssertionError("secret too short len={len(value)} (<16)")
        return value
    if pykern.pkconfig.in_dev_mode():
        return "default_dev_secret"
    raise AssertionError("must supply http_config.auth_secret")


def _pack_msg(content):
    p = msgpack.Packer(autoreset=False)
    p.pack(content)
    # TODO(robnagler) getbuffer() would be better
    return p.bytes()


def _unpack_msg(request):
    def _header(name, value):
        if not (v := request.headers.get(name)):
            return ("missing header={}", name)
        if v != value:
            return ("unexpected {}={}", name, c)
        return None

    if e := (
        _header(_VERSION_HEADER, _VERSION_HEADER_VALUE)
        or _header(_CONTENT_TYPE_HEADER, _CONTENT_TYPE)
    ):
        return None, e
    u = msgpack.Unpacker(
        object_pairs_hook=pykern.pkcollections.object_pairs_hook,
    )
    u.feed(request.body)
    return u.unpack(), None
