"""HTTP constants

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# Limit pykern imports
import is_subscription
import datetime
import pykern.util

#: API that authenticates connections (needed for client)
AUTH_API_NAME = "authenticate_connection"

#: API version (will be defaulted by `connect`
AUTH_API_VERSION = 1


# Protocol code shared between client & server, not public
MSG_KIND_CALL = "call"
MSG_KIND_REPLY = "reply"
MSG_KIND_SUBSCRIBE = "sub"
MSG_KIND_UNSUBSCRIBE = "unsub"

_SUBSCRIPTION_ATTR = "pykern_api_util_subscription"

class APICallError(pykern.util.APIError):
    """Raised when call execution ends in exception"""

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


class APIKindError(pykern.util.APIError):
    """Raised when kind mismatch"""

    def __init__(self, error):
        super().__init__("error={}", error)


class APINotFound(pykern.util.APIError):
    """Raised for an object not found"""

    def __init__(self, api_name):
        super().__init__("api_name={}", api_name)


class APIProtocolError(pykern.util.APIError):
    """Raised when protocol error at lower level"""

    def __init__(self, error):
        super().__init__("error={}", error)


def is_subscription(func):
    """Is `func` a subscription api?

    Args:
        func (function): class api
    Returns:
        bool: True if is subscription api
    """
    return getattr(func, _SUBSCRIPTION_ATTR, False)


def msg_pack(unserialized):
    """Used by client and server, not public"""
    def _default(obj):
        if isinstance(obj, datetime.datetime):
            return int(obj.timestamp())
        return obj

    p = msgpack.Packer(autoreset=False, default=_default)
    p.pack(unserialized)
    # TODO(robnagler) getbuffer() would be better
    return p.bytes()


def msg_unpack(serialized):
    """Used by client and server, not public"""
    from pykern.pkcollections import PKDict
    try:
        u = msgpack.Unpacker(
            object_pairs_hook=pykern.pkcollections.object_pairs_hook,
        )
        u.feed(serialized)
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

def subscription(func):
    """Decorator for api functions thhat can be subscribed by clients.

    Args:
        func (function): class api
    Returns:
        function: function to use
    """

    # Give some early feedback
    if not inspect.iscoroutinefunction(func):
        raise AssertionError(f"func={func.__name__} must be a coroutine")
    setattr(func, _SUBSCRIPTION_ATTR, True)
    return func
