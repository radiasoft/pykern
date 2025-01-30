"""HTTP WebSocket server & client


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
import pykern.util
import re
import tornado.httpclient
import tornado.web
import tornado.websocket


_API_NAME_RE = re.compile(rf"^{pykern.quest.API.METHOD_PREFIX}(\w+)")


#: API that authenticates connections
AUTH_API_NAME = "pykern_http_auth"

#: API version (will be defaulted by `connect`
AUTH_API_VERSION = 1

_MSG_CALL = "call"
_MSG_SUBSCRIBE = "sub"
_MSG_UNSUBSCRIBE = "unsub"
_MSG_REPLY = "reply"

class AuthArgs(PKDict):
    """Passed from `HTTPClient` to api_pykern_http_auth to validate connection

    Atributes:
        client_id (str): If None, generate id, else validate id
        token (str): secret value evaluated by `AuthAPI`
        version (int): protocol version
    """

    pass


class AuthResult(PKDict):
    """State of connection

    If `client_id` is not known, a new id will be generated.

    Atributes:
        client_id (str): persistent id (originally) generated by server
    """

    pass


class AuthAPI(pykern.quest.API):

    #: Defaults version number but allows override
    PYKERN_HTTP_VERSION: int = AUTH_API_VERSION

    #: cache of local clients
    pykern_http_clients = PKDict()

    #: If None, do not validate; otherwise validate
    PYKERN_HTTP_TOKEN: str = None

    #: uniquely identify token
    PYKERN_HTTP_CLIENT_ID_PREFIX: str = "pykern_http_v1-"

    def pykern_http_validate_client(self, auth_args: AuthArgs):
        """Validates client in `auth_args`

        Args:
            auth_args (AuthArgs): what to validate
        Returns:
            AuthResult: validation result
        """
        if (
            auth_args.client_id is None
            or auth_args.client_id not in self.pykern_http_clients
        ):
            for _ in range(5):
                i = self.PYKERN_HTTP_CLIENT_ID_PREFIX + pykern.util.random_base62()
                if i not in self.pykern_http_clients:
                    auth_args.client_id = i
                    self.pykern_http_clients[i] = auth_args
                    break
            else:
                raise AssertionError("unable to generate unique client id")
        self.session.client_id = auth_args.client_id
        return AuthResult(client_id=auth_args.client_id)

    async def api_pykern_http_auth(self, auth_args: AuthArgs):
        """Process AuthRequest from server

        Args:
            auth_args (AuthArgs): what to validate
        Returns:
            AuthResult: validation result
        """
        if auth_args.version != self.PYKERN_HTTP_VERSION:
            raise APICallError(
                f"invalid version={auth_args.version}, expected={self.PYKERN_HTTP_VERSION}"
            )
        if (
            self.PYKERN_HTTP_TOKEN is not None
            and self.PYKERN_HTTP_TOKEN != auth_args.token
        ):
            raise APIForbidden()
        return self.pykern_http_validate_client(auth_args)


class APICallError(pykern.quest.APIError):
    """Raised for an object not found"""

    def __init__(self, error):
        super().__init__("error={}", error)


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
        http_config (PKDict): tcp_ip, tcp_port, api_uri
    """

    def __init__(self, http_config):
        # TODO(robnagler) tls with verification(?)
        self.uri = (
            f"ws://{http_config.tcp_ip}:{http_config.tcp_port}{http_config.api_uri}"
        )
        self.client_id = None
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

        return await self._send_api(api_name, api_args, _MSG_CALL).reply()

    async def connect(self, auth_args=None):
        """Connect to the server

        Args:
            auth_args (PKDict): how to authenticate connection; may be AuthArgs or other PKDict [None]
        Returns:
            AuthReply: status of connection
        """

        async def _auth():
            try:
                self.client_id = (
                    await self.call_api(AUTH_API_NAME, _auth_args())
                ).client_id
            except Exception as e:
                if self._destroyed:
                    return
                if self._connection:
                    self._connection.close()
                raise

        def _auth_args():
            rv = auth_args
            if rv is None:
                rv = AuthArgs()
            return rv.pksetdefault(
                client_id=None,
                token=None,
                version=AUTH_API_VERSION,
            )

        if self._destroyed:
            raise AssertionError("destroyed")
        if self._connection:
            raise AssertionError("already connected")
        self._connection = await tornado.websocket.websocket_connect(
            tornado.httpclient.HTTPRequest(self.uri, method="GET"),
            # TODO(robnagler) accept in http_config. share defaults with sirepo.job.
            max_message_size=int(2e8),
            ping_interval=120,
            ping_timeout=240,
        )
        asyncio.create_task(self._read_loop())
        await _auth()

    def destroy(self):
        """Must be called"""
        if self._destroyed:
            return
        self._destroyed = True
        self._pending_calls = None
        for c in x.values():
            c.destroy()
        if self._connection:
            self._connection.close()
            self._connection = None
        x = self._pending_calls

    async def subscribe_api(self, api_name, api_args):
        """Subscribe to api_name from API server

        Args:
            api_name (str): what to call on the server
            api_args (PKDict): passed verbatim to the API on the server.
        Returns:
            _Call: to get replies or unsubscribe
        """

        return self._send_api(api_name, api_args, _MSG_SUBSCRIBE)

    def unsubscribe_by_call_id(self, call_id):
        """Not a public interface"""
        if self._destroyed:
            return False
        if not (c := self._pending_calls.pkdel(call_id)):
            return False
        self._send_msg(PKDict(call_id=call_id, msg_kind=_MSG_UNSUBSCRIBE))

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
                if not (c := self._pending_calls.get(r.call_id)):
                    pkdlog("call_id={} not found reply={} {}", r.call_id, r, self)
                    # TODO(robnagler) possibly too harsh, but safer for now
                    break
                if not c.is_subscription:
                    self._pending_calls.pkdel(r.call_id)
                c.reply_put(r)
                # Clear all state before next await
                c = m = r = None
        except Exception as e:
            pkdlog("exception={} reply={} stack={}", e, r, pkdexc())
        try:
            if not self._destroyed:
                self.destroy()
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())

    def __repr__(self):
        def _calls():
            if not self._pending_calls:
                return ""
            return " " + " ".join(
                (
                    str(v)
                    for v in sorted(
                        self._pending_calls.values(), key=lambda x: x.call_id
                    )
                ),
            )

        if self._destroyed:
            return f"<{self.__class__.__name__} DESTROYED>"
        return f"<{self.__class__.__name__}{_calls()}>"

    def _send_api(self, api_name, api_args, msg_kind):
        def _send():
            self._call_id += 1
            c = PKDict(
                api_name=api_name,
                api_args=api_args,
                call_id=self._call_id,
                msg_kind=msg_kind,
            )
            rv = _Call(self, msg)
            self._pending_calls[rv.call_id] = rv
            self._send_msg(c)
            return rv

        if self._destroyed:
            raise APIDisconnected()
        if self._connection is None:
            raise AssertionError("no connection, must call connect() first")
        if self.client_id is None and api_name != AUTH_API_NAME:
            raise AssertionError("connection not authenticated; await connect()")
        return _send()

    def _send_msg(self, msg):
        self._connection.write_message(_pack_msg(msg), binary=True)


