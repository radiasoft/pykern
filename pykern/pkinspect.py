# -*- coding: utf-8 -*-
u"""Helper functions for to :mod:`inspect`.

:copyright: Copyright (c) 2015 RadiaSoft, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

# Avoid pykern imports so avoid dependency issues for pkconfig
import inspect
import sys


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
    return caller_module().__name__ == '__main__'


def module_basename(obj):
    """Parse the last part of a module name

    For example, module_basename(pkinspect) is 'pkinspect'.

    Args:
        obj (object): any python object

    Returns:
        str: base part of the module name
    """
    return module_name_split(obj).pop()


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
    return '.'.join(x)
