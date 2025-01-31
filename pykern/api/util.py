"""HTTP constants

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import datetime
import pykern.util

#: API that authenticates connections (needed for client)
AUTH_API_NAME = "authenticate_connection"

#: API version (will be defaulted by `connect`
AUTH_API_VERSION = 1


class APICallError(pykern.util.APIError):
    """Raised for an object not found"""

    def __init__(self, error):
        super().__init__("error={}", error)


class APIDisconnected(pykern.util.APIError):
    """Raised when remote server closed or other error"""

    def __init__(self):
        super().__init__("")


class APIForbidden(pykern.util.APIError):
    """Raised for forbidden or protocol error"""

    def __init__(self):
        super().__init__("")


class APINotFound(pykern.util.APIError):
    """Raised for an object not found"""

    def __init__(self, api_name):
        super().__init__("api_name={}", api_name)

def pack_msg(content):

    def _datetime(obj):
        if isinstance(obj, datetime.datetime):
            return int(obj.timestamp())
        return obj

    p = msgpack.Packer(autoreset=False, default=_datetime)
    p.pack(content)
    # TODO(robnagler) getbuffer() would be better
    return p.bytes()


def unpack_msg(content):
    try:
        u = msgpack.Unpacker(
            object_pairs_hook=pykern.pkcollections.object_pairs_hook,
        )
        u.feed(content)
        rv = u.unpack()
    except Exception as e:
        return None, f"msgpack exception={e}"
    if not isinstance(rv, PKDict):
        return None, f"msg not dict type={type(rv)}"
    if "call_id" not in rv:
        return None, "msg missing call_id keys={list(rv.keys())}"
    i = rv.call_id
    if not isinstance(i, int):
        return None, f"msg call_id non-integer type={type(i)}"
    if i <= 0:
        return None, f"msg call_id non-positive call_id={i}"
    return rv, None
