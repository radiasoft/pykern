"""test pkasyncio

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_URI = "/echo"

_PORT = None


def test_action_loop():
    from pykern import pkunit, pkdebug, pkasyncio
    import time

    class _Worker(pkasyncio.ActionLoop):
        def __init__(self, *args, **kwargs):
            self._loop_timeout_secs = 0.1
            self.last_arg = None
            super().__init__(*args, **kwargs)

        def action_callback(self, arg):
            return arg

        def action_end(self, arg):
            return self._LOOP_END

        def action_normal(self, arg):
            self.last_arg = arg
            return None

        def action_raise(self, arg):
            raise RuntimeError(f"action_raise arg=arg")

        def _on_loop_timeout(self):
            self.last_arg = "timeout"
            # Slow down loop so it doesn't timeout again
            time.sleep(0.1)
            return

        def _start(self, *args, **kwargs):
            try:
                super()._start(*args, **kwargs)
            except Exception as e:
                self.last_exception = e
                raise

    _cb_called = False

    def _cb():
        nonlocal _cb_called
        _cb_called = True

    w = _Worker()
    w.action(w.action_normal, "first")
    time.sleep(0.01)
    pkunit.pkeq("first", w.last_arg)
    w.action("callback", _cb)
    time.sleep(0.01)
    pkunit.pkok(_cb_called, "_cb not called")
    w.action("raise", "expect stack trace in log")
    time.sleep(0.01)
    pkunit.pkok(w.last_exception, "exception did not raise to __target")
    w.thread.join(timeout=0.1)
    w = _Worker()
    w.action("end", None)
    w.thread.join(timeout=0.1)
    w = _Worker()
    time.sleep(0.2)
    pkunit.pkeq("timeout", w.last_arg)
    w.destroy()
    w.thread.join(timeout=0.1)


def test_websocket():
    import os, signal, time
    from pykern import pkunit, pkdebug

    global _PORT

    _PORT = pkunit.unbound_localhost_tcp_port(37000, 38000)
    p = os.fork()
    if p == 0:
        try:
            pkdebug.pkdlog("start server")
            _server()
        except Exception as e:
            pkdebug.pkdlog("server exception={} stack={}", e, pkdebug.pkdexc())
        finally:
            os._exit(0)
    try:
        time.sleep(1)
        _client()
    finally:
        os.kill(p, signal.SIGKILL)


def _client():
    from pykern import pkdebug, pkunit
    import asyncio

    async def _all():
        w = await _open()
        pkdebug.pkdlog("open")
        await _send(w, "hello")
        pkdebug.pkdlog("send")
        pkunit.pkeq("hello", await _recv(w))
        pkdebug.pkdlog("recv")

    async def _open():
        from tornado import httpclient, websocket

        return await websocket.websocket_connect(
            httpclient.HTTPRequest(
                url=f"ws://{pkunit.LOCALHOST_IP}:{_PORT}{_URI}",
            ),
            ping_interval=100,
            ping_timeout=1000,
        )

    async def _recv(ws):
        return await ws.read_message()

    async def _send(ws, text):
        await ws.write_message(text)

    asyncio.run(_all())

    # This does not work. The read_message hangs.
    # try:
    #     w = asyncio.run(_open())
    #     pkdebug.pkdlog("open")
    #     asyncio.run(_send(w))
    #     pkdebug.pkdlog("send")
    #     pkdebug.pkdlog("recv={}", asyncio.run(_recv(w)))
    # except Exception as e:
    #     pkdebug.pkdlog("exception={} stack={}", e, pkdebug.pkdexc())


def _server():
    from pykern import pkasyncio, pkdebug, pkunit
    from pykern.pkcollections import PKDict
    from tornado import websocket

    class _Echo(websocket.WebSocketHandler):
        def open(self):
            # just to print something
            pkdebug.pkdlog("remote_ip={}", self.request.remote_ip)

        async def on_message(self, msg):
            import asyncio

            try:
                pkdebug.pkdlog(msg)
                self.write_message(msg)
                pkdebug.pkdlog("send")
            except Exception as e:
                pkdebug.pkdlog("exception {}", e)

    l = pkasyncio.Loop()
    l.http_server(
        PKDict(
            uri_map=((_URI, _Echo),),
            tcp_port=_PORT,
            tcp_ip=pkunit.LOCALHOST_IP,
        )
    )
    l.start()
