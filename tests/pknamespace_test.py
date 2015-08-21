# -*- coding: utf-8 -*-
"""pytest for :mod:`pykern.pknamespace`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import pytest

from pykern.pknamespace import Namespace


def test_delitem():
    n = Namespace(a=1)
    del n['a']
    with pytest.raises(KeyError):
        del n['b']


def test_getitem():
    n = Namespace(a=1)
    assert 1 == n['a'], \
        'Extract known element as dict'
    with pytest.raises(KeyError):
        if n['b']:
            pass


def test_iter():
    n = Namespace(a=1, b=2)
    i = iter(n)
    assert sorted([i.next(), i.next()]) == ['a', 'b'], \
        'Both values should be returned on iterations'
    with pytest.raises(StopIteration):
        i.next()


def test_len():
    n = Namespace()
    assert 0 == len(n), \
        'Namespace should be empty without values'
    n = Namespace(a=1, b=2)
    assert 2 == len(n), \
        'Namespaces should have two values'


def test_setitem():
    n = Namespace(a=1)
    n['a'] = 2
    assert 2 == n['a'], \
        'Setting a known element should update it'
    n['b'] = 3
    assert 3 == n['b'], \
        'Setting an unknown element should create it'


def test_update():
    n = Namespace(a=1, b=2)
    n.update({})
    assert Namespace(a=1, b=2) == n, \
        'Update of empty dict should do nothing'
    n.update(Namespace())
    assert Namespace(a=1, b=2) == n, \
        'Update of empty dict should do nothing'
    n.update(dict(b=3, c=4))
    assert Namespace(a=1, b=3, c=4) == n, \
        'Update with dict should replace and add'
    n.update(Namespace(b=3, c=4))
    assert Namespace(a=1, b=3, c=4) == n, \
        'Update with dict should replace and add'
