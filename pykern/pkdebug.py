# -*- coding: utf-8 -*-
u"""Logging or regex-controlled print statements

We take the view that there are two types of logging: permanent
(`pkdp`) and dynamically controlled (`pkdc`). In both cases, you want
to know where the print statement originated from. Python's `logging`
module supports logging the origin, but it doesn't support user-
defined dynamic filters in the form of a regular expression.

Permanent print statements (`pkdp`) is what people traditionally think
of as "logging". What we don't care about is "logging levels", because
one person's "critical" is another person's "whatever". It's up to
operations people to figure out what's an error worth paying attention
to, and what's not. That's managed by external rule bases, not inside
some library module.

Python's logging module gives programmers too many options and
adds complexity to filters. If you don't attach a handler to
the loggers, you'll never see some messages. Or, if the handler
has `logging.WARN` set, and you really want to see `logging.INFO`
messages, you won't see them.

There are cases when you really don't want to see output. We call
these dynamically controlled print statements. They are typically used
by developers when debugging a new module, and sometimes these lines
get left in the code for a while so that you can get detailed (noisy)
debugging information on production systems.

Dynamically controlled print statements (`pkdc`) would overwhelm logs
so they are off by default and can be filtered by regular expressions
supplied via configuration (including environment variables) or
programmatically via `init`.

Example:

    In a module, you would write::

        from pykern.debug import pkdc, pkdexc, pkdp

        pkdp('user entered: {}', val)
        pkdc('user context: name={name}, id={id}', **user_rec)

    If you do nothing, the first print statement would come
    out always. The second wouldn't come out unless you
    specified a ""control" via the environment variable
    ``$PYKERN_PKDEBUG_CONTROL``:

        PYKERN_PKDEBUG_CONTROL=my_mod python my_prog.py

    Or, if you want a specific conditional print::

        PYKERN_PKDEBUG_CONTROL=my_mod.py:52:

    You can match any text in the line output with a regular expression, which
    is case insensitive.

If `output` is a string, will open the file to write to. The initial
value of output is ``$PYKERN_PKDEBUG_OUTPUT``.

:copyright: Copyright (c) 2014-2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkinspect
import datetime
import inspect
import logging
import os
import re
import six
import sys
import threading
import traceback


#: Maximum number of exceptions thrown before printing stops
MAX_EXCEPTION_COUNT = 5

#: Was control initialized?
_have_control = False

#: Object which does the writing, initialized every time :func:`init` is called.
_printer = None

#: Get IPython InteractiveShell.write()
# See https://github.com/ipython/ipython/blob/master/IPython/core/interactiveshell.py)
_ipython_write = None
try:
    _ipython_write = get_ipython().write_err
except Exception:
    pass

#: Type of a regular expression
_RE_TYPE = type(re.compile(''))

#: How to parse thread names
_THREAD_ID_RE = re.compile(r'Thread-(\d+)', re.IGNORECASE)


def init(**kwargs):
    """May be called to (re)initialize this module.

    `control` is a regular expression, which is used to control the
    output of :func:`pkdc`. Messages from :func:`pkdp` and :func:`pkdc`
    are written to `output`.

    `output` is either an object which implements `write` or a `str`, in which
    case it is opened with :func:`io.open`.

    Args:
        control(str or re.RegexObject): lines matching will be output
        output (str or file): where to write messages [error output]
        redirect_logging (bool): Redirect Python's logging to output [True]
        want_pid_time (bool): display PID and time in messages [False]
    """
    global _printer
    global _have_control
    _printer = _Printer(**kwargs)
    _have_control = _printer.have_control


def pkdc(fmt, *args, **kwargs):
    """Conditional print a message to `output` selectively based on `control`.

    Controlled output that you can leave in your code permanently.

    Args:
        fmt (str): how to :func:`str.format`
        args: what to format
        kwargs: what to format
    """
    # Since calls are left in for product, this check has
    # some value.
    if _have_control:
        _printer._write(fmt, args, kwargs, with_control=True)


def pkdexc():
    """Return last exception and stack as a string

    Must be called from an ``except``. This function removes
    the last two calls from the stack. It joins the traceback
    so you get a complete stack trace.

    Will catch exceptions during the formatting and returns a
    string in all cases.

    Example::

        try:
            something
        except:
            pkdp(pkdexc())

    Returns:
        str: formatted exception and stack trace
    """
    try:
        stack = traceback.format_stack()[:-2]
        e = sys.exc_info()
        stack +=  traceback.format_tb(e[2])
        return ''.join(traceback.format_exception_only(e[0], e[1]) + stack)
    except Exception as e:
        return 'pykern.pkdebug.pkdexc: unable to retrieve exception info'


def pkdlog(fmt_or_arg, *args, **kwargs):
    """Print messages that are intended to be permanent logging.

    See `pkdp` for usage.
    """
    # implementation aliased below
    pass


def pkdp(fmt_or_arg, *args, **kwargs):
    """Print a message to `output` unconditionally, possibly returning its arg

    Use for print statements in your code that you don't intend
    to keep in the system.

    Use `pkdlog` for permanent log messages.

    Args:
        fmt_or_arg (object): how to :func:`str.format`, or object to print
        args: what to format
        kwargs: what to format

    Returns:
        object: Will return fmt_or_arg, if args and kwargs are empty
    """
    if args or kwargs:
        _printer._write(fmt_or_arg, args, kwargs, with_control=False)
    else:
        _printer._write('{}', [fmt_or_arg], {}, with_control=False)
        return fmt_or_arg

# Alias since they are the same
pkdlog = pkdp


def pkdpretty(obj):
    """Return pretty print the object.

    If `obj` is JSON, parse and print it. If it is a regular python
    data structure, pretty print that. Any exceptions are caught,
    and the return value will be `obj`.

    Args:
        obj (object): JSON string or python object

    Returns:
        str: pretty printed string
    """
    try:
        import json
        if isinstance(obj, six.string_types):
            try:
                obj = json.loads(obj)
            except Exception:
                pass
        # try to dump as JSON else dump as Python
        try:
            return json.dumps(
                obj,
                sort_keys=True,
                indent=4,
                separators=(',', ': '),
            ) + '\n'
        except Exception:
            pass
        import pprint
        if pprint.isreadable(obj):
            return pprint.pformat(obj, indent=4) + '\n'
    except Exception:
        pass
    return obj


class _LoggingHandler(logging.Handler):
    """Handler added to root logger.

    """
    def emit(self, record):
        """Emit a log record via _printer

        Writes all `logging.INFO` and above like `pkdp`, that is,
        always. Below `logging.INFO` (i.e. DEBUG) is written like
        `pkdc` using the same matching algorithms by converting
        log records appropriately.
        """
        def msg():
            # Like the default formatter
            return '{}:{}:{}'.format(record.levelname, record.name, record.getMessage())

        def pid_time():
            return (record.process, datetime.datetime.utcfromtimestamp(record.created))

        def prefix():
            return pkinspect.Call(record)

        wc = record.levelno < logging.INFO
        _printer._process(prefix, msg, pid_time, with_control=wc)


class _Printer(object):
    """Internal implementation of :func:`init`. Don't call directly.
    """
    def __init__(self, **kwargs):
        self.too_many_exceptions = False
        self.exception_count = 0
        # Safe values are set here so we can get over initialization errors
        for k in cfg:
            setattr(self, k, cfg[k])
        self.logging_handler = None
        try:
            self.want_pid_time = self._init_want_pid_time(kwargs)
            self.output = self._init_output(kwargs)
            self.redirect_logging = self._init_redirect_logging(kwargs)
            self.control = self._init_control(kwargs)
            self.have_control = bool(self.control)
        except Exception:
            for k in cfg:
                setattr(self, k, cfg[k])
            self._err('initialization failed, reverting values', pkdexc())
        self._logging_install()

    def _err(self, msg, exc):
        """When a logging error occurs.
        """
        self.exception_count += 1
        self._out('pykern.pkdebug error: ' + msg + '\n' + exc)

    def _format(self, fmt, args, kwargs):
        """Format fmt with args & kwargs

        Args:
            fmt (str): how to format
            args (list): what to format
            kwargs (dict): what to format

        Returns:
            str: formatted output
        """
        try:
            return fmt.format(*args, **kwargs)
        except Exception:
            self.exception_count += 1
            return 'invalid format format={} args={} kwargs={}'.format(
                fmt, args, kwargs)

    def _init_control(self, kwargs):
        try:
            if 'control' in kwargs:
                return _cfg_control(kwargs['control'])
        except Exception:
            self._err('control compile error, using safe value', pkdexc())
        return cfg.control


    def _init_output(self, kwargs):
        try:
            if 'output' in kwargs:
                return _cfg_output(kwargs['output'])
        except Exception:
            self._err('output could not be opened, using safe value', pkdexc())
        return cfg.output

    def _init_redirect_logging(self, kwargs):
        return bool(kwargs.get('redirect_logging', cfg.redirect_logging))

    def _init_want_pid_time(self, kwargs):
        return bool(kwargs.get('want_pid_time', cfg.want_pid_time))

    def _logging_install(self):
        """Initialize logging based on redirect_logging
        """
        self.logging_handler = None
        self.logging_prev_handlers = None
        self.logging_prev_level = None
        try:
            if _printer:
                _printer._logging_uninstall()
            if not self.redirect_logging:
                return
            # Optimization: Loggers check the level first before creating
            # the LogRecord, just like pkdc checks _have_control so don't
            # want to create LogRecord unnecessarily
            rl = logging.getLogger()
            self.logging_prev_level = rl.level
            self.logging_prev_handlers = []
            while rl.handlers:
                h = rl.handlers[0]
                rl.removeHandler(h)
                self.logging_prev_handlers.append(h)
            level = logging.DEBUG if self.have_control else logging.INFO
            self.logging_handler = _LoggingHandler(level=level)
            rl.addHandler(self.logging_handler)
            rl.setLevel(level)
        except Exception:
            self._err('unable to install logging handler', pkdexc())

    def _logging_uninstall(self):
        """Remove handler from logging stack and set level to previous
        """
        try:
            if not self.logging_handler:
                return
            rl = logging.getLogger()
            if not self.logging_prev_level is None:
                rl.setLevel(self.logging_prev_level)
            for h in self.logging_prev_handlers:
                rl.addHandler(h)
            rl.removeHandler(self.logging_handler)
        except Exception:
            pass
        self.logging_handler = None
        self.logging_prev_handlers = None
        self.logging_prev_level = None

    def _out(self, msg):
        """Writes msg to output (or error output if not output)

        If running in IPython, then use ``get_ipython().write_err()``
        so that logging comes out in the cell as an error. Otherwise,
        use stderr.

        If an error occurs, output is reset to None.

        Args:
            output (file): where to write
            msg (str): what to write
        """
        try:
            output = self.output
            if not output:
                if _ipython_write:
                    _ipython_write(msg)
                    return
                output = sys.stderr
            output.write(msg)
        except Exception as e:
            self.exception_count += 1
            sys.__stderr__.write('output error: ' + str(e))

    def _pid_time(self, pid, time):
        """Creates pid-time string for output

        Args:
            pid (int): process id
            time (datetime): when did it happen (UTC)

        Returns:
            str: formatted
        """
        if not self.want_pid_time:
            return ''
        try:
            # Force the thread id to a reasonable length so that
            # we don't clutter the logs. It can't be used for anything
            # other than identifying "in the small" log line relationships.
            i = self._thread_id() % 99999
            return '{:%b %d %H:%M:%S} {:5d} {:5d} '.format(time, pid, i)
        except Exception:
            self.exception_count += 1
            self._err('error formatting pid and time', pkdexc())
            return 'Xxx 00 00:00:00 00000.0'

    def _prefix(self, call):
        """Format prefix line from location details

        Args:
            caller: state of call
        Returns:
            str: formatted prefix
        """
        return '{} '.format(call)

    def _process(self, call, message, pid_time_values, with_control):
        """Writes formatted message to output with location prefix.

        If not `with_control`, always writes message to
        :attr:`output`. If `with_control` and whole expression matches
        :attr:`control`, writes message, else nothing is output.

        Args:
            call (func): returns filename, line, funcname
            message (func): returns message with prefix as string
            pid_time_values (func): returns pid and time
            with_control (bool): respect :attr:`control`
        """
        if self.too_many_exceptions or with_control and not self.control:
            return
        try:
            msg = self._prefix(call()) + message()
            if not with_control or self.control.search(msg):
                self._out(self._pid_time(*pid_time_values()) + msg.rstrip() + '\n')
        except Exception:
            self._err('unable to process message', pkdexc())
        finally:
            if self.exception_count >= MAX_EXCEPTION_COUNT:
                self.too_many_exceptions = True

    def _thread_id(self):
        """Returns a number to identify the current thread

        Returns:
            int: some number that uniquely identifies the thread
        """
        t = threading.current_thread()
        n = t.name
        if n == 'MainThread':
            return 0
        m = _THREAD_ID_RE.search(t.name)
        if m:
            return int(m.group(1))
        return t.ident

    def _write(self, fmt, args, kwargs, with_control=False):
        """Provides formatter for message to _process

        Args:
            fmt_or_record (str or LogRecord): how to format
            args (list): what to format
            kwargs (dict): what to format
            with_control (bool): respect :attr:`control`
        """
        def msg():
            try:
                return self._format(fmt, args, kwargs)
            except Exception:
                self.exception_count += 1
                return 'write error: fmt={} args={} kwargs={}'.format(
                    fmt, args, kwargs)

        def pid_time():
            return (os.getpid(), datetime.datetime.utcnow())

        def prefix():
            return pkinspect.Call(inspect.currentframe().f_back.f_back.f_back.f_back)

        self._process(prefix, msg, pid_time, with_control)


@pkconfig.parse_none
def _cfg_control(anything):
    if anything is None:
        return None
    if isinstance(anything, _RE_TYPE):
        return anything
    return re.compile(anything, flags=re.IGNORECASE)


@pkconfig.parse_none
def _cfg_output(anything):
    if anything is None:
        return None
    if hasattr(anything, 'write'):
        return anything
    return open(anything, 'w')


def _z(msg):
    """Useful for debugging this module"""
    with open('/dev/tty', 'w') as f:
        f.write(str(msg) + '\n')


cfg = pkconfig.init(
    control=(None, _cfg_control, 'Pattern to match against pkdc messages'),
    output=(None, _cfg_output, 'Where to write messages either as a "writable" or file name'),
    redirect_logging=(False, bool, "Redirect Python's logging to output"),
    want_pid_time=(False, bool, 'Display pid and time in messages'),
)

if cfg:
    init()
