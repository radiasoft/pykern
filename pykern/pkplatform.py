# -*- coding: utf-8 -*-
u"""Wrapper for Python's :mod:`platform` to provide cleaner programmatic
control of system features.

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import platform
import re
import sys


def is_darwin():
    """All flavors of Mac (OS X)

    Returns:
        bool: True if :attr:`sys.platform` is Mac.
    """
    return sys.platform.startswith('darwin')


def is_linux():
    """All flavors of linux

    Returns:
        bool: True if :attr:`sys.platform` is Linux.
    """
    return sys.platform.startswith('linux')


def is_unix():
    """All flavors of Unix. Currently, it's darwin, linux, cygwin, freebsd,
    netbsd, sunos, solaris, unixware, irix, aix, and next.

    Returns:
        bool: True if :attr:`sys.platform` is a pure Unix system (e.g. not beos)
    """
    return re.match(r'aix|cygwin|darwin|freebsd|irix|linux|netbsd|solaris|sunos|unix', sys.platform) is not None


def is_windows():
    """All flavors of Windows (32, 64, cygwin, etc.). If your program expects
    a unix flavor, you will want :func:`is_unix`.

    Returns:
        bool: True if :attr:`sys.platform` is ``win32`` or ``cygwin``
    """
    return re.match(r'win|cygwin', sys.platform) is not None
