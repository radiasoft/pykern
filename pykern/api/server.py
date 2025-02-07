"""WebSocket Quest server

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
from pykern.api import util
import asyncio
import importlib
import inspect
import pykern.pkasyncio
import pykern.quest
import pykern.util
import tornado.websocket
import re


_API_NAME_RE = re.compile(rf"^{pykern.quest.API.METHOD_PREFIX}(\w+)")


class Session(pykern.quest.Attr):
    """State held on server bound to a client.

    Currently the state is not persisted when the server terminates. This may change.
    """

    ATTR_KEY = "session"

    IS_SINGLETON = True

    def handle_on_close(self):
        x = list(self.values())
        # Reversed so LIFO
        while x:
            if s := getattr(x.pop(), "session_end", None):
                s()


class Subscription(pykern.quest.Attr):
    """EXPERIMENTAL"""

    ATTR_KEY = "subscription"

    def __init__(self, server_msg):
        super().__init__(None, _server_msg=server_msg)

    def result_put(self, api_result):
        self._server_msg.subscription_result_put(api_result)


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
                    if r.name == util.AUTH_API_NAME:
                        a = True
                    yield r
            if not a:
                for r in _api_class_funcs1(
                    importlib.import_module("pykern.api.auth_api").AuthAPI
                ):
                    yield r

        def _api_class_funcs1(clazz):
            for n, o in inspect.getmembers(clazz, predicate=inspect.isfunction):
                if not (m := _API_NAME_RE.search(n)):
                    continue
                yield PKDict(
                    class_=clazz,
                    func=o,
                    func_name=n,
                    is_subscription=util.is_subscription(o),
                    name=m.group(1),
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

        h = http_config.copy().pksetdefault(uri_map=[])
        self.loop = loop
        self.api_map = _api_map()
        self.attr_classes = attr_classes
        h.uri_map = h.uri_map[:]
        h.uri_map.append((h.api_uri, _ServerHandler, PKDict(server=self)))
        self.api_uri = h.pkdel("api_uri")
        h.log_function = self._log_end
        self._ws_id = 0
        loop.http_server(h)

    def handle_get(self, handler):
        self._log(handler, "ws-get")

    def handle_open(self, handler):
        try:
            self._ws_id += 1
            handler.pykern_api_context.ws_id = self._ws_id
            return _ServerConnection(self, handler, ws_id=self._ws_id)
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())
            self._log(handler, "open-error", "exception={}", [e])
            return None

    def _log(self, handler, which, fmt="", args=None):
        def _add(key, value):
            nonlocal f, a
            if value is not None:
                f += (" " if f else "") + key + "={}"
                a.append(value)

        f = ""
        a = []
        if x := getattr(handler, "pykern_api_context", None):
            _add("error", x.pkdel("error"))
            _add("ws_id", x.get("ws_id"))
        if fmt:
            f = f + " " + fmt
            a.extend(args)
        self.loop.http_log(handler, which, f, a)

    def _log_end(self, handler, *args, **kwargs):
        if isinstance(handler, _ServerHandler):
            self._log(handler, "ws-end")
        else:
            self.loop.http_log(handler)


class _ServerConnection:

    def __init__(self, server, handler, ws_id):
        self.server = server
        self.handler = handler
        self.ws_id = ws_id
        self.pending_msgs = []
        self._destroyed = False
        self.session = Session(None)
        self.remote_peer = server.loop.remote_peer(handler.request)
        self.log("ws-open")

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        x = list(self.pending_msgs)
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
        if self._destroyed:
            return
        m = None
        try:
            m = _ServerMsg(self)
            self.pending_msgs.append(m)
            if not await m.process(msg):
                self.destroy()
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())
            self.log("msg-error", m, "unhandled exception={}", [e])
            self.destroy()
        finally:
            try:
                if not self._destroyed and m:
                    # Maybe have been already destroyed
                    self.pending_msgs.remove(m)
            except Exception as e:
                pkdlog("exception={} stack={}", e, pkdexc())
                pass

    def log(self, which, call=None, fmt="", args=None):
        if fmt:
            fmt = " " + fmt
        pkdlog(
            "{} ip={} ws={} {}" + fmt,
            which,
            self.remote_peer,
            self.ws_id,
            call,
            *(args if args else ()),
        )


class _ServerHandler(tornado.websocket.WebSocketHandler):
    def initialize(self, server):
        # Since part of a global space, need to prefix
        self.pykern_api_server = server
        self.pykern_api_context = PKDict()
        self.pykern_api_connection = None

    async def get(self, *args, **kwargs):
        try:
            self.pykern_api_server.handle_get(self)
            return await super().get(*args, **kwargs)
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())

    async def on_message(self, msg):
        try:
            # WebSocketHandler only allows one on_message at a time
            pykern.pkasyncio.create_task(
                self.pykern_api_connection.handle_on_message(msg)
            )
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())

    def on_close(self):
        try:
            if not (c := self.pykern_api_connection):
                return
            self.pykern_api_connection = None
            c.handle_on_close()
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())

    def open(self):
        try:
            self.pykern_api_connection = self.pykern_api_server.handle_open(self)
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())


class _ServerMsg:

    def __init__(self, connection):
        self._connection = connection
        self._call = None
        self._qcall = None
        self._api = None
        self._destroyed = False

    def destroy(self, unsubscribe=False):
        if self._destroyed:
            return
        self._destroyed = True
        if not (c := self._qcall):
            return
        self._qcall = None
        c.quest_end(in_error=not unsubscribe)

    async def process(self, msg):
        try:
            self._call, e = util.msg_unpack(msg, "server")
            if e:
                self._log("unpack-error", "error={}", [e])
                return False
            if r := self._parse():
                pass
            elif self._call.msg_kind.is_unsubscribe():
                self._unsubscribe(self._call.call_id)
                return True
            elif self._call.msg_kind.is_subscribe():
                r = await self._do_call(Subscription(self))
                if r is not None and not isinstance(r, Exception):
                    r = util.APICallError(
                        f"return type={type(r)} from subscription api must be None"
                    )
            else:
                r = await self._do_call(None)
            if self._destroyed:
                return True
            self._reply(r)
            if isinstance(r, util.APIProtocolError):
                self._log("protocol-error", "exception={}", [e])
                return False
            self._log("end")
            return True
        except Exception as e:
            pkdlog("exception={} {} stack={}", e, self, pkdexc())
            self._log("process-error", "exception={}", [e])
            self._reply(e)
            return False
        finally:
            self.destroy()

    def subscription_result_put(self, api_result):
        if isinstance(api_result, Exception):
            raise util.APICallError(
                "api_result type={type(api_result)} may not be an exception"
            )
        if api_result is None:
            raise util.APICallError("api_result may not be None")
        self._reply(api_result)
        if self._destroyed:
            raise util.APIDisconnected()

    async def _do_call(self, sub):
        try:
            # Let quest.start see the exception
            with self._quest_start(sub) as c:
                try:
                    self._qcall = c
                    return await getattr(c, self._api.func_name)(self._call.api_args)
                finally:
                    self._qcall = None
        except Exception as e:
            pkdlog("exception={} {} stack={}", self, e, pkdexc())
            if not isinstance(e, pykern.util.APIError):
                e = util.APICallError(f"unhandled_exception={e}")
            return e

    def _log(self, which, *args):
        return self._connection.log(which, self, *args)

    def _parse(self):
        def _args():
            if self._call.get("api_args") is None:
                return util.APIProtocolError("missing msg field api_args")
            return None

        def _name():
            if not (n := self._call.get("api_name")):
                return util.APIProtocolError("missing msg field api_name")
            if a := self._connection.server.api_map.get(n):
                self._api = a
                return None
            return util.APINotFound(n)

        def _kind():
            k = self._call.msg_kind
            if k.is_unsubscribe():
                return None
            if r := _name():
                return r
            if k.is_subscribe():
                if not self._api.is_subscription:
                    return util.APIKindError(
                        f"cannot subscribe non-subscription api={self._call.api_name}"
                    )
            elif k.is_call():
                if self._api.is_subscription:
                    return util.APIKindError(
                        f"call_api on subscription api={self._call.api_name}"
                    )
            else:
                raise AssertionError(f"invalid {k} returned from msg_unpack")
            return _args()

        self._log(self._call.msg_kind.name.lower())
        return _kind()

    def _quest_start(self, sub=None):
        a = list(self._connection.server.attr_classes)
        a.append(self._connection.session)
        if sub:
            a.append(sub)
        return pykern.quest.start(self._api.class_, a)

    def _reply(self, call_rv):
        try:
            if call_rv == None:
                if self._call.msg_kind.is_subscribe():
                    r = PKDict(msg_kind=util.MsgKind.UNSUBSCRIBE)
                else:
                    r = PKDict(api_result=None, api_error="missing reply")
            elif not isinstance(call_rv, Exception):
                r = PKDict(api_result=call_rv, api_error=None)
            elif isinstance(call_rv, pykern.util.APIError):
                r = PKDict(
                    api_result=None,
                    api_error=f"{call_rv.__class__.__name__}: {call_rv}",
                )
            else:
                r = PKDict(api_result=None, api_error=f"unhandled_exception={call_rv}")
            r.pksetdefault(msg_kind=util.MsgKind.REPLY)
            r.call_id = self._call.call_id
            self._connection.handler.write_message(util.msg_pack(r), binary=True)
            self._log("reply")
        except Exception as e:
            pkdlog("exception={} {} stack={}", e, self, pkdexc())
            self._log("reply-error")
            self.destroy()

    def __str__(self):
        def _destroyed():
            return " DESTROYED" if self._destroyed else ""

        def _info(c):
            if not c:
                return
            k = c.get("msg_kind")
            i = c.get("call_id")
            if not (k and i):
                return
            rv = f"{k.name.lower()}#{i}"
            if a := c.get("api_name"):
                rv += " " + a
            return f"<{rv}{_destroyed()}>"

        return _info(self._call) or f"<{self.__class__.__name__}{_destroyed()}>"

    def _unsubscribe(self, call_id):
        for m in self._connection.pending_msgs:
            if m._call and m._call.get("call_id") == call_id and m._api:
                if m._api.is_subscription:
                    m.destroy(unsubscribe=True)
