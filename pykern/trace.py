# -*- coding: utf-8 -*-
"""Real-time debug logging controlled by regular expressions.

Example:
    In a module, you would write::

        from pykern.trace import trace

        trace('user entered: {}', val)

    Or::

        trace('user context: name={name}, id={id}', **user_rec)

    Running the program, to get a module to output, you'd set $PYKERN_TRACE::

        PYKERN_TRACE=my_mod python my_prog.py

    Or, if you want a specific tracepoint::

        PYKERN_TRACE=my_mod.py:52:

    You can match any text in the line output with a regular expression, which
    is case insensitive.

:copyright: Copyright (c) 2014-2015 Bivio Software, Inc.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""
from __future__ import absolute_import
from __future__ import print_function

import inspect
import os
import re
import sys

#: Maximum number of exceptions thrown before trace printing stops
MAX_EXCEPTION_COUNT = 5

#: Printer object initialized every time
_printer = None

#: Used to simplify paths output
_start_dir = ''
try:
    _start_dir = os.getcwd()
except Exception:
    pass


def trace(fmt, *args, **kwargs):
    """Print a message to trace log based on caller context and current
    value of $PYKERN_TRACE regular expression.

    Args:
        fmt (str): how to :func:`str.format`
        *args: what to format
        **kwargs: what to format
    """
    if _printer:
        _printer._write_maybe(fmt, args, kwargs)


def init(control=None, output=None):
    """May be called to (re)initialize this module.

    To turn of tracing set ``control`` to None.

    Args:
        control(str or re.RegexObject): trace lines matching will be output.
        output (file): where to write trace messages (default: sys.stderr)
    """
    global _printer
    _printer = None
    if not control:
        return
    try:
        _printer = _Printer(control, output)
    except Exception as e:
        err = None
        try:
            err = '"{}": pykern.trace.init failed: {}'.format(control, e)
            _write(output, err)
        except Exception:
            if not err:
                err = 'pykern.trace.init failed'
            _write(None, err)


class _Printer(object):
    """Implements trace output. Call :func:`init` to initialize.
    """
    def __init__(self, control, output):
        self.control = re.compile(control, flags=re.IGNORECASE)
        self.output = output
        self.exception_count = 0

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
            return 'invalid trace format={} args={} kwargs={}'.format(
                fmt, args, kwargs)

    def _prefix(self):
        """Format prefix from current stack frame

        Returns:
            str: description of caller
        """
        f = None
        try:
            f = inspect.currentframe().f_back.f_back.f_back
            filename = os.path.relpath(f.f_code.co_filename, _start_dir)
            line = f.f_lineno
            name = f.f_code.co_name
            return '{}:{}:{} '.format(filename, line, name)
        except Exception:
            self.exception_count += 1
            return ''
        finally:
            # Avoid cycles in the stack
            del f

    def _write_maybe(self, fmt, args, kwargs):
        """Implements :func:`trace`. Writes formatted msg if matches control.

        Args:
            fmt (str): how to format
            args (list): what to format
            kwargs (dict): what to format
        """
        if not self.control:
            return
        try:
            msg = self._prefix() + self._format(fmt, args, kwargs)
            if self.control.search(msg):
                _write(self.output, msg + '\n')
        except Exception:
            self.exception_count += 1
            try:
                _write(
                    self.output,
                    'trace write error: fmt={} args={} kwargs={}'.format(
                        fmt, args, kwargs),
                )
            except Exception:
                self.exception_count = MAX_EXCEPTION_COUNT
        finally:
            if self.exception_count >= MAX_EXCEPTION_COUNT:
                self.control = None


def _write(output, msg):
    """Writes msg to output (or sys.stderr if not output)

    Args:
        output (file): where to write
        msg (str): what to write
    """
    if not output:
        output = sys.stderr
    output.write(msg)


init(os.getenv('PYKERN_TRACE'))
