# -*- coding: utf-8 -*-
u"""JSON help

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


#: byte encoding
ENCODING = 'utf-8'


def dump_pretty(obj, filename=None, pretty=True):
    """Formats as json as string

    Args:
        obj (object): any Python object
        filename (str or py.path): where to write [None]
        pretty (bool): pretty print [True]

    Returns:
        str: sorted and formatted JSON
    """
    from pykern import pkio
    import json
    import py.path

    if pretty:
        res = json.dumps(obj, indent=4, separators=(',', ': '), sort_keys=True) + '\n'
    else:
        res = json.dumps(obj)
    if filename:
        pkio.py_path(filename).write(res)
    return res


def dump_bytes(obj):
    """Formats as json as bytes for network transfer

    Args:
        obj (object): any Python object

    Returns:
        bytes: (unsorted) formatted JSON
    """
    import json

    return json.dumps(obj).encode(ENCODING)


def load_any(obj):
    """Calls `pkcollections.json_load_any`

    Args:
        obj (object): str or object with "read"

    Returns:
        object: parsed JSON
    """
    from pykern import pkcollections

    return pkcollections.json_load_any(obj)
