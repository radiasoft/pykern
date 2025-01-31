"""API wrapper

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdformat
import contextlib

_SUBSCRIPTION_ATTR = "pyern_quest_subscription"

class API(PKDict):
    """Holds request context for all API calls."""

    METHOD_PREFIX = "api_"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._destroyed = False

    def attr_set(self, name, obj):
        """Assign an object to qcall"""
        assert isinstance(obj, Attr)
        assert name not in self
        self[name] = obj

    def destroy(self, commit=False):
        if self._destroyed:
            return
        x = list(reversed(self.items()))
        self.clear()
        self._destroyed = True
        for k, v in x:
            if hasattr(v, "destroy"):
                try:
                    v.destroy(commit=commit)
                except Exception:
                    pkdlog("destroy failed {}={} stack={}", k, v, pkdexc())

    def is_destroyed(self):
        return self._destroyed


class APIError(Exception):
    """Application level errors or exceptions sent to client and raised on client"""

    def __init__(self, fmt, *args, **kwargs):
        super().__init__(pkdformat(fmt, *args, **kwargs) if args or kwargs else fmt)


class Attr(PKDict):
    #: shared Attrs do not have link to qcall
    IS_SINGLETON = False

    def __init__(self, qcall, **kwargs):
        """Initialize object

        Subclasses must define ATTR_KEY so it can be added to qcall.

        If `IS_SINGLETON` is true then qcall must be None. This will
        only be called outside of init_quest. Otherwise, qcall is bound to instance.

        Args:
            qcall (API): what qcall is being initialized
            kwargs (dict): insert into dictionary

        """
        if self.IS_SINGLETON:
            assert qcall is None
            super().__init__(**kwargs)
        else:
            super().__init__(qcall=qcall, **kwargs)

    @classmethod
    def init_quest(cls, qcall, **kwargs):
        """Initialize an instance of cls and put on qcall

        If `IS_SINGLETON`, qcall is not put on self. `kwargs` must contain ATTR_KEY,
        which is an instance of class.

        Args:
            qcall (API): quest
            kwargs (**): values to passed to `start`
        """
        if not cls.IS_SINGLETON:
            self = cls(qcall, **kwargs)
        elif (self := kwargs.get(cls.ATTR_KEY)) is None:
            raise AssertionError(f"init_quest.kwargs does not contain {cls.ATTR_KEY}")
        elif not isinstance(self, cls):
            raise AssertionError(
                f"init_quest.kwargs.{cls.ATTR_KEY}={self} not instance of {cls}"
            )
        qcall.attr_set(self.ATTR_KEY, self)


class Spec:
    # qspec
    pass


class SubscriptionAttr(Attr):
    ATTR_KEY = "subscription"

    def __init__(self, qcall, **kwargs):
        super().__init__(qcall, **kwargs[self.ATTR_KEY])

    def reply(self, api_result):
        self._connection.subscription_reply(self._call_id, api_result)


def is_subscription_api(func):
    """Is `func` a subscription api?

    Args:
        func (function): class api
    Returns:
        bool: True if is subscription api
    """
    return getattr(func, _SUBSCRIPTION_ATTR, False)


@contextlib.contextmanager
def start(api_class, attr_classes, **kwargs):
    qcall = api_class()
    c = False
    try:
        for a in attr_classes:
            a.init_quest(qcall, **kwargs)
        yield qcall
        c = True
    finally:
        qcall.destroy(commit=c)


def subscription_api(func):
    """Decorator for api functions thhat can be subscribed by clients.

    Args:
        func (function): class api
    Returns:
        function: function to use
    """

    setattr(func, _SUBSCRIPTION_ATTR, True)
    return func
