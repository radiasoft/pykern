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
        value (object): The string or object to be decoded, may be None.

    Returns:
        str: decoded string (PY2: type unicode)
    """
    pass

if hasattr(str, 'decode'):
    # py2
    def _locale_str(value):
        if value is None:
            return None
        if isinstance(value, unicode):
            return value
        if not (isinstance(value, bytes) or isinstance(value, str)):
            value = str(value)
        return value.decode(locale.getpreferredencoding())

    def _to_bytes(value):
        assert isinstance(value, str)
        return value

    def _from_bytes(value):
        assert isinstance(value, bytes)
        return value
else:
    # py3
    def _assert_type(value, typ):
        assert isinstance(value, typ), \
            '"{:20}<SNIP>" is not a {} type={}'.format(value, typ, type(value))

    def _locale_str(value):
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode(locale.getpreferredencoding())
        _assert_type(value, str)
        return value

    def _to_bytes(value):
        if isinstance(value, bytes):
            return value
        _assert_type(value, str)
        return bytes(value, 'utf-8')

    def _from_bytes(value):
        if isinstance(value, str):
            return value
        _assert_type(value, bytes)
        return value.decode('utf-8')

locale_str = _locale_str
to_bytes = _to_bytes
from_bytes = _from_bytes


def unicode_unescape(value):
    """Convert escaped unicode and Python backslash values in str

    Args:
        value (str): contains escaped characters
    Returns:
        str: unescaped string
    """
    if hasattr(value, 'decode'):
        # py2
        return value.decode('string_escape')
    # py3
    return value.encode('utf-8').decode('unicode-escape')


def unicode_getcwd():
    """:func:`os.getcwd` unicode wrapper

    Returns:
        str: current directory (PY2: type unicode)
    """
    return os.getcwdu()


if not hasattr(os, 'getcwdu'):
    unicode_getcwd = os.getcwd
