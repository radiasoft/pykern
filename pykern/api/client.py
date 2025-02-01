"""WebSocket Quest client

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.api import util
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import pykern.util
import tornado.httpclient
import tornado.websocket


class Client:
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
        self._authenticated = False
        self._connection = None
        self._destroyed = False
        self._next_call_id = 1
        self._pending_calls = PKDict()

    async def call_api(self, api_name, api_args):
        """Make a request to the API server

        Args:
            api_name (str): what to call on the server
            api_args (PKDict): passed verbatim to the API on the server.
        Returns:
            str: value of `api_result`.
        Raises:
           pykern.util.APIError: if there was an raise in the API or on a server protocol violation
           Exception: other exceptions that `AsyncHTTPClient.fetch` may raise, e.g. NotFound
        """

        return await self._send_api(api_name, api_args, util.MSG_KIND_CALL).result_get()

    async def connect(self, auth_args=None):
        """Connect to the server

        Args:
            auth_args (PKDict): how to authenticate connection; may be AuthArgs or other PKDict [None]
        Returns:
            AuthReply: status of connection
        """

        async def _auth():
            try:
                await self.call_api(util.AUTH_API_NAME, _auth_args())
                return True
            except Exception as e:
                if self._destroyed:
                    return False
                self.destroy()
                raise

        def _auth_args():
            rv = auth_args
            if rv is None:
                rv = PKDict()
            return rv.pksetdefault(
                token=None, version=util.AUTH_API_VERSION
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
        self._authenticated = await _auth()

    def destroy(self):
        """Must be called"""
        if self._destroyed:
            return
        # Allow functions to call back so _destroyed is still True.
        # Reversed so we unsubscribe in opposite order of subscribe
        for c in reversed(self._pending_calls.values()):
            try:
                c.destroy()
            except Exception as e:
                pkdlog("{} destroy exception={}", c, e)
        # Just in case of exceptions above
        self._pending_calls = None
        self._destroyed = True
        if self._connection:
            self._connection.close()
            self._connection = None

    async def subscribe_api(self, api_name, api_args):
        """Subscribe to api_name from API server

        Args:
            api_name (str): what to call on the server
            api_args (PKDict): passed verbatim to the API on the server.
        Returns:
            _Call: to get replies or unsubscribe
        """

        return self._send_api(api_name, api_args, util.MSG_KIND_SUBSCRIBE)

    def finish_call_id(self, call_id, unsubscribe):
        """Not a public interface"""
        if self._destroyed:
            return
        self._pending_calls.pkdel(call_id)
        if unsubscribe:
            # Header always has api_name
            self._send_msg(PKDict(call_id=call_id, msg_kind=util.MSG_KIND_UNSUBSCRIBE))

    async def __aenter__(self):
        await self.connect()
        if self._destroyed:
            raise util.APIDisconnected()
        return self

    async def __aexit__(self, *args, **kwargs):
        self.destroy()
        return False

    async def _read_loop(self):
        def _unpack(msg):
            r, e = util.msg_unpack(msg)
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
                c.reply_put(r)
                if not c.is_subscription:
                    self._pending_calls.pkdel(r.call_id)
                # Clear all state before next await
                c = m = r = None
        except Exception as e:
            pkdlog("exception={} reply={} stack={}", e, r, pkdexc())
        try:
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
            c = PKDict(
                api_name=api_name,
                api_args=api_args,
                call_id=self._next_call_id,
                msg_kind=msg_kind,
            )
            self._next_call_id += 1
            rv = _Call(self, c)
            self._pending_calls[c.call_id] = rv
            self._send_msg(c)
            return rv

        if self._destroyed:
            raise util.APIDisconnected()
        if self._connection is None:
            raise AssertionError("no connection, must call connect() first")
        if not self._authenticated and api_name != util.AUTH_API_NAME:
            raise AssertionError("connection not authenticated; wait for connect() to return")
        return _send()

    def _send_msg(self, msg):
        # Might not have connection in finish_call_id
        if self._connection:
            self._connection.write_message(util.msg_pack(msg), binary=True)


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
        self.is_subscription = msg.msg_kind == util.MSG_KIND_SUBSCRIBE
        # TODO(robnagler) should there be a maximum?
        self._reply_q = asyncio.Queue()
        self._destroyed = False

    def destroy(self, unsubscribe=False):
        if self._destroyed:
            return
        self._client.finish_call_id(self._call_id, unsubscribe=unsubscribe and self.is_subscription)
        self._destroyed = True
        if x := getattr(self._reply_q, "shutdown", None):
            x.shutdown(immediate=True)
        else:
            # Inferior to shutdown, but necessary pre-Python 3.13
            self._reply_q.put(None)
        self._call_id = None
        self._client = None
        self._reply_q = None

    def reply_put(self, msg):
        if self._destroyed:
            return
        self._reply_q.put_nowait(msg)

    async def result_get(self):
        """Get the next result from a subscription.

        Used internally to this module to get a result from a one-time call.

        Returns:
            PKDict|None: If None, subscription ended normally.
        """
        if self._destroyed:
            raise util.APIDisconnected()
        d = True
        try:
            try:
                rv = await self._reply_q.get()
            except Exception as e:
                if (x := getattr(asyncio, "QueueShutDown", None)) and isinstance(e, x):
                    raise util.APIDisconnected()
                raise
            if self._destroyed:
                raise util.APIDisconnected()
            self._reply_q.task_done()
            if rv is None:
                raise util.APIDisconnected()
            if rv.msg_kind == util.MSG_KIND_UNSUBSCRIBE:
                return None
            if rv.api_error:
                raise pykern.util.APIError(rv.api_error)
            d = not self.is_subscription
            return rv.api_result
        finally:
            if d:
                self.destroy()

    def unsubscribe(self):
        """End call and notify server

        Object is not usable after this call.
        """
        if self._destroyed:
            # allows unsubscribe to be idempotent
            return
        if not self.subscription:
            raise AssertionError("call is not a subscription")
        self.destroy()

    def __repr__(self):
        if self._destroyed:
            return f"<self.__class__.__name__ DESTROYED>"
        return f"<self.__class__.__name__ {self.api_name}#{self._call_id}>"
