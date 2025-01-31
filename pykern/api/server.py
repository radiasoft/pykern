"""WebSocket Quest server

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import importlib
import pykern.api.util
import pykern.pkasyncio
import pykern.quest
import tornado.websocket



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



def start(api_classes, attr_classes, http_config, coros=()):
    """Start `_Server` in `pkasyncio`

    Args:
        api_classes (Iterable): `pykern.quest.API` subclasses to be dispatched
        attr_classes (Iterable): `pykern.quest.Attr` subclasses to create API instance
        http_config (PKDict): `pkasyncio.Loop.http_server` arg
        coros (Iterable): list of coroutines to be passed to `pkasyncio.Loop.run`
    """
    l = pykern.pkasyncio.Loop()
    _Server(l, api_classes, attr_classes, http_config)
    if coros:
        l.run(*coros)
    l.start()


class _Server:
    def __init__(self, loop, api_classes, attr_classes, http_config):
        def _api_class_funcs():
            a = False
            for c in api_classes:
                for r in _api_class_funcs1(c):
                    if r.name == pykern.api.util.AUTH_API_NAME:
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
                    class_=c,
                    func=o,
                    func_name=n,
                    is_sub=pykern.api.util.is_subscription(o),
                    name = m.group(1)
                )


        def _api_map():
            rv = PKDict()
            for a in _api_class_funcs():
                if a.name in rv:
                    raise AssertionError(
                        "duplicate api={a.name} class={a.class_.__name__}"
                    )
                # don't need to save func
                if not inspect.iscoroutinefunction(a.pkdel("func")):
                    raise AssertionError(
                        "api_func={n} is not async class={a.class_.__name__}"
                    )
                rv[a.name] = a
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
        self.handler = handler
        self.server = server
        self.ws_id = ws_id
        self.pending__msgs = []
        self._destroyed = False
        self.session = Session()
        self.remote_peer = server.loop.remote_peer(handler.request)
        self._log("open")

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        x = list(self.pending_msgs.values())
        self.pending_msgs = []
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
        self.pending_msgs.append(m)
        try:
            if not await m.process():
                self.destroy()
        except Exception as e:
            self._log("error", m, "exception={}", [e])
        finally:
            try:
                self.pending_msgs.remove(m)
            except Exception:
                pass

    def unsubscribe(self, call_id):
            s.destroy()
        else:
            self._log("error", "not found in subscriptions={}", tuple(self._subscriptions))
        return self._NO_REPLY

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
        # Since part of a global space, need to prefix
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
        self._connection = connection
        self._call = None
        self._qcall = None
        self._api = None
        self._is_sub = False

    def destroy(self, unsubscribe=False):
        if not (c := self._qcall):
            return
        self._qcall = None
        c.quest_end(in_error=not unsubscribe)

    async def process(self, msg):
        try:
            self._call, e = pykern.api.util.unpack_msg(msg)
            if e:
                self._log("error", self, "msg unpack error={}", [e])
                return False
            if (r := self._parse()):
                if r is not self._NO_REPLY:
                    self._reply(r)
                return True
            if self._is_sub:
                r = self._do_call(Subscription(self))
                if r is not None:
                    raise APICallError("unexpected reply from subscription api")
                return True
            else:
                r = await self._do_call(None))
            if self._destroyed:
                return True
            self._reply(r)
        except Exception as e:
            pkdlog("exception={} call={} stack={}", e, c, pkdexc())
            self._reply(e)


    def subscription_result(self, call_id, api_result):
        self.handler.write_message(
            pykern.api.util.pack_msg(
                PKDict(call_id=call_id, api_result=api_result, msg_kind=pykern.api.util.MSG_REPLY)
            ),
            binary=True,
        )

    async def _do_call(self, sub):
        try:
            # Let quest.start see the exception
            with self._quest(sub) as c:
                try:
                    self._qcall = c
                    return await getattr(c, self._api.func_name)(self._call.api_args)
                finally:
                    self._qcall = None
        except Exception as e:
            pkdlog("exception={} {} stack={}", self, e, pkdexc())
            return APICallError(e)

    def _log(self, which, *args):
        return self._connection.log(which, self, *args)

    def _parse(self, call):
        def _name():
            if a := self.server.api_map.get(call.api_name):
                self._api = a
                return None
            return APINotFound(call.api_name)

        def _kind():
            if call.msg_kind == pykern.api.util.MSG_UNSUBSCRIBE:
                self._unsubscribe()
                return self._NO_REPLY
            if self.msg_kind == pykern.api.util.MSG_SUBSCRIBE:
                if not self._api.is_sub:
                    return APICallError(f"cannot subscribe non-subscription api={call.api_name}")
                self._is_sub = True
            elif k == pykern.api.util.MSG_CALL:
                if self._api.is_sub:
                    return APICallError(
                        f"call_api on subscription api={call.api_name}"
                    )
            else:
                return APICallError(f"invalid msg_kind={call.msg_kind}")

        for x in "api_name", "call_id", "msg_kind":
            if not call.get(x):
                return APICallError(f"missing {x}")
        # Have enough to register a message
        self._log(call.msg_king, self)
        return _name() or _kind()


    def _quest(self, sub=None):
        a = list(self._connection.server.attr_classes)
        a.append(self._connection.session)
        if sub:
            a.append(sub)
        return pykern.quest.start(self._api.class_, a)


    def _reply(self, call_rv):
        try:
            if call_rv == None:
                r = PKDict(api_result=None, api_error="missing reply")
            if not isinstance(call_rv, Exception):
                r = PKDict(api_result=call_rv, api_error=None)
            elif isinstance(call_rv, pykern.const.APIError):
                r = PKDict(api_result=None, api_error=str(call_rv))
            else:
                r = PKDict(
                    api_result=None, api_error=f"unhandled_exception={call_rv}"
                )
            r.call_id = call.get("call_id")
            r.msg_kind = (
                pykern.api.util.MSG_UNSUBSCRIBE if self._is_sub else pykern.api.util.MSG_REPLY
            )
            self.handler.write_message(pykern.api.util.pack_msg(r), binary=True)
            if
            self._log("reply", self)
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

    def _unsubscribe(self):
        for m in self._connection.pending_msgs:
            if m._call and m._call.get("call_id") == self._call.call_id:
                m.destroy(unsubscribe=True)
