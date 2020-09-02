# -*- coding: utf-8 -*-
u"""Wrapper for :mod:`yaml`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern import pkcompat
from pykern import pkinspect
from pykern import pkio
from pykern import pkresource
import ruamel.yaml

def dump_pretty(obj, filename, pretty=True, **kwargs):
    """Formats as yaml as string

    If an object is not encoded by default, will call str() on the
    object.

    Unlike `pkjson.dump_pretty`, returns nothing.

    Args:
        obj (object): any Python object
        filename (str or py.path): where to write [None]
        pretty (bool): pretty print [True]
        kwargs (object): other arguments to `ruamel.yaml.dump`
    """
    y = ruamel.yaml.YAML()
    if pretty:
        y.indent(mapping=2, sequence=4, offset=2)
    y.dump(_fixup_dump(obj), stream=pkio.open_text(filename, mode='wt'), **kwargs)


def load_file(filename):
    """Read a file, making sure all keys and values are locale.

    Args:
        filename (str): file to read (Note: ``.yml`` will not be appended)

    Returns:
        object: `PKDict` or list
    """
    return load_str(pkio.read_text(filename))


def load_resource(basename):
    """Read a resource, making sure all keys and values are locale

    Args:
        basename (str): file to read without yml suffix

    Returns:
        object: `PKDict` or list
    """
    return load_file(
        pkresource.filename(basename + '.yml', pkinspect.caller_module()),
    )


def load_str(value):
    """Read a value, making sure all keys and values are locale.

    Args:
        value (str): string to parse

    Returns:
        object: `PKDict` or list
    """
    r = ruamel.yaml.YAML(typ='safe')
    return _fixup_load(r.load(value))


def _fixup_dump(obj):
    if isinstance(obj, PKDict):
        return {k: _fixup_dump(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_fixup_dump(v) for v in obj]
    return obj


def _fixup_load(obj):
    """Convert all objects to locale strings and PKDict"""
    if isinstance(obj, dict):
        r = PKDict()
        for k, v in obj.items():
            r[pkcompat.locale_str(k)] = _fixup_load(v)
        return r
    if isinstance(obj, (list, tuple)):
        return [_fixup_load(v) for v in obj]
    if type(obj) == bytes or type(obj) == str and hasattr(obj, 'decode'):
        return pkcompat.locale_str(obj)
    return obj
