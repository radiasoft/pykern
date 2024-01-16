"""test pkasyncio

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_LOCALHOST = "127.0.0.1"
_URI = "/echo"

_PORT = None


def test_websocket():
    import os, signal, time

    global _PORT

    _PORT = _port()
    p = os.fork()
    if p == 0:
        try:
            _server()
        finally:
            os._exit(0)
    try:
        time.sleep(1)
        _client()
    finally:
        os.kill(p, signal.SIGKILL)


def _client():
    from pykern import pkdebug
    import asyncio

    async def _all():
        w = await _open()
        pkdebug.pkdlog("open")
        await _send(w)
        pkdebug.pkdlog("send")
        pkdebug.pkdlog("recv={}", await _recv(w))
        return

    async def _open():
        from tornado import httpclient, websocket

        return await websocket.websocket_connect(
            httpclient.HTTPRequest(
                url=f"ws://{_LOCALHOST}:{_PORT}{_URI}",
            ),
            ping_interval=100,
            ping_timeout=1000,
        )

    async def _recv(ws):
        return await ws.read_message()

    async def _send(ws):
        await ws.write_message("hello")

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


def _port():
    import random

    def _check_port(port):
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((_LOCALHOST, int(port)))
        return port

    for p in random.sample(range(37000, 37100), 10):
        try:
            return _check_port(p)
        except Exception:
            pass
    raise AssertionError(
        f"ip={_LOCALHOST} unable to bind to port in range={37000-37100}"
    )


def _server():
    from pykern import pkasyncio, pkdebug
    from pykern.pkcollections import PKDict
    from tornado import websocket

    class _Echo(websocket.WebSocketHandler):
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
            tcp_ip=_LOCALHOST,
        )
    )
    l.start()