class Session(pykern.quest.Attr):
    """State held on server bound to a client.

    Currently the state is not persisted when the server terminates. This may change.
    """

    ATTR_KEY = "session"

    IS_SINGLETON = True


def server_start(api_classes, attr_classes, http_config, coros=()):
    """Start the `_HTTPServer` in asyncio

    Args:
        api_classes (Iterable): `pykern.quest.API` subclasses to be dispatched
        attr_classes (Iterable): `pykern.quest.Attr` subclasses to create API instance
        http_config (PKDict): `pkasyncio.Loop.http_server` arg
        coros (Iterable): list of coroutines to be passed to `pkasyncio.Loop.run`
    """
    l = pykern.pkasyncio.Loop()
    _HTTPServer(l, api_classes, attr_classes, http_config)
    if coros:
        l.run(*coros)
    l.start()


class _Call:
    """Holds state of an API call

    Attributes:
        api_name (str): name of api
        is_subscription (bool): True if call is subscribed
    """

    def __init__(self, client, msg):
        self.api_name = msg.api_name
        self._call_id = msg.call_id
        self._client = client
        self.is_subscription = msg.msg_kind == _MSG_SUBSCRIBE
        # TODO(robnagler) should there be a maximum?
        self._reply_q = asyncio.Queue()
        self._destroyed = False

    def destroy(self):
        if self._destroyed:
            return
        self._client.unsubscribe_by_call_id(self._call_id)
        if getattr(self._reply_q, "shutdown"):
            self._reply_q.shutdown(immediate=True)
        else:
            self._reply_q.put(None)
        self._call_id = None
        self._client = None
        self._reply_q = None
        self._destroyed = True

    async def reply(self):
        """Get a reply from a regular call or subscription

        Returns:
            PKDict|None: If None, subscription ended normally.
        """
        if self._destroyed:
            raise APIDisconnected()
        try:
            rv = await self.reply_q.get()
        except asyncio.QueueShutDown:
            raise APIDisconnected()
        if self._destroyed:
            raise APIDisconnected()
        self.reply_q.task_done()
        if rv is None:
            self.destroy()
            raise APIDisconnected()
        if rv.api_error:
            self.destroy()
            raise pykern.quest.APIError(rv.api_error)
        if not self.is_subscription:
            self.destroy()
        elif rv.msg_kind == _MSG_UNSUBSCRIBE:
            self.destroy()
            return None
        return rv.api_result

    def reply_put(self, msg):
        if self._destroyed:
            return
        self._reply_q.put_nowait(msg)

    def unsubscribe(self):
        if not self.subscribe:
            raise AssertionError("call is not a subscription")
        if not self._client.call_unsubscribe(self._call_id):
            raise AssertionError("call not registered with client (should not happen)")
        self.destroy()

    def __repr__(self):
        if self._destroyed:
            return f"<self.__class__.__name__ DESTROYED>"
        return f"<self.__class__.__name__ {self.api_name}#{self._call_id}>"


