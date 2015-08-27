# -*- coding: utf-8 -*-
"""Wrapper for :mod:`array` to simplify and make future compatible.

Not a complete wrapper. New routines added as required.

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from future.utils import bytes_to_native_str

import array

#: Future-proof typecode for double
DOUBLE_TYPECODE = bytes_to_native_str('d')

#: Future-proof typecode for float
FLOAT_TYPECODE = bytes_to_native_str(b'f')

def new_double(*args, **kwargs):
    """Creates a new double ("d") array

    Args are the same as :func:`array.array` except for typecode,
    which is passed by this module.

    Returns:
        array.array: New, initialized array
    """
    return array.array(DOUBLE_TYPECODE, *args, **kwargs)


def new_float(*args, **kwargs):
    """Creates a new float ("f") array

    Args are the same as :func:`array.array` except for typecode,
    which is passed by this module.

    Returns:
        array.array: New, initialized array
    """
    return array.array(FLOAT_TYPECODE, *args, **kwargs)
