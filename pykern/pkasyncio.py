"""Utilities to support `asyncio` and to simplify starting `tornado`.

See also `pkykern.api` which provides a higher level mechanism for
websocket clients and servers.

:copyright: Copyright (c) 2022-2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""

from pykern import pkconfig
from pykern import pkconst
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc
import asyncio
import inspect
import queue
import re
import threading
import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web

_cfg = None

_background_tasks = set()


class ActionLoop:
    """Processes actions in a loop fed by a `queue.Queue` running in
    `threading.Thread`.

    Useful to avoid blocking main loop in `asyncio` for compute or
    blocking libraries that do not support `asyncio`.

    Calling `action` is `asyncio` and thread safe. If the action
    methods transfer data back to the `asyncio` loop, use
    `asyncio.call_soon_threadsafe` on the appropriate `asyncio`
    loop. See discussion in `action`.

    """

    #: sentinel to end loop in `_start`
    _LOOP_END = object()

    #: default is to wait forever for next action; subclasses may override
    _loop_timeout_secs = 0

    def __init__(self):
        # All these attributes must exist even after destroy()
        self.destroyed = False
        self.__lock = threading.Lock()
        self.__actions = queue.Queue()
        # You can join the thread to block another (e.g. main) thread from exiting
        # until an ActionLoop is done.
        self.thread = threading.Thread(target=self.__target, daemon=True)
        self.__get_args = PKDict()
        if self._loop_timeout_secs > 0:
            if not hasattr(self, "_on_loop_timeout"):
                raise AssertionError(
                    f"_loop_timeout_secs={self._loop_timeout_secs} and not _on_loop_timeout"
                )
            self.__get_args.timeout = self._loop_timeout_secs
        self.thread.start()

    def action(self, method, arg):
        """Queue ``method`` to be called in loop thread.

        Actions are methods that (by convention) begin with
        ``action_`` and are called sequentially inside `_start`. A
        lock is used to prevent `destroy` being called during the
        action and serializing activities within a single action.

        Actions return ``None`` to continue on to the next
        action. `_LOOP_END` should be returned to terminate `_start`
        (the loop) in which case no further actions are
        performed. Actions can return a callable that will be called
        inside the loop and outside the lock. These returned callables
        are known as external callbacks, that is, functions that may
        do anything so holding the lock could be problematic.

        The lock is managed by this class and subclasses should not
        need locking. Resources should be "handed off" to actions via
        `arg` passed to `method`, which can "return" the resource by
        returning a callback that gets called outside the lock but
        within the single thread of control that an `ActionLoop`
        represents. Read the `Go Channels Tutoral
        <https://go101.org/article/channel.html>`_ for more
        information about using queues for resource sharing without
        locks.

        Args:
            method (callable or str): a method or a name used to find a method: ``self.action_<method>``
            arg (object): passed verbatim to ``method``
        """
        self.__actions.put_nowait(
            (
                (
                    getattr(self, f"action_{method}")
                    if isinstance(method, str)
                    else method
                ),
                arg,
            ),
        )

    def destroy(self):
        """Stops thread and calls subclass `_destroy`

        THREADING: subclasses should not call destroy directly. They should
        return `_LOOP_END` instead. External callbacks may call destroy, because
        _ActionLoop does not hold lock during external callbacks.
        """
        try:
            with self.__lock:
                if self.destroyed:
                    return
                self.destroyed = True
                self.__actions.put_nowait((None, None))
                self._destroy()
        except Exception as e:
            pkdlog("error={} {} stack={}", e, self, pkdexc(simplify=True))

    def _dispatch_action(self, method, arg):
        """Calls method with arg.

        Subclasses may re-implement. This function will remain a
        very simple wrapper for ``return method(arg)``.

        This function is called inside the lock.

        Args:
            method (callable): to be called
            arg (object): to be passed
        Returns:
            object: result of method
        """
        return method(arg)

    def _dispatch_callback(self, callback):
        """Calls callback.

        Subclasses may re-implement. This method will remain a very
        simple wrapper for ``callback()``.

        This function is called outside the lock.

        Args:
            callback (callable): to be called
        """
        callback()

    def _on_loop_timeout(self):
        """Called when a loop timeout occurs.

        Subclasses must implement this *if* they set `_loop_timeout_secs`.
        """
        # `__init__` prevents this from happening, but good to document.
        raise NotImplementedError("ActionLoop._on_loop_timeout")

    def __repr__(self):
        def _destroyed():
            return " DESTROYED" if self.destroyed else ""

        return f"<{self.__class__.__name__}{_destroyed()} self._repr()>"

    def _start(self):
        """Loops over actions and exits on `_LOOP_END` or on unhandled exception.

        See `action` for details of what actions are.

        Called by `__target`. Subclasses may override this method to setup the loop.
        """
        while True:
            with self.__lock:
                if self.destroyed:
                    return
            try:
                m, a = self.__actions.get(**self.__get_args)
                self.__actions.task_done()
            except queue.Empty:
                m, a = self._on_loop_timeout(), None
            with self.__lock:
                if self.destroyed:
                    return
                # Do not need to check m, because only invalid when destroyed is True
                if (m := self._dispatch_action(m, a)) is self._LOOP_END:
                    return
                # Will be true if destroy called inside action (m)
                if self.destroyed:
                    return
            # Action returned an external callback, which must occur outside lock
            if m:
                self._dispatch_callback(m)

    def __target(self):
        """Thread's target function"""
        try:
            self._start()
        except Exception as e:
            pkdlog("error={} {} stack={}", e, self, pkdexc(simplify=True))
        finally:
            self.destroy()


