# -*- coding: utf-8 -*-
u"""Temporary and regex-controlled permanent print statements.

Did you ever see output from your application, and you didn't know
which module generated it? Do you put the function, line, and/or module
in each an every print statement so you know where it is being printed
from? Do you have a bug where you would like to see interesting output
on production, and have to edit the code to insert those messages?

This module helps with these problems. The output of this module is always
prefixed with a module and line number so you can always find where it is
being printed from and easily remove if one happens to slip into productions.

You can leave permanent print statements in your code that can be controlled
conditionally by a regular expression supplied by configuration. This way
you can turn on debugging statements in individual modules or on a specific
line or function.

Example:
    In a module, you would write::

        from pykern.debug import *

        pkdc('user entered: {}', val)

    Or::

        pkdc('user context: name={name}, id={id}', **user_rec)

    Running the program, to get a module to output,
    you'd set ``$PYKERN_DEBUG_CONTROL``::

        PYKERN_DEBUG_CONTROL=my_mod python my_prog.py

    Or, if you want a specific conditional print::

        PYKERN_DEBUG_CONTROL=my_mod.py:52:

    You can match any text in the line output with a regular expression, which
    is case insensitive.

If `output` is a string, will open the file to write to. The initial
value of output is ``$PYKERN_DEBUG_OUTPUT``.

:copyright: Copyright (c) 2014-2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import inspect
import os
import re
import sys

#: For convenience, we want to import this module unqualified (``*``)
__all__ = [
    'pkdc', 'pkdp', 'pkdi',
    # TODO(robnagler) deprecated
    'ipr', 'cpr', 'dpr',
]

#: Maximum number of exceptions thrown before printing stops
MAX_EXCEPTION_COUNT = 5

#: Was control initialized?
_have_control = False

#: Object which does the writing, initialized every time :func:`init` is called.
_printer = None

#: Used to simplify paths output
_start_dir = ''
try:
    _start_dir = os.getcwd()
except Exception:
    pass


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
# TODO(robnagler) remove after all apps updated
cpr = pkdc


def pkdi(arg):
    """Inline print a value to `output` unconditionally and return arg

    Used when you want to see a value in the middle of an expression.

    Args:
        arg (object): object to print

    Returns:
        object: returns `arg` unmodified
    """
    _printer._write('{}', [arg], {}, with_control=False)
    return arg
# TODO(robnagler) remove after all apps updated
ipr = pkdi


def pkdp(fmt, *args, **kwargs):
    """Print a message to `output` unconditionally.

    Use this for temporary print statements in your code.

    Args:
        fmt (str): how to :func:`str.format`
        args: what to format
        kwargs: what to format
    """
    _printer._write(fmt, args, kwargs, with_control=False)
# TODO(robnagler) remove after all apps updated
dpr = pkdp


def init(control=None, output=None):
    """May be called to (re)initialize this module.

    `control` is a regular expression, which is used to control the
    output of :func:`pkdc`. Messages from :func:`pkdp`, :func:`pkdi`, and :func:`pkdc`
    are written to `output`.

    `output` is either an object which implements `write` or a `str`, in which
    case it is opened with :func:`io.open`.

    Args:
        control(str or re.RegexObject): lines matching will be output.
        output (str or file): where to write messages (default: sys.stderr)
    """
    global _printer
    global _have_control
    _printer = _Printer(control, output)
    _have_control = bool(_printer.control)


class _Printer(object):
    """Implements output. Call :func:`init` to initialize.
    """
    def __init__(self, control, output):
        self.too_many_exceptions = False
        self.exception_count = 0
        self.output = self._init_output(output)
        self.control = self._init_control(control)

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

    def _init_control(self, control):
        try:
            if control:
                return re.compile(control, flags=re.IGNORECASE)
            return None
        except Exception as e:
            err = None
            try:
                err = '"{}": pkdebug.init: control compile error: {}\n'.format(
                    control, e)
            except Exception:
                # Probably shouldn't happen, but just in case
                err = 'pkdebug.init: control compile failed\n'
                _out(self.output, err)
        try:
            _out(self.output, err)
        except Exception as e:
            self.output = None
            _out(None, err + ' AND output write failed, using stderr\n')

    def _init_output(self, output):
        try:
            if not output:
                return None
            if hasattr(output, 'write'):
                return output
            return open(output, 'w')
        except Exception as e:
            _out(
                None,
                '{}: output could not be opened, using default\n'.format(output))
            return None

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

    def _write(self, fmt, args, kwargs, with_control=False):
        """Writes formatted message to output with location prefix.

        If not `with_control`, always writes message to
        :attr:`output`. If `with_control` and whole expression matches
        :attr:`control`, writes message, else nothing is output.

        Args:
            fmt (str): how to format
            args (list): what to format
            kwargs (dict): what to format
            with_control (bool): respect :attr:`control`
        """
        if self.too_many_exceptions or with_control and not self.control:
            return
        try:
            msg = self._prefix() + self._format(fmt, args, kwargs)
            if not with_control or self.control.search(msg):
                _out(self.output, msg + '\n')
        except Exception:
            self.exception_count += 1
            try:
                _out(
                    self.output,
                    'debug write error: fmt={} args={} kwargs={}'.format(
                        fmt, args, kwargs),
                )
            except Exception:
                self.exception_count = MAX_EXCEPTION_COUNT
        finally:
            if self.exception_count >= MAX_EXCEPTION_COUNT:
                self.too_many_exceptions = True


def _init_from_environ():
    """Calls :func:`init` with ``$PYKERN_DEBUG_*`` environment variables
    """
    init(os.getenv('PYKERN_DEBUG_CONTROL'), os.getenv('PYKERN_DEBUG_OUTPUT'))

def _out(output, msg):
    """Writes msg to output (or sys.stderr if not output)

    Args:
        output (file): where to write
        msg (str): what to write
    """
    if not output:
        output = sys.stderr
    output.write(msg)


def _z(msg):
    """Useful for debugging this module"""
    with open('/dev/tty', 'w') as f:
        f.write(str(msg) + '\n')

_init_from_environ()
