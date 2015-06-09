# -*- coding: utf-8 -*-
u"""Various extensions to :mod:`inspect`.


:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import inspect


def caller_module():
    """Which module is calling the caller of this function.

    Will not return the same module as the calling module, that is,
    will iterate until a new module is found.

    Note: may return __main__ module.

    Returns:
        module: module which is calling module
    """
    frame = None
    try:
        frame = inspect.currentframe().f_back
        exclude = [inspect.getmodule(frame), caller_module]
        while True:
            frame = frame.f_back
            m = inspect.getmodule(frame)
            if m not in exclude:
                return m
        # Will raise exception if caller is __main__
    finally:
        if frame:
            del frame


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
