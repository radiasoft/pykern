# -*- coding: utf-8 -*-
"""JSON wrapper

:copyright: Copyright (c) 2017-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import json


#: how bytes are encoded
ENCODING = "utf-8"

#: MIME type
MIME_TYPE = "application/json"


#: Content-Type MIME header
CONTENT_TYPE = f'{MIME_TYPE}; charset="{ENCODING}"'


class Encoder(json.JSONEncoder):
    def default(self, obj):
        # Return Python object, and JSONEncoder._iterencode will encode
        return str(obj)


def dump_bytes(obj, **kwargs):
    """Formats as json as bytes for network transfer

    Args:
        obj (object): any Python object
        kwargs (object): other arguments to `dump_pretty`
    Returns:
        bytes: (unsorted) formatted JSON
    """
    return dump_pretty(obj, pretty=False, **kwargs).encode(ENCODING)


def dump_pretty(obj, filename=None, pretty=True, **kwargs):
    """Formats as json as string

    If an object is not encoded by default, will call str() on the
    object.

    Args:
        obj (object): any Python object
        filename (str or py.path): where to write [None]
        pretty (bool): pretty print [True]
        kwargs (object): other arguments to `json.dumps`

    Returns:
        str: sorted and formatted JSON
    """
    if pretty:
        res = (
            json.dumps(
                obj,
                indent=4,
                separators=(",", ": "),
                sort_keys=True,
                cls=Encoder,
                **kwargs,
            )
            + "\n"
        )
    else:
        res = json.dumps(obj, separators=(",", ":"), cls=Encoder, **kwargs)
    if filename:
        from pykern import pkio

        pkio.write_text(filename, res)
    return res


def dump_str(obj, **kwargs):
    """Formats as a compact json as string

    Args:
        obj (object): any Python object
        kwargs (object): other arguments to `dump_pretty`
    Returns:
        str: (unsorted) formatted JSON
    """
    return dump_pretty(obj, pretty=False, **kwargs)


def load_any(obj):
    """Calls `pkcollections.json_load_any`

    Args:
        obj (object): str or object with "read"

    Returns:
        object: parsed JSON
    """
    from pykern import pkcollections

    return pkcollections.json_load_any(obj)