class _HTTPServer:

    def __init__(self, loop, api_classes, attr_classes, http_config):
        def _api_class_funcs():
            for c in api_classes:
                for n, o in inspect.getmembers(c, predicate=inspect.isfunction):
                    yield PKDict(
                        api_class=c,
                        api_func=o,
                        api_func_name=n,
                        is_subscription_api=pykern.quest.is_subscription_api(o),
                    )

        def _api_map():
            rv = PKDict()
            for a in _api_class_funcs():
                n = a.api_func_name
                if not (m := _API_NAME_RE.search(n)):
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

        def _attr_classes():
            rv = list(attr_classes)
            if not any(filter(lambda c: issubclass(c, Session), rv)):
                rv.append(Session)
            return rv

        h = http_config.copy()
        self.loop = loop
        self.api_map = _api_map()
        self.attr_classes = _attr_classes()
        h.uri_map = ((h.api_uri, _ServerHandler, PKDict(server=self)),)
        self.api_uri = h.pkdel("api_uri")
        h.log_function = self._log_end
        self._ws_id = 0
        loop.http_server(h)

    def handle_get(self, handler):
        self._log(handler, "start")

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
        self._subscriptions = PKDict()
        self._destroyed = False
        self.session = Session(qcall=None)
        self.remote_peer = server.loop.remote_peer(handler.request)
        self._log("open")

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        self.handler.close()
        self.handler = None
        self.session = None

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
            if not (c := call.get("call_id")):
                return APICallError("missing call_id")
            if not (k := _msg_kind(call, api)):
                return
            with _quest(call, api) as qcall:
                if k == _MSG_SUBSCRIBE:
                    self._subscriptions[c] = qcall
                try:
                    return await getattr(qcall, api.api_func_name)(api_args)
                except Exception as e:
                    pkdlog("exception={} call={} stack={}", call, e, pkdexc())
                    return APICallError(e)
                finally:
                    if k == _MSG_SUBSCRIBE:
                        self._subscriptions.pkdel(c)
        def _msg_kind(call, api):
            if not (k := call.get("msg_kind")):
                raise APICallError("missing msg_kind")
            if k == _MSG_UNSUBSCRIBE:
                if s := self._subscriptions.get(c):
                    s.destroy()
                else:
                    pkdlog("call_id={} not found in subscriptions={}", c, tuple(self._subscriptions))
                return None
            if k == _MSG_SUBSCRIBE:
                if not api.subscription:
                    raise APICallError(f"non-subscription api={api_name} msg_kind={k}")
            elif k == _MSG_CALL:
                if api.subscription:
                    raise APICallError(f"simple call not for subscription api={api_name}")
            else:
                raise APICallError(f"invalid msg_kind={k}")
            return k

        def _quest(call, api):
            # TODO(robnagler): May need a mutex for shared instance
            k = PKDict({self.session.ATTR_KEY: self.session})
            c = list(_attr_classes())
            if api.subscription:
                a.append(pykern.quest.SubscriptionAttr)

                k[a[-1].ATTR_KEY] = PKDict(_connection=self, _call_id=call.call_id, _api_name=call.api_name)
            return pykern.quest.start(api.api_class, a, **k)

        def _reply(call, api, call_rv):
            try:
                if not isinstance(call_rv, Exception):
                    r = PKDict(api_result=call_rv, api_error=None)
                elif isinstance(call_rv, pykern.quest.APIError):
                    r = PKDict(api_result=None, api_error=str(call_rv))
                else:
                    r = PKDict(api_result=None, api_error=f"unhandled_exception={call_rv}")
                r.call_id = call.get("call_id")
                r.msg_kind = _MSG_UNSUBSCRIBE if api and api.subscription else _MSG_REPLY
                self.handler.write_message(_pack_msg(r), binary=True)
            except Exception as e:
                pkdlog("exception={} call={} stack={}", e, call, pkdexc())
                self.destroy()

        c = None
        a = None
        try:
            c, e = _unpack_msg(msg)
            if e:
                self._log("error", None, "msg unpack error={}", [e])
                self.destroy()
                return None
            self._log("call", c, "api={}", [c.api_name])
            if not (a := _api(c)):
                return
            r = await _call(c, a, c.api_args)
            if r is None:
                return
            if self._destroyed:
                return
            _reply(c, a, r)
            self._log("reply", c)
            c = None
        except Exception as e:
            pkdlog("exception={} call={} stack={}", e, c, pkdexc())
            _reply(c, a, e)

    def subscription_reply(self, call_id, api_result):
        if self._destroyed:
            return
        if call_id not in self._subscriptions:
            pkdlog("call_id={} not found in subscriptions={}", call_id, tuple(self._subscriptions))
            raise APIDisconnected()
        self.handler.write_message(
            _pack_msg(
                PKDict(call_id=call_id, api_result=api_result, msg_kind=_MSG_REPLY)
            ),
            binary=True,
        )


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
        self.pykern_server.handle_get(self)
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
