# -*- coding: utf-8 -*-
"""pytest for :mod:`pykern.pkcollections`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_canonicalize():
    from pykern.pkunit import pkeq, pkexcept
    from pykern.pkcollections import PKDict, canonicalize
    import decimal

    class _i(int):
        pass

    class _o:
        pass

    pkeq(None, canonicalize(None))
    pkeq(3.3, canonicalize(decimal.Decimal(3.3)))
    pkeq(int, type(canonicalize(_i(1))))
    pkeq([1], canonicalize(set([1])))
    pkeq(["bytes", "str"], canonicalize(iter([b"bytes", "str"])))
    pkeq([9.01, True, False], canonicalize((9.01, True, False)))
    d = canonicalize({_i(-1): dict(a="b", c=frozenset([13]))})
    pkeq(PKDict({-1: PKDict(a="b", c=[13])}), d)
    pkeq(int, type(list(d.keys())[0]))
    with pkexcept("unable to canonicalize"):
        canonicalize(_o())


def test_delitem():
    from pykern.pkcollections import PKDict

    n = PKDict(a=1)
    del n["a"]
    assert not hasattr(n, "a"), "delitem should remove the item"
    with pytest.raises(KeyError):
        del n["b"]


def test_dict():
    """Validate PKDict()"""
    from pykern import pkcollections
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkok, pkeq, pkexcept

    n = PKDict()
    n.a = 1
    pkok(
        1 == n.a,
        "new attribute should work with x.y format",
    )
    pkok(
        1 == n["a"],
        'x["y"] should retrieve 1',
    )
    n.a = 2
    pkok(
        2 == n.a,
        "overwrite attr",
    )
    with pkexcept(pkcollections.PKDictNameError):
        delattr(n, "a")
    with pkexcept(pkcollections.PKDictNameError):
        setattr(n, "keys", 3)
    expect = "invalid key for PKDict"
    with pkexcept(expect):
        setattr(n, "__getattr__", 3)
    with pkexcept(pkcollections.PKDictNameError):
        delattr(n, "items")
    n = PKDict(items=1)
    pkok(list(n.items()) == [("items", 1)], "items() should be retrievable")
    n["items"] = ""
    del n["items"]
    pkok(list(n.items()) == [], "items() should be deletable")
    # specific string is generated so match exactly
    with pkexcept("'PKDict' object has no attribute 'missing_attribute'"):
        n.missing_attribute()
    with pkexcept(KeyError):
        n["missing key"]


def test_dict_copy():
    from pykern.pkcollections import PKDict
    import copy
    from pykern.pkunit import pkeq, pkne

    n = PKDict(a=1, b=PKDict(c=3))
    m = copy.copy(n)
    pkne(id(n), id(m))
    pkeq(id(n.b), id(n.b))
    m = copy.deepcopy(n)
    pkne(id(n), id(m))
    pkeq(id(n.b), id(n.b))


def test_dict_pkdel():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkok, pkeq, pkexcept

    n = PKDict(d4=4)
    pkeq(4, n.pkdel("d4"))
    pkeq(None, n.pkdel("d4"))
    pkeq("x", n.pkdel("d4", "x"))


def test_dict_pknested_get():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq, pkexcept

    n = PKDict(one=PKDict(two=1.2), simple=1)
    pkeq(1, n.pknested_get("simple"))
    pkeq(1, n.pknested_get(["simple"]))
    pkeq(1.2, n.pknested_get("one.two"))
    pkeq(1.2, n.pknested_get(("one", "two")))
    with pkexcept(TypeError):
        n.pknested_get("simple.not")
    pkeq(1, n.pkunchecked_nested_get("simple"))
    pkeq(1.2, n.pkunchecked_nested_get("one.two"))
    pkeq(None, n.pkunchecked_nested_get("one.two.three"))
    pkeq(None, n.pkunchecked_nested_get("simple.not"))
    pkeq(36, n.pkunchecked_nested_get("simple.not", 36))
    n = PKDict(one=[10, PKDict(last="done"), 14])
    pkeq("done", n.pknested_get("one.1.last"))


def test_dict_pknested_set():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq, pkexcept

    n = PKDict(one=PKDict())
    n.pknested_set("one.two", 2)
    n.pknested_set("other", 3)
    pkeq(2, n.pknested_get("one.two"))
    pkeq(3, n.pknested_get(["other"]))


def test_dict_pksetdefault():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkok, pkeq, pkexcept

    n = PKDict()
    pkeq(13, n.pksetdefault("d1", lambda: 13).d1)
    pkeq(13, n.pksetdefault("d1", "already set").d1)
    pkeq(n, n.pksetdefault("d1", "already set", "d2", 2, "d3", 3, "d4", 4))
    pkeq(2, n.d2)
    pkeq(3, n.d3)
    pkeq(4, n.d4)
    for i in "already set", 2, 3, 4:
        with pkexcept(KeyError):
            n[i]
    with pkexcept(AssertionError):
        n.pksetdefault("a", "b", "c")
    n = PKDict()
    pkeq(13, n.pksetdefault(d1=13).d1)
    pkeq(13, n.pksetdefault(d1="already set").d1)
    pkeq(n, n.pksetdefault(d1="already set", d2=2, d3=3, d4=4))
    pkeq(2, n.d2)
    pkeq(3, n.d3)
    pkeq(4, n.d4)
    for i in "already set", 2, 3, 4:
        with pkexcept(KeyError):
            n[i]
    # ok to call empty kwargs
    n.pksetdefault()


def test_dict_pksetdefault1():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkok, pkeq, pkexcept

    n = PKDict()
    pkeq(13, n.pksetdefault1("d1", lambda: 13))
    pkeq(13, n.pksetdefault1("d1", "already set"))
    pkeq("value", n.pksetdefault1(key1="value"))
    pkeq("other", n.pksetdefault1(key2=lambda: "other"))
    for a, k, r in (
        (("d2", 2, "d3", 3), dict(), "too many args"),
        ((), dict(d2=2, d3=3), "too many kwargs"),
        ((), dict(), "no args"),
        (("d3",), dict(), "one arg"),
    ):
        with pkexcept(AssertionError, r):
            n.pksetdefault1(*a, **k)


def test_dict_pkupdate():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq

    d = PKDict()
    pkeq(id(d), id(d.pkupdate(a=1)))
    pkeq(1, d.a)


def test_pkmerge():
    from pykern.pkunit import pkeq
    from pykern.pkcollections import PKDict

    s = PKDict(one=PKDict(two=None, three=PKDict(four=[4])), five=99)
    s.pkmerge(PKDict(five=5, one=PKDict(two=[1, 2], three=PKDict(four2=4.2))))
    pkeq(PKDict(one=PKDict(two=[1, 2], three=PKDict(four=[4], four2=4.2)), five=5), s)


def test_subclass():
    from pykern import pkcollections
    from pykern.pkunit import pkeq, pkok
    import copy

    class S(pkcollections.PKDict):
        def __init__(self, some_arg):
            self._some_arg = some_arg

        def __copy__(self):
            return self.__class__(self._some_arg)

    e = S(["anything"])
    a = copy.deepcopy(e)
    pkeq(e._some_arg, a._some_arg)
    pkok(id(e._some_arg) != id(a._some_arg), "some args is not copied")


def test_unchecked_del():
    from pykern.pkunit import pkeq
    from pykern import pkcollections

    n = {"a": 1, "b": 2, "c": 3}
    pkcollections.unchecked_del(n, "a")
    pkeq({"b": 2, "c": 3}, n)
    pkcollections.unchecked_del(n, "a", "b", "c")
    pkeq({}, n)