class Loop:
    """HTTP Server loop"""

    def __init__(self):
        _init()
        self._coroutines = []
        self.__http_server = False

    def http_server(self, http_cfg):
        """Instantiate a tornado web server

        Under the covers Tornado uses the asyncio event loop so asyncio methods
        can be mixed with Tornado methods.

        Using asyncio methods, e.g. `asyncio.run`, is preferred over
        Tornado methods, e.g.  `tornado.ioloop.IOLoop.current` to
        reduce dependency on Tornado. Using this module should allow
        the code to be portable to other http server frameworks.

        ``http_config.uri_map`` maps URI expressions to classes, which
        is passed directly to `tornado.web.Application`.

        Args:
            http_cfg (PKDict): quest_start, uri_map, debug, tcp_ip, tcp_port,

        """

        async def _do():
            # TODO(e-carlin): pull in the one in job_supervisor.py
            p = http_cfg.get("tcp_port", _cfg.server_port)
            i = http_cfg.get("tcp_ip", _cfg.server_ip)
            tornado.httpserver.HTTPServer(
                tornado.web.Application(
                    http_cfg.uri_map,
                    debug=http_cfg.get("debug", _cfg.debug),
                    log_function=http_cfg.get("log_function", self.http_log),
                ),
                xheaders=True,
            ).listen(p, i)
            pkdlog("name={} ip={} port={}", http_cfg.get("name"), i, p)
            await asyncio.Event().wait()

        if self.__http_server:
            raise AssertionError("http_server may only be called once")
        self.__http_server = True
        self.run(_do())

    def http_log(self, handler, which="end", fmt="", args=None):
        r = handler.request
        f = "{} ip={} uri={}"
        a = [which, self.remote_peer(r), r.uri]
        if fmt:
            f += " " + fmt
            a += args
        if which == "start":
            f += " proto={} {} ref={} ua={}"
            a += [
                r.method,
                r.version,
                r.headers.get("Referer") or "",
                r.headers.get("User-Agent") or "",
            ]
        elif which == "end":
            f += " status={} ms={:.2f}"
            a += [
                handler.get_status(),
                r.request_time() * 1000.0,
            ]
        pkdlog(f, *a)

    def remote_peer(self, request):
        # https://github.com/tornadoweb/tornado/issues/2967#issuecomment-757370594
        # implementation may change; Code in tornado.httputil check connection.
        if c := request.connection:
            # socket is not set on stream for websockets.
            if getattr(c, "stream", None) and (s := getattr(c.stream, "socket", None)):
                return "{}:{}".format(*s.getpeername())
        i = request.headers.get("proxy-for", request.remote_ip)
        return f"{i}:0"

    def run(self, *coros):
        for c in coros:
            if not inspect.iscoroutine(c):
                raise AssertionError(f"must be a coroutine arg={c} coros={coros}")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self._coroutines.extend(coros)
            return
        raise AssertionError("cannot call after event loop has started")

    def start(self):
        async def _do():
            await asyncio.gather(*self._coroutines)

        if not self._coroutines:
            raise AssertionError("no coroutines registered; must have at least one")
        asyncio.run(_do(), debug=_cfg.debug)


@pkconfig.parse_none
def cfg_ip(value):
    if value is None:
        return "0.0.0.0" if pkconfig.in_dev_mode() else pkconst.LOCALHOST_IP
    return value


def cfg_port(value):
    v = int(value)
    l = 3000
    u = 32767
    if not l <= v <= u:
        pkconfig.raise_error(f"value must be from {l} to {u}")
    return v


def create_task(coro):
    """Create a task

    Keeps a global reference to the task so to avoid the garbage
    collector running before the task is run.
    https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
    """
    t = asyncio.create_task(coro)
    _background_tasks.add(t)
    t.add_done_callback(_background_tasks.discard)
    return t


async def sleep(secs):
    await asyncio.sleep(secs)


def _init():
    global _cfg
    if _cfg:
        return
    _cfg = pkconfig.init(
        debug=(pkconfig.in_dev_mode(), bool, "enable debugging for asyncio"),
        server_ip=(
            None,
            cfg_ip,
            "ip to listen on",
        ),
        server_port=("9001", cfg_port, "port to listen on"),
        verify_tls=(
            not pkconfig.channel_in("dev"),
            bool,
            "validate TLS certificates on requests; for self-signed set to False",
        ),
    )
