"""test pkasyncio

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_URI = "/echo"

_PORT = None


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
