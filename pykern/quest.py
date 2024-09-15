"""API wrapper

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdformat
import contextlib


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


class API(PKDict):
    """Holds request context for all API calls."""

    METHOD_PREFIX = "api_"

    def attr_set(self, name, obj):
        """Assign an object to qcall"""
        assert isinstance(obj, Attr)
        assert name not in self
        self[name] = obj

    def destroy(self, commit=False):
        for k, v in reversed(list(self.items())):
            if hasattr(v, "destroy"):
                try:
                    v.destroy(commit=commit)
                except Exception:
                    pkdlog("destroy failed attr={} stack={}", v, pkdexc())
            self.pkdel(k)


class APIError(Exception):
    """Application level errors or exceptions sent to client and raised on client"""

    def __init__(self, fmt, *args, **kwargs):
        super().__init__(pkdformat(fmt, *args, **kwargs) if args or kwargs else fmt)


class Attr(PKDict):
    # Class names bound to attribute keys
    _KEY_MAP = PKDict()

    def __init__(self, qcall, **kwargs):
        """Initialize object from a qcall

        Args:
            qcall (API): what qcall is being initialized
            kwargs (dict): insert into dictionary
        """
        super().__init__(qcall=qcall, **kwargs)
        qcall.attr_set(self.ATTR_KEY, self)

    @classmethod
    def init_quest(cls, qcall):
        cls(qcall)


class Spec:
    # qspec
    pass
