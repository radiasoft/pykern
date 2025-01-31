"""?

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp


_API_NAME_RE = re.compile(rf"^{pykern.quest.API.METHOD_PREFIX}(\w+)")

class Session(pykern.quest.Attr):
    """State held on server bound to a client.

    Currently the state is not persisted when the server terminates. This may change.
    """

    ATTR_KEY = "session"

    IS_SINGLETON = True

    def handle_on_close(self):
        for v in self.values():
            if s := getattr(v, "session_end", None):
                s()

class Subscription(pykern.quest.Attr):
    """EXPERIMENTAL"""

    ATTR_KEY = "subscription"

    def __init__(self, server_msg):
        super().__init__(None, _server_msg=server_msg)

    def result_put(self, api_result):
        self._server_msg.subscription_result(api_result)



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


class _HTTPServer:

    def __init__(self, loop, api_classes, attr_classes, http_config):
        def _api_class_funcs():
            a = False
            for c in api_classes:
                for r in _api_class_funcs1(c):
                    if r.name == pykern.const.AUTH_API_NAME:
                        a = True
                    yield r
            if not a:
                for r in _api_class_funcs1(importlib.importmodule("pykern.api.auth_api").AuthAPI):
                    yield r

        def _api_class_funcs1(clazz)
            for n, o in inspect.getmembers(clazz, predicate=inspect.isfunction):
                if not (m := _API_NAME_RE.search(n)):
                    continue
                yield PKDict(
                    api_class=c,
                    api_func=o,
                    api_func_name=n,
                    api_name = m.group(1)
                    is_subscription_api=pykern.quest.is_subscription_api(o),
                )


        def _api_map():
            rv = PKDict()
            for a in _api_class_funcs():
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
        self._msgs = PKDict()
        self._destroyed = False
        self.session = Session()
        self.remote_peer = server.loop.remote_peer(handler.request)
        self._log("open")

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        x = list(self._msgs.values())
        self._msgs = None
        while x:
            # Reversed so end in opposite order of calls (LIFO)
            x.pop().destroy()
        self.handler.close()
        self.handler = None
        if s := self.session:
            self.session = None
            # Last since it calls out of this module
            s.handle_on_close()

    def handle_on_close(self):
        self.destroy()

    async def handle_on_message(self, msg):
        m = _ServerMsg(self, msg)
        self._msgs.append(m)
        try:
            if not await m.process():
                self.destroy()
        except Exception as e:
            self._log("error", m, "exception={}", [e])
        finally:
            try:
                self._msgs.remove(m)
            except Exception:
                pass

    def unsubscribe(self, call_id):
        for
    def _log(self, which, call=None, fmt="", args=None):
        if fmt:
            fmt = " " + fmt
        pkdlog(
            "{} ip={} ws={}#{}" + fmt,
            which,
            self.remote_peer,
            self.ws_id,
            call,
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
        if not (c := self.pykern_connection):
            return
        self.pykern_connection = None
        c.handle_on_close()

    def open(self):
        self.pykern_connection = self.pykern_server.handle_open(self)


class _ServerMsg:

    _NO_REPLY = object()

    def __init__(self, connection):
        self.connection
        self._call = None
        self._qcall = None
        self._api = None
        self._is_sub = False

    def destroy(self):
        if not (c := self._qcall):
            return
        self._qcall = None
        c.quest_end(in_error=True)

    async def process(self, msg):
        try:
            self._call, e = _unpack_msg(msg)
            if e:
                self._connection.log("error", None, "msg unpack error={}", [e])
                return False
            self._connection.log("call", self)
            if (r := self._parse()):
                if r is not self._NO_REPLY:
                    self._reply(r)
                return True
            if not self._is_sub:
                if (r := await self._do_call()) == self._NO_REPLY:
                    return True
                elif self._call.msg_kind == _MSG_UNSUBSCRIBE:
                    self._connection.unsubscribe(self._call.call_id)
                    return True
            if self._destroyed:
                return
            self._reply(r)
        except Exception as e:
            pkdlog("exception={} call={} stack={}", e, c, pkdexc())
            self._reply(e)

    def subscription_result(self, call_id, api_result):
        self.handler.write_message(
            _pack_msg(
                PKDict(call_id=call_id, api_result=api_result, msg_kind=_MSG_REPLY)
            ),
            binary=True,
        )

    async def _do_call(self, api_args):
        try:
            # Let quest.start see the exception
            with pykern.quest.start(api.api_class) as qcall:
                return await getattr(qcall, api.api_func_name)(api_args)
        except Exception as e:
            pkdlog("exception={} call={} stack={}", call, e, pkdexc())
            return APICallError(e)

    async def _do_sub(self, api_args):
        def _quest(call, api):
            # TODO(robnagler): May need a mutex for shared instance
            k = PKDict({self.session.ATTR_KEY: self.session})
            a = list(self.server.attr_classes)
            if self.is_sub:
                a.append(Subscription(_connection=self))
            return pykern.quest.start(api.api_class, a, **k)


        with _quest() as qcall:
            self._subscriptions[c] = qcall
            try:
                r = await getattr(qcall, api.api_func_name)(api_args)
                if r is None:
                    if not self._is_sub:
                        raise jjj
            except Exception as e:
                pkdlog("exception={} call={} stack={}", call, e, pkdexc())
                return APICallError(e)
            finally:
                if self._is_sub:
                    self._subscriptions.pkdel(c)

    def _parse(self, call):
        def _id(self, call_id):
             if not call_id:
                 return APICallError("missing call_id")
             self._call = call_id
             return None

        def _kind(self, kind):
            if not kind:
                return APICallError("missing msg_kind")
        if k == _MSG_UNSUBSCRIBE:
            if s := self._subscriptions.get(c):
                s.destroy()
            else:
                pkdlog(
                    "call_id={} not found in subscriptions={}",
                    c,
                    tuple(self._subscriptions),
                )
            return self._NO_REPLY
        if k == _MSG_SUBSCRIBE:
            if not api.is_subscription_api:
                return APICallError(f"non-subscription api={self._api.name} msg_kind={k}")
        elif k == _MSG_CALL:
            if api.is_subscription_api:
                return APICallError(
                    f"simple call not for subscription api={self._api.name}"
                )
        else:
            return APICallError(f"invalid msg_kind={k}")
        return k
        def _name(self, api_name):
            if not api_name:
                api_name = "<missing>"
            elif a := self.server.api_map.get(api_name):
                self._api = a
                return None
            return APINotFound(api_name)

        return _name(call.get("api_name")) or _id(call.get("call_id")) or _kind(call.get("msg_kind"))

    def _reply(self, call_rv):
        try:
            if call_rv == None:
                r = PKDict(api_result=None, api_error="missing reply")
            if not isinstance(call_rv, Exception):
                r = PKDict(api_result=call_rv, api_error=None)
            elif isinstance(call_rv, pykern.quest.APIError):
                r = PKDict(api_result=None, api_error=str(call_rv))
            else:
                r = PKDict(
                    api_result=None, api_error=f"unhandled_exception={call_rv}"
                )
            r.call_id = call.get("call_id")
            r.msg_kind = (
                _MSG_UNSUBSCRIBE if self._is_sub else _MSG_REPLY
            )
            self.handler.write_message(_pack_msg(r), binary=True)
            if
            self._connection.log("reply", self)
        except Exception as e:
            pkdlog("exception={} call={} stack={}", e, call, pkdexc())
            self.destroy()

    def __repr__(self):
        rv = "<self.__class__.__name__"
        if self._call:
            for n in ("api_name", "call_id", "msg_kind"):
                if (i := self._call.get(n)):
                    rv += " " + i
        return rv + ">"

    def _unsubscribe(self, call_id):
        if s := self._connection.subscriptions.get(call_id):
            s.destroy()
        else:
            self._log("error", "not found in subscriptions={}", tuple(self._subscriptions))
        return self._NO_REPLY

    def _log(self, which, *args):
        return self._connection.log(which, self, *args)
