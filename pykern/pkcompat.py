# -*- coding: utf-8 -*-
"""Python 2 and 3 compatibility str routines

:mod:`six` and :mod:`future.utils` do most things, but there are some missing
things here

:copyright: Copyright (c) 2015-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
# Limit pykern imports so avoid dependency issues for pkconfig
from __future__ import absolute_import, division, print_function
import inspect
import locale
import os
import subprocess


def from_bytes(value):
    """Converts value to a str

    If `value` is not a str, decode with utf-8.

    If already str, does nothing.

    Args:
        value (object): The string or object to be decoded.

    Returns:
        bytes: encoded string
    """
    if isinstance(value, str):
        return value
    _assert_type(value, (bytes, bytearray))
    return value.decode("utf-8")


def locale_str(value):
    """Converts a value to a unicode str unless already unicode.

    Args:
        value (object): The string or object to be decoded, may be None.

    Returns:
        str: decoded string (PY2: type unicode)
    """
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        return value.decode(locale.getpreferredencoding())
    _assert_type(value, str)
    return value


def to_bytes(value):
    """Converts a value to bytes

    If `value` is a str, encode with utf-8.

    If already bytes, does nothing.

    Args:
        value (object): The string or object to be encoded.

    Returns:
        bytes: encoded string
    """
    if isinstance(value, bytes):
        return value
    _assert_type(value, str)
    return bytes(value, "utf-8")


def unicode_getcwd():
    """:func:`os.getcwd` unicode wrapper

    Returns:
        str: current directory
    """
    return os.getcwd


def unicode_unescape(value):
    """Convert escaped unicode and Python backslash values in str

    Args:
        value (str): contains escaped characters
    Returns:
        str: unescaped string
    """
    return value.encode("utf-8").decode("unicode-escape")


def _assert_type(value, typ):
    if not isinstance(value, typ):
        raise TypeError(
            '"value={:.20}<SNIP>" is not a {}, actual type={}'.format(
                repr(value),
                typ,
                type(value),
            ),
        )
