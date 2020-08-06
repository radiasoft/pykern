# -*- coding: utf-8 -*-
"""pytest for :mod:`pykern.pkcollections`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_delitem():
    from pykern.pkcollections import PKDict

    n = PKDict(a=1)
    del n['a']
    assert not hasattr(n, 'a'), \
        'delitem should remove the item'
    with pytest.raises(KeyError):
        del n['b']


def test_dict():
    """Validate PKDict()"""
    from pykern import pkcollections
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkok, pkeq, pkexcept


    n = PKDict()
    n.a = 1
    pkok(
        1 == n.a,
        'new attribute should work with x.y format',
    )
    pkok(
        1 == n['a'], \
        'x["y"] should retrieve 1',
    )
    n.a = 2
    pkok(
        2 == n.a,
        'overwrite attr',
    )
    with pkexcept(pkcollections.PKDictNameError):
        delattr(n, 'a')
    with pkexcept(pkcollections.PKDictNameError):
        setattr(n, 'keys', 3)
    expect = 'invalid key for PKDict'
    with pkexcept(expect):
        setattr(n, '__getattr__', 3)
    with pkexcept(pkcollections.PKDictNameError):
        delattr(n, 'items')
    n = PKDict(items=1)
    pkok(list(n.items()) == [('items', 1)], 'items() should be retrievable')
    n['items'] = ''
    del n['items']
    pkok(list(n.items()) == [], 'items() should be deletable')
    with pkexcept(AttributeError):
        n.missing_attribute()
    with pkexcept(KeyError):
        n['missing key']
    pkeq(13, n.pksetdefault('d1', lambda: 13).d1)
    pkeq(13, n.pksetdefault('d1', 'already set').d1)
    pkeq(n, n.pksetdefault('d1', 'already set', 'd2', 2, 'd3', 3, 'd4', 4))
    pkeq(2, n.d2)
    pkeq(3, n.d3)
    pkeq(4, n.d4)
    for i in 'already set', 2, 3, 4:
        with pkexcept(KeyError):
            n[i]
    with pkexcept(AssertionError):
        n.pksetdefault('a', 'b', 'c')
    n = PKDict()
    pkeq(13, n.pksetdefault(d1=13).d1)
    pkeq(13, n.pksetdefault(d1='already set').d1)
    pkeq(n, n.pksetdefault(d1='already set', d2=2, d3=3, d4=4))
    pkeq(2, n.d2)
    pkeq(3, n.d3)
    pkeq(4, n.d4)
    for i in 'already set', 2, 3, 4:
        with pkexcept(KeyError):
            n[i]
    # ok to call empty kwargs
    n.pksetdefault()
    pkeq(4, n.pkdel('d4'))
    pkeq(None, n.pkdel('d4'))
    pkeq('x', n.pkdel('d4', 'x'))


def test_dict_nested_get():
    from pykern import pkcollections
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkok, pkeq, pkexcept

    n = PKDict(one=PKDict(two=1.2), simple=1)
    pkeq(1, n.pknested_get('simple'))
    pkeq(1.2, n.pknested_get('one.two'))
    with pkexcept(TypeError):
        n.pknested_get('simple.not')
    pkeq(1, n.pkunchecked_nested_get('simple'))
    pkeq(1.2, n.pkunchecked_nested_get('one.two'))
    pkeq(None, n.pkunchecked_nested_get('one.two.three'))
    pkeq(None, n.pkunchecked_nested_get('simple.not'))


def test_getitem():
    from pykern.pkcollections import PKDict

    n = PKDict(a=1)
    assert 1 == n['a'], \
        'Extract known element as dict'
    with pytest.raises(KeyError):
        if n['b']:
            pass


def test_json_load_any():
    """Validate json_load_any()"""
    import json
    from pykern import pkcollections
    from pykern.pkunit import pkeq

    j = json.dumps({'a': 33})
    j2 = pkcollections.json_load_any(j)
    pkeq(
        33, j2.a,
        '{}: j2.a is not 33',
        j2.a,
    )
    j = json.dumps({'a': 33, 'b': {'values': 'will collide, but ok'}})
    j2 = pkcollections.json_load_any(j)
    pkcollections.json_load_any(j, object_pairs_hook=pkcollections.PKDict)


def test_len():
    from pykern.pkcollections import PKDict

    n = PKDict()
    assert 0 == len(n), \
        'PKDict should be empty without values'
    n = PKDict(a=1, b=2)
    assert 2 == len(n), \
        'PKDicts should have two values'


def test_unchecked_del():
    from pykern.pkunit import pkeq
    from pykern import pkcollections

    n = {'a': 1, 'b': 2, 'c': 3}
    pkcollections.unchecked_del(n, 'a')
    pkeq({'b': 2, 'c': 3}, n)
    pkcollections.unchecked_del(n, 'a', 'b', 'c')
    pkeq({}, n)
