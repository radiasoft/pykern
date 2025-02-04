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

    def is_quest_end(self):
        return self._destroyed

    def quest_end(self, in_error=True):
        def _attr_end(name, attr):
            try:
                attr.quest_end(self, in_error=in_error)
            except Exception:
                pkdlog("destroy failed {}={} stack={}", name, attr, pkdexc())

        if self._destroyed:
            return
        x = reversed(list(self.__attrs()))
        self.clear()
        # must be after the clear
        self._destroyed = True
        for k, v in x:
            _attr_end(k, v)

    def quest_init(self, attr_classes, init_kwargs):
        def _set(name, attr):
            if not isinstance(attr, Attr):
                raise AssertionError(f"type=type(obj) not Attr name={name}")
            if name in self:
                raise AssertionError(f"name={name} already added")
            self[name] = attr

        for a in attr_classes:
            s = a if isinstance(a, Attr) else a.quest_init(self, init_kwargs)
            _set(s.ATTR_KEY, s)

    def quest_start(self):
        for _, v in self.__attrs():
            v.quest_start(self)

    def __attrs(self):
        for k, v in self.items():
            if isinstance(k, Attr):
                yield k, v


class Attr(PKDict):
    #: shared Attrs do not have link to qcall
    IS_SINGLETON = False

    def __init__(self, qcall, **kwargs):
        """Initialize object

        Subclasses must define ATTR_KEY so it can be added to qcall.

        If `IS_SINGLETON` is true then qcall must be None. This will
        only be called outside of quest_init. Otherwise, qcall is
        bound to instance.

        Args:
            qcall (API): what qcall is being initialized
            kwargs (dict): inserted into dictionary

        """
        if self.IS_SINGLETON:
            assert qcall is None
            super().__init__(**kwargs)
        else:
            # It may be qcall is None at this point, but that's ok. Will be set below
            super().__init__(qcall=qcall, **kwargs)

    def quest_end(self, qcall, in_error):
        """Called when quest ends

        Right before destroy. No other attributes are available.

        Args:
            qcall (API): qcall being ended
            in_error (bool): True, aborting quest. False, successful quest [True]
        """
        pass

    @classmethod
    def quest_init(cls, qcall, init_kwargs):
        """Initialize an instance of cls and put on qcall

        If `IS_SINGLETON`, qcall is not put on self. `kwargs` must contain ATTR_KEY,
        which is an instance of class.

        Args:
            qcall (API): quest being initialized
            init_kwargs (PKDict): values to passed to `start`
        Returns:
            Attr: instance to bind to quest
        """
        if not cls.IS_SINGLETON:
            self = cls(qcall, **init_kwargs)
        elif (self := init_kwargs.get(cls.ATTR_KEY)) is None:
            raise AssertionError(
                f"init_kwargs does not contain singleton key={cls.ATTR_KEY}"
            )
        if not isinstance(self, Attr):
            raise AssertionError(f"{cls.ATTR_KEY}={self} not instance of Attr")
        return self

    def quest_start(self, qcall):
        """Called after all attrs are initialized

        Args:
            qcall (API): quest being started
        """
        pass


class Spec:
    # qspec
    pass


@contextlib.contextmanager
def start(api_class, attr_classes, **kwargs):
    qcall = api_class()
    e = True
    try:
        qcall.quest_init(attr_classes, PKDict(kwargs))
        qcall.quest_start()
        yield qcall
        e = False
    finally:
        qcall.quest_end(in_error=e)
