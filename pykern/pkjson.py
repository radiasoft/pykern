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

_JSON_INT_MAX = 2**53 - 1
_JSON_INT_MIN = -(2**53) + 1


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


def load_any(obj, *args, **kwargs):
    """Parse object containing json into dict-like object.

    object_pairs_hook modifies the return type.

    Args:
        obj (object): str or object with "read" or py.path
        args (tuple): passed verbatim to json.loads()
        kwargs (dict): object_pairs_hook may be overriden

    Returns:
        object: parsed JSON
    """
    from pykern import pkcollections

    def _parse_int(value):
        if len(value) > 64:
            # 64 is pretty arbitrary, but reasonable in Python. Nothing in
            # JSON can be this large.
            raise ValueError(f"number={value:60s}... unreasonably large")
        if len(value) > 17:
            return float(value)
        res = int(value)
        if _JSON_INT_MIN <= res <= _JSON_INT_MAX:
            return res
        return float(res)

    kwargs.setdefault("parse_int", _parse_int)
    kwargs.setdefault("object_pairs_hook", pkcollections.object_pairs_hook)
    return json.loads(obj.read() if hasattr(obj, "read") else obj, *args, **kwargs)
