"""API constants

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# Limit pykern imports
from pykern.pkcollections import PKDict
import datetime
import enum
import inspect
import msgpack
import pykern.util

#: API that authenticates connections (needed for client)
AUTH_API_NAME = "authenticate_connection"

#: API version for AUTH (and for pykern.api)
AUTH_API_VERSION = 658584001

# Protocol code shared between client & server, not public

# A bit of type checking
_MSG_KIND_BASE = 777500


class MsgKind(enum.Enum):
    CALL = _MSG_KIND_BASE + 1
    REPLY = _MSG_KIND_BASE + 2
    SUBSCRIBE = _MSG_KIND_BASE + 3
    UNSUBSCRIBE = _MSG_KIND_BASE + 4

    def is_call(self):
        return self is self.CALL

    def is_reply(self):
        return self is self.REPLY

    def is_subscribe(self):
        return self is self.SUBSCRIBE

    def is_unsubscribe(self):
        return self is self.UNSUBSCRIBE


_MSG_KIND_IS_VALID = PKDict(
    client=frozenset((MsgKind.REPLY, MsgKind.UNSUBSCRIBE)),
    server=frozenset((MsgKind.CALL, MsgKind.SUBSCRIBE, MsgKind.UNSUBSCRIBE)),
)


_SUBSCRIPTION_ATTR = "pykern_api_util_subscription"


class APICallError(pykern.util.APIError):
    """Raised when call execution ends in exception or other error"""

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
        if isinstance(obj, enum.Enum):
            return obj.value
        if hasattr(obj, "tolist"):
            # tolist works with pandas and numpy. If tolist takes
            # params or not a callable, then the result will be the
            # essentially the same as not having this code.
            return obj.tolist()
        return obj

    p = msgpack.Packer(autoreset=False, default=_default)
    p.pack(unserialized)
    # TODO(robnagler) getbuffer() would be better
    return p.bytes()


def msg_unpack(serialized, which):
    """Used by client and server, not public"""

    def _int(rv, which):
        i = rv[which]
        if not isinstance(i, int):
            return None, f"msg {which} non-integer type={type(i)}"
        if i <= 0:
            return None, f"msg {which} non-positive int={i}"
        return None

    def _kind(rv):
        if r := _int(rv, "msg_kind"):
            return r
        try:
            k = MsgKind(rv.msg_kind)
            if k not in _MSG_KIND_IS_VALID[which]:
                return None, f"{k} invalid for {which}"
            rv.msg_kind = k
            return None
        except Exception as e:
            return None, f"msg_kind={rv.msg_kind} not in valid"

    try:
        u = msgpack.Unpacker(
            object_hook=pykern.pkcollections.object_pairs_hook,
        )
        u.feed(serialized)
        rv = u.unpack()
    except Exception as e:
        return None, f"msgpack exception={e}"
    if not isinstance(rv, PKDict):
        return None, f"msg not dict type={type(rv)}"
    for f in "call_id", "msg_kind":
        if not rv.get(f):
            return None, f"msg missing {f} keys={list(rv.keys())}"
    return _int(rv, "call_id") or _kind(rv) or (rv, None)


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
