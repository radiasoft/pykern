# -*- coding: utf-8 -*-
u"""Python 2 and 3 compatbility routines

:mod:`six` and :mod:`future.utils` do most things, but there are some missing
things here

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import inspect
import locale
import os
import subprocess


def locale_str(value):
    """Converts a value to a unicode str unless already unicode.

    Args:
        value: The string or object to be decoded, may be None.

    Returns:
        str: decoded string (PY2: type unicode)
    """
    if isinstance(value, unicode):
        return value
    if not ( isinstance(value, bytes) or isinstance(value, str) ):
        value = str(value)
    return value.decode(locale.getpreferredencoding())


if not hasattr(str, 'decode'):
    locale_str = str


try:
    unicode
    def isinstance_str(value):
        """Portable test for str

        Args:
            value (object): to test

        Returns:
            bool: True if value is a str or unicode
        """
        return isinstance(value, str) or isinstance(value, unicode)
except NameError:
    def isinstance_str(value):
        """Portable test for str

        Args:
            value (object): to test

        Returns:
            bool: True if value is a str or unicode
        """
        return isinstance(value, str)


def unicode_getcwd():
    """:func:`os.getcwd` unicode wrapper

    Returns:
        str: current directory (PY2: type unicode)
    """
    return os.getcwdu()


if not hasattr(os, 'getcwdu'):
    unicode_getcwd = os.getcwd
