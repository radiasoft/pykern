"""Wrapper on asyncio and tornado

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern.pkdebug import pkdlog
import asyncio
import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web


async def sleep(secs):
    await asyncio.sleep(secs)


def tornado_http_server(uris, cfg):
    """Instantiate a tornado web server

    Under the covers Tornado uses the asyncio event loop so asyncio methods
    can be mixed with Tornado methods.

    To start the server you can call the returned function. Or you can use any of the
    asyncio methods that run the event loop (ex asyncio.run).

    Using asyncio methods (ex asyncio.run()) is prefered over Tornado methods (ex.
    tornado.ioloop.IOLoop.current().start()) to reduce leaking out details of Tornado.

    Args:
        uris (tuple): tuple of (uri, handler_class) tuples
        cfg (PKDict): object with ip and port fields
    Returns:
        function: a blocking call that runs the server
    """
    # TODO(e-carlin): pull in the one in job_supervisor.py
    tornado.httpserver.HTTPServer(
        tornado.web.Application(
            uris,
            debug=pkconfig.channel_in("dev"),
        ),
        xheaders=True,
    ).listen(cfg.port, cfg.ip)
    return tornado.ioloop.IOLoop.current().start
