# -*- coding: utf-8 -*-
"""pytest for :mod:`pykern.pkcollections`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkcollections import OrderedMapping, Dict
from pykern.pkunit import pkok, pkexcept, pkeq
import pytest
import random
import string

_VALUE = 1


def test_delattr():
    n = OrderedMapping()
    with pytest.raises(AttributeError):
        del n.not_there
    n.there =1
    del n.there
    assert not hasattr(n, 'there'), \
        'del should delete attribute'


def test_delitem():
    n = OrderedMapping(a=1)
    del n['a']
    assert not hasattr(n, 'a'), \
        'delitem should remove the item'
    with pytest.raises(KeyError):
        del n['b']


def test_dict():
    """Validate Dict()"""
    n = Dict()
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
    with pkexcept(pkcollections.DictNameError):
        delattr(n, 'a')
    with pkexcept(pkcollections.DictNameError):
        setattr(n, 'keys', 3)
    expect = 'invalid key for Dict'
    with pkexcept(expect):
        setattr(n, '__getattr__', 3)
    with pkexcept(pkcollections.DictNameError):
        delattr(n, 'items')
    n = Dict(items=1)
    pkok(list(n.items()) == [('items', 1)], 'items() should be retrievable')
    n['items'] = ''
    del n['items']
    pkok(n.items() == [], 'items() should be deletabley')
    with pkexcept(AttributeError):
        n.missing_attribute()
    with pkexcept(KeyError):
        n['missing key']


def test_eq():
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
    n = OrderedMapping(a=1)
    assert 1 == n['a'], \
        'Extract known element as dict'
    with pytest.raises(KeyError):
        if n['b']:
            pass


def test_init():
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
    j = json.dumps({'a': 33})
    j2 = pkcollections.json_load_any(j)
    pkeq(
        33, j2.a,
        '{}: j2.a is not 33',
        j2.a,
    )
    j = json.dumps({'a': 33, 'b': {'values': 'will collide, but ok'}})
    j2 = pkcollections.json_load_any(j)
    pkcollections.json_load_any(j, object_pairs_hook=pkcollections.Dict)


def test_len():
    n = OrderedMapping()
    assert 0 == len(n), \
        'OrderedMapping should be empty without values'
    n = OrderedMapping(a=1, b=2)
    assert 2 == len(n), \
        'OrderedMappings should have two values'


def test_map_items():
    n = OrderedMapping(a=1)
    n.b = 2
    res = pkcollections.map_items(n, lambda k, v: (v + 1, k))
    assert [(2, 'a'), (3, 'b')] == res, \
        'map_items should call op in order'
    assert [('a', 1), ('b', 2)] == pkcollections.map_items(n), \
        'map_items should return items with no op'


def test_map_keys():
    n = OrderedMapping(a=1)
    n.b = 2
    res = pkcollections.map_keys(n, lambda k: k * 2)
    assert ['aa', 'bb'] == res, \
        'map_keys should call op in order'
    assert ['a', 'b'] == pkcollections.map_keys(n), \
        'map_keys should return keys with no op'


def test_map_values():
    n = OrderedMapping(a=1)
    n.b = 2
    res = pkcollections.map_values(n, lambda v: v * 2)
    assert [2, 4] == res, \
        'map_values should call op in order'
    assert [1, 2] == pkcollections.map_values(n), \
        'map_values should return values with no op'


def test_mapping_merge():
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
    n = OrderedMapping(a=1)
    n['a'] = 2
    assert 2 == n['a'], \
        'Setting a known element should update it'
    n['b'] = 3
    assert 3 == n['b'], \
        'Setting an unknown element should create it'


class _OrderedMapping2(OrderedMapping):
    pass


def _keys(n):
    return [k for k in n]


def _random_init():
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
