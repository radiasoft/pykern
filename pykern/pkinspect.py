# -*- coding: utf-8 -*-
u"""Various extensions to :mod:`inspect`.


:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import inspect
import sys

from pykern.pkdebug import pkdc, pkdi, pkdp

def caller_module():
    """Which module is calling the caller of this function.

    Will not return the same module as the calling module, that is,
    will iterate until a new module is found.

    Note: may return __main__ module.

    Will raise exception if calling from __main__

    Returns:
        module: module which is calling module
    """
    frame = None
    try:
        # Ugly code, because don't want to bind "frame"
        # in a call. If an exception is thrown, the stack
        # hangs around forever. That's what the del frame
        # is for.
        frame = inspect.currentframe().f_back
        exclude = [inspect.getmodule(caller_module)]
        while True:
            m = inspect.getmodule(frame)
            # getmodule doesn't always work for some reason
            if not m:
                m = sys.modules[frame.f_globals['__name__']]
            if m not in exclude:
                if len(exclude) > 1:
                    # Caller's caller
                    return m
                # Have to go back two exclusions (this module
                # and our caller)
                exclude.append(m)
            frame = frame.f_back
        # Will raise exception if calling from __main__
    finally:
        if frame:
            del frame


def is_caller_main():
    """Is the caller's calling module __main__?

    Returns:
        bool: True if calling module was called by __main__.
    """
    print(caller_module().__name__ + 'xx')
    return caller_module().__name__ == '__main__'


def module_basename(obj):
    """Parse the last part of a module name

    For example, module_basename(pkinspect) is 'pkinspect'.

    Args:
        obj (object): any python object

    Returns:
        str: base part of the module name
    """
    return _module_split(obj).pop()


def root_package(obj):
    """Parse the root package in which `obj` is defined.

    For example, root_package(module_basename) is 'pykern'.

    Args:
        obj (object): any python object

    Returns:
        str: root package for the object
    """
    return _module_split(obj).pop(0)


def _module_split(obj):
    """Splits the calling module's name"""
    n = inspect.getmodule(obj).__name__
    return n.split('.');
