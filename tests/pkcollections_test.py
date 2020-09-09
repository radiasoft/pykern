# -*- coding: utf-8 -*-
"""pytest for :mod:`pykern.pkcollections`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


_VALUE = 1


def test_delattr():
    from pykern.pkcollections import OrderedMapping

    n = OrderedMapping()
    with pytest.raises(AttributeError):
        del n.not_there
    n.there =1
    del n.there
    assert not hasattr(n, 'there'), \
        'del should delete attribute'


def test_delitem():
    from pykern.pkcollections import OrderedMapping

    n = OrderedMapping(a=1)
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
    # specific string is generated so match exactly
    with pkexcept("'PKDict' object has no attribute 'missing_attribute'"):
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


def test_eq():
    from pykern.pkcollections import OrderedMapping

    class _OrderedMapping2(OrderedMapping):
        pass

    assert not OrderedMapping() == None, \
        'OrderedMapping compared to None is false'
    assert OrderedMapping() == OrderedMapping(), \
        'Empty namespaces are equal'
    assert OrderedMapping() != _OrderedMapping2(), \
        'OrderedMappings with different types are not equal'
    assert OrderedMapping() != OrderedMapping(a=1), \
        'OrderedMappings with different numbers of values are not equal'
    n, order = _random_init()
    n2 = OrderedMapping(n)
    assert n == n2, \
        'OrderedMappings with same keys and values are equal'
    assert OrderedMapping(a=1) != OrderedMapping(a=2), \
        'OrderedMappings with different values are unequal'
    x = order[0]
    v = n2[x]
    del n2[x]
    n2[x] = v
    assert n != n2, \
        'OrderedMappings with different orders are not equal'


def test_getitem():
    from pykern.pkcollections import OrderedMapping

    n = OrderedMapping(a=1)
    assert 1 == n['a'], \
        'Extract known element as dict'
    with pytest.raises(KeyError):
        if n['b']:
            pass


def test_init():
    from pykern.pkcollections import OrderedMapping

    n = OrderedMapping()
    assert [] == _keys(n), \
        'Empty namespace has no elements'
    n = OrderedMapping(a=1)
    with pytest.raises(TypeError):
        n = OrderedMapping('a', 1, 'b')
    # Cannot test for OrderedMapping([]) see code
    with pytest.raises(TypeError):
        OrderedMapping(['b'])
    n = OrderedMapping([('x', 1), ('b', 2)])
    assert ['x', 'b'] == _keys(n), \
        'Init with list of 2-tuples'


def test_init_order():
    from pykern.pkcollections import OrderedMapping

    order = ['c', 'a', 'd', 'b', 'e', 'g', 'f']
    values = []
    for k, v in zip(order, range(len(order))):
        values.append(k)
        values.append(v)
    n = OrderedMapping(values)
    for i, k in enumerate(n):
        assert order[i] == k, \
            '*args keys should be in order of args'
    n = OrderedMapping(*values)
    for i, k in enumerate(n):
        assert order[i] == k, \
            'args[0] keys should be in order of args'


def test_iter():
    n, order = _random_init()
    assert order == _keys(n), \
        'Order of iteration insertion order'


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
    from pykern.pkcollections import OrderedMapping

    n = OrderedMapping()
    assert 0 == len(n), \
        'OrderedMapping should be empty without values'
    n = OrderedMapping(a=1, b=2)
    assert 2 == len(n), \
        'OrderedMappings should have two values'


def test_map_items():
    from pykern import pkcollections
    from pykern.pkcollections import OrderedMapping

    n = OrderedMapping(a=1)
    n.b = 2
    res = pkcollections.map_items(n, lambda k, v: (v + 1, k))
    assert [(2, 'a'), (3, 'b')] == res, \
        'map_items should call op in order'
    assert [('a', 1), ('b', 2)] == pkcollections.map_items(n), \
        'map_items should return items with no op'


def test_map_keys():
    from pykern import pkcollections
    from pykern.pkcollections import OrderedMapping

    n = OrderedMapping(a=1)
    n.b = 2
    res = pkcollections.map_keys(n, lambda k: k * 2)
    assert ['aa', 'bb'] == res, \
        'map_keys should call op in order'
    assert ['a', 'b'] == pkcollections.map_keys(n), \
        'map_keys should return keys with no op'


def test_map_values():
    from pykern import pkcollections
    from pykern.pkcollections import OrderedMapping

    n = OrderedMapping(a=1)
    n.b = 2
    res = pkcollections.map_values(n, lambda v: v * 2)
    assert [2, 4] == res, \
        'map_values should call op in order'
    assert [1, 2] == pkcollections.map_values(n), \
        'map_values should return values with no op'


def test_mapping_merge():
    from pykern import pkcollections
    from pykern.pkcollections import OrderedMapping

    n, order = _random_init()
    pkcollections.mapping_merge(n, {})
    assert list(order) == _keys(n), \
        'mapping_merge of empty dict should do nothing'
    pkcollections.mapping_merge(n, OrderedMapping())
    assert list(order) == _keys(n), \
        'mapping_merge of empty OrderedMapping should do nothing'
    n2 = OrderedMapping(n)
    existing = order[0]
    new = '!'
    pkcollections.mapping_merge(n, {existing: 3, new: 4})
    order += new
    assert list(order) == _keys(n), \
        'mapping_merge with dict should replace and add'
    pkcollections.mapping_merge(n2, OrderedMapping(b=3, c=4))
    assert order == _keys(n), \
        'mapping_merge with dict should replace and add'


def test_repr():
    from pykern.pkcollections import OrderedMapping

    n = OrderedMapping()
    assert 'OrderedMapping()' == repr(n), \
        'Blank repr should not contain keys'
    n.a = 1
    assert 'OrderedMapping(a=1)' == repr(n), \
        'Single element repr should not have any commas'
    n, order = _random_init()
    expect = []
    for c in order:
        expect.append('{}={}'.format(c, _VALUE))
    expect = 'OrderedMapping({})'.format(', '.join(expect))
    assert expect == repr(n), \
        'Multiple elements should be in order of insertion'


def test_setattr():
    from pykern.pkcollections import OrderedMapping

    n = OrderedMapping()
    n.a = 1
    assert 1 == n.a, \
        'new att'
    n.a = 2
    assert 2 == n.a, \
        'overwrite attr'
    n, order = _random_init()
    assert order == _keys(n), \
        'Elements should be in order of creation'
    x = order.pop(3)
    delattr(n, x)
    assert order == _keys(n), \
        'Removed element should not be visible'
    setattr(n, x, _VALUE)
    order.append(x)
    assert order == _keys(n), \
        'Reinserting element should put it at end'


def test_setitem():
    from pykern.pkcollections import OrderedMapping

    n = OrderedMapping(a=1)
    n['a'] = 2
    assert 2 == n['a'], \
        'Setting a known element should update it'
    n['b'] = 3
    assert 3 == n['b'], \
        'Setting an unknown element should create it'


def test_unchecked_del():
    from pykern.pkunit import pkeq
    from pykern import pkcollections

    n = {'a': 1, 'b': 2, 'c': 3}
    pkcollections.unchecked_del(n, 'a')
    pkeq({'b': 2, 'c': 3}, n)
    pkcollections.unchecked_del(n, 'a', 'b', 'c')
    pkeq({}, n)


def _keys(n):
    return [k for k in n]


def _random_init():
    from pykern.pkcollections import OrderedMapping
    import random, string

    n = OrderedMapping()
    order = ''
    # ensure all elements are unique
    while len(order) < 6:
        c = random.choice(string.ascii_lowercase)
        if c in order:
            continue
        order += c
        setattr(n, c, _VALUE)
    return n, list(order)
