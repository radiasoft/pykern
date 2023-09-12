# -*- coding: utf-8 -*-
"""Backwards and forward compatible Python utilities

Functions here will be available forever, even when functions are
removed from Python.

Some functions are no longer necessary, e.g. `unicode_getcwd`. Others
are still convenient, e.g. `from_bytes` is useful when you don't know
whether it is a `str` or not.

:copyright: Copyright (c) 2015-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""
# Limit pykern imports so avoid dependency issues for pkconfig
import inspect
import itertools
import locale
import os
import subprocess
import sys


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


def zip_strict(*iterables):
    """`zip` where iterables must be exact.

    ``strict`` option was added in 3.10. This function is always strict.
    Args:
        iterables (object): things to be zipped
    Returns:
        object: Iterator for zipping
    """
    if _version_ok(3, 10):
        return zip(*iterables, strict=True)
    return _zip_strict(iterables)


def _assert_type(value, typ):
    if not isinstance(value, typ):
        raise TypeError(
            '"value={:.20}<SNIP>" is not a {}, actual type={}'.format(
                repr(value),
                typ,
                type(value),
            ),
        )


def _version_ok(major, minor):
    return sys.version_info >= (major, minor)


def _zip_strict(iterables):
    """Code from https://stackoverflow.com/a/69485272"""

    def _first_tail():
        nonlocal first_stopped
        first_stopped = True
        return
        yield

    def _zip_tail():
        if not first_stopped:
            raise ValueError("first iterable is longer than rest")
        for x in itertools.chain.from_iterable(rest):
            raise ValueError(f"left over data={str(x):.100} in iterable")
            yield

    if len(iterables) < 2:
        return zip(*iterables)
    first_stopped = False
    iterables = iter(iterables)
    first = itertools.chain(next(iterables), _first_tail())
    rest = list(map(iter, iterables))
    return itertools.chain(zip(first, *rest), _zip_tail())
