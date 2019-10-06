# -*- coding: utf-8 -*-
u"""JSON wrapper

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import json


#: how bytes are encoded
ENCODING = 'utf-8'


class Encoder(json.JSONEncoder):
    def default(self, obj):
        # Return Python object, and JSONEncoder._iterencode will encode
        return str(obj)


def dump_pretty(obj, filename=None, pretty=True):
    """Formats as json as string

    If an object is not encoded by default, will call str() on the
    object.

    Args:
        obj (object): any Python object
        filename (str or py.path): where to write [None]
        pretty (bool): pretty print [True]

    Returns:
        str: sorted and formatted JSON
    """
    if pretty:
        res = json.dumps(obj, indent=4, separators=(',', ': '), sort_keys=True, cls=Encoder) + '\n'
    else:
        res = json.dumps(obj, cls=Encoder)
    if filename:
        from pykern import pkio

        pkio.py_path(filename).write(res)
    return res


def dump_bytes(obj):
    """Formats as json as bytes for network transfer

    Args:
        obj (object): any Python object

    Returns:
        bytes: (unsorted) formatted JSON
    """
    return dump_pretty(obj, pretty=False).encode(ENCODING)


def load_any(obj):
    """Calls `pkcollections.json_load_any`

    Args:
        obj (object): str or object with "read"

    Returns:
        object: parsed JSON
    """
    from pykern import pkcollections

    return pkcollections.json_load_any(obj)
