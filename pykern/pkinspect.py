# -*- coding: utf-8 -*-
u"""Helper functions for to :mod:`inspect`.

:copyright: Copyright (c) 2015 RadiaSoft, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

# Avoid pykern imports so avoid dependency issues for pkconfig
from pykern import pkcollections
import inspect
import os
import os.path
import re
import sys

#: Used to simplify paths output
_start_dir = ''
try:
    _start_dir = os.getcwd()
except Exception:
    pass


_VALID_IDENTIFIER_RE = re.compile(r'^[a-z_]\w*$', re.IGNORECASE)


class Call(pkcollections.Dict):
    """Saves file:line:name of stack frame and renders as string.

    Args:
        frame_or_log (frame or LogRecord): values to extract

    Attributes:
        filename (str): full path (co_filename)
        lineno (int): line number (f_lineno)
        name (str): function name (co_name)
    """
    def __init__(self, frame_or_log):
        try:
            if hasattr(frame_or_log, 'f_code'):
                super(Call, self).__init__(
                    filename=frame_or_log.f_code.co_filename,
                    lineno=frame_or_log.f_lineno,
                    name=frame_or_log.f_code.co_name,
                    # Only used by caller_module()
                    _module=sys.modules[frame_or_log.f_globals['__name__']],
                )
            else:
                super(Call, self).__init__(
                    filename=frame_or_log.pathname,
                    lineno=frame_or_log.lineno,
                    name=frame_or_log.funcName,
                    _module=None,
                )
        finally:
            if frame_or_log:
                del frame_or_log

    def __str__(self):
        try:
            filename = os.path.relpath(self.filename, _start_dir)
            if len(filename) > len(self.filename):
                # "relpath" always makes relative even when no common components.
                # Take the absolute (shorter) path
                filename = self.filename
            return '{}:{}:{}'.format(filename, self.lineno, self.name)
        except Exception:
            return '<no file>:0:<no func>'


def caller(ignore_modules=None, exclude_first=True):
    """Which file:line:func is calling the caller of this function.

    Will not return the same module as the calling module, that is,
    will iterate until a new module is found. If `ignore_modules` is
    defined, will ignore those modules as well.

    Note: may return __main__ module.

    Will raise exception if calling from __main__

    Args:
        ignore_modules (list): other modules (objects) to exclude [None]
        exclude_first (bool): skip first module found [True]

    Returns:
        pkcollections.Dict: keys: filename, lineno, name, module
    """
    frame = None
    try:
        exclude = [inspect.getmodule(caller)]
        if ignore_modules:
            exclude.extend(ignore_modules)
        exclude_orig_len = len(exclude)
        # Ugly code, because don't want to bind "frame"
        # in a call.
        frame = inspect.currentframe().f_back
        while True:
            m = inspect.getmodule(frame)
            # getmodule doesn't always work for some reason
            if not m:
                m = sys.modules[frame.f_globals['__name__']]
            if m not in exclude:
                if len(exclude) > exclude_orig_len or not exclude_first:
                    return Call(frame)
                # Have to go back two exclusions (this module and our caller)
                exclude.append(m)
            frame = frame.f_back
        # Will raise exception if calling from __main__
    finally:
        # If an exception is thrown, the stack
        # hangs around forever. That's what the del frame
        # is for.
        if frame:
            del frame


def caller_module():
    """Which module is calling the caller of this function.

    Will not return the same module as the calling module, that is,
    will iterate until a new module is found.

    Note: may return __main__ module.

    Will raise exception if calling from __main__

    Returns:
        module: module which is calling module
    """
    return caller()._module


def is_caller_main():
    """Is the caller's calling module __main__?

    Returns:
        bool: True if calling module was called by __main__.
    """
    return caller_module().__name__ == '__main__'


def is_valid_identifier(string):
    """Is this a valid Python identifier?

    Args:
        string (str): what to validate
    Returns:
        bool: True if is valid python ident.
    """
    return bool(_VALID_IDENTIFIER_RE.search(string))


def module_basename(obj):
    """Parse the last part of a module name

    For example, module_basename(pkinspect) is 'pkinspect'.

    Args:
        obj (object): any python object

    Returns:
        str: base part of the module name
    """
    return module_name_split(obj).pop()


def module_name_join(names):
    """Joins names with '.'

    Args:
        names (iterable): list of strings to join

    Returns:
        str: module name
    """
    return '.'.join(names)


def module_name_split(obj):
    """Splits obj's module name on '.'

    Args:
        obj (object): any python object

    Returns:
        str: base part of the module name
    """
    n = inspect.getmodule(obj).__name__
    return n.split('.');


def root_package(obj):
    """Parse the root package in which `obj` is defined.

    For example, root_package(module_basename) is 'pykern'.

    Args:
        obj (object): any python object

    Returns:
        str: root package for the object
    """
    return module_name_split(obj).pop(0)


def submodule_name(obj):
    """Remove the root package in which `obj` is defined.

    For example, root_package(module_basename) is 'pkinspect'.

    Args:
        obj (object): any python object

    Returns:
        str: submodule for the object
    """
    x = module_name_split(obj)
    x.pop(0)
    return module_name_join(x)

def this_module():
    """Module object for caller

    Returns:
        module: module object
    """
    return caller(exclude_first=False)._module
