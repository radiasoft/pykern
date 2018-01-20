# -*- coding: utf-8 -*-
u"""Wrapper for :mod:`yaml`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkcompat
from pykern import pkinspect
from pykern import pkio
from pykern import pkresource
import py
import yaml


def load_file(filename):
    """Read a file, making sure all keys and values are locale.

    Args:
        filename (str): file to read (Note: ``.yml`` will not be appended)

    Returns:
        object: `pkcollections.Dict` or list
    """
    return load_str(pkio.read_text(filename))


def load_resource(basename):
    """Read a resource, making sure all keys and values are locale

    Args:
        basename (str): file to read without yml suffix

    Returns:
        object: `pkcollections.Dict` or list
    """
    return load_file(
        pkresource.filename(basename + '.yml', pkinspect.caller_module()))


def load_str(value):
    """Read a value, making sure all keys and values are locale.

    Args:
        value (str): string to parse

    Returns:
        object: `pkcollections.Dict` or list
    """
    return _fixup(yaml.load(value))


def _fixup(obj):
    """Convert all objects to locale strings"""
    if isinstance(obj, dict):
        res = pkcollections.Dict()
        for k in obj:
            res[pkcompat.locale_str(k)] = _fixup(obj[k])
        return res
    if isinstance(obj, list):
        res = []
        for v in obj:
            res.append(_fixup(v))
        return res
    if type(obj) == bytes or type(obj) == str and hasattr(obj, 'decode'):
        return pkcompat.locale_str(obj)
    return obj
