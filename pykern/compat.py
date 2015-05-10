# -*- coding: utf-8 -*-
u"""Python 2 and 3 compatbility routines

:mod:`six` and :mod:`future.utils` do most things, but there are some missing
things here

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import locale
import subprocess


def locale_check_output(*args, **kwargs):
    """Convert subprocess output to unicode in the preferred locale.

    Returns:
        str: decoded string (PY2: type unicode)
    """
    return locale_str(subprocess.check_output(*args, **kwargs))


def locale_str(byte_str):
    """Converts the byte string to a unicode str unless already unicode.

    Args:
        bytes or str: The string to be decoded, may be None.

    Returns:
        str: decoded string (PY2: type unicode)
    """
    if type(byte_str) == bytes or type(byte_str) == str and hasattr(byte_str, 'decode'):
        return byte_str.decode(locale.getpreferredencoding())
    return byte_str
