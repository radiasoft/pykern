# -*- coding: utf-8 -*-
"""Ordered attribute mapping type

Similar to :class:`argparse.Namespace`, but is ordered, and behaves like
dictionary except there are no public methods on OrderedMapping. All operations
are operators or Python builtins so that the attribute names from clients of
a OrderedMapping don't collide.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
# Avoid pykern imports so avoid dependency issues for pkconfig
import json

class Dict(dict):
    """A subclass of dict that allows items to be read/written as attributes.

    The purpose of this is as a convenience in coding. You
    can refer to dictionary keys as attributes as long as they
    don't collide with the object's attributes. You should always
    use the `dict` interface to refer to the items of the dictionary
    programmatically, just like you would do with Javascript.

    You can reference any dict key as an attribute as long as it
    does not conflict with an attribute. For example, this works::

        x = Dict()
        x.a = 1
        assert 1 == x.a
        x['a'] = 3
        assert 3 == x.a
        assert 'a' == x.keys()[0]

    You can't set an attribute that already exists. These calls throw
    exceptions::

        x.values = 1
        delattr(x, 'values')

    `dict` doesn't allow this anyway. However, you can't set or
    delete any existing attribute, even writable attributes. Indeed,
    you can't delete attributes at all. Subclasses should be "containers"
    only, not general objects.
    """
    def __delattr__(self, name):
        raise DictNameError('{}: you cannot delete attributes', name)

    def __getattr__(self, name):
        try:
            return self.__getattribute__(name)
        except AttributeError:
            try:
                return self[name]
            except KeyError:
                return self.__getattribute__(name)

    def __setattr__(self, name, value):
        if name in dir(self):
            raise DictNameError(
                '{}: invalid key for Dict matches existing attribute'.format(name))
        super(Dict, self).__setitem__(name, value)


class DictNameError(NameError):
    """Raised when a key matches a builtin attribute in `dict`."""
    pass


class OrderedMapping(object):
    """Ordered mapping can be initialized by kwargs or single argument.

    Args:
        first (object): copy map in order of iterator, OR
        kwargs (dict): initial values (does not preserver order)

    All operations are munged names to avoid collisions with the clients
    of OrderedMapping so there are no "methods" on self except operator overloads.
    """
    def __init__(self, *args, **kwargs):
        self.__order = []
        # Remove __order's mangled name from __order
        self.__order.pop(0)
        if args:
            assert not kwargs, \
                'May not pass kwargs if passing args'
            if len(args) == 1:
                if isinstance(args[0], list):
                    args = args[0]
                else:
                    kwargs = args[0]
                    args = None
            if args:
                if isinstance(args[0], (tuple, list)):
                    # For json.object_pairs_hook, accept list of 2-tuples
                    for k, v in args:
                        setattr(self, k, v)
                    return
                if len(args) % 2 != 0:
                    raise TypeError(
                        'If mapping type given, must be even number of values')
                i = iter(args)
                for k, v in zip(i, i):
                    setattr(self, k, v)
                return
            # If args[0] is not mapping type, then this method
            # will not fail as it should. The problem is that you
            # can't test for a mapping type. Sequences implement all
            # the same functions, just that they don't return the keys
            # for iterators but the values, which is why ['a'] will
            # fail as an initializer.
        for k in kwargs:
            setattr(self, k, kwargs[k])

    __hash__ = None

    def __contains__(self, key):
        return key in self.__order

    def __delattr__(self, name):
        super(OrderedMapping, self).__delattr__(name)
        self.__order.remove(name)

    def __delitem__(self, key):
        try:
            delattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __eq__(self, other):
        """Type of object, and order of keys and values must be the same"""
        if not type(self) == type(other):
            return False
        # Types must be the same. "__order" is included in vars()
        # so verifies order, too.
        return vars(self) == vars(other)

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __iter__(self):
        return iter(self.__order)

    def __len__(self):
        return len(self.__order)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        res = type(self).__name__ + '('
        if not len(self):
            return res + ')'
        for name in self:
            res += '{!s}={!r}, '.format(name, getattr(self, name))
        return res[:-2] + ')'

    def __setattr__(self, name, value):
        super(OrderedMapping, self).__setattr__(name, value)
        if name not in self.__order:
            self.__order.append(name)

    def __setitem__(self, key, value):
        setattr(self, key, value)


def json_load_any(obj, *args, **kwargs):
    """Read json file or str with ``object_pairs_hook=Dict``

    Args:
        obj (object): str or object with "read"
        args (tuple): passed verbatim
        kwargs (dict): object_pairs_hook overriden

    Returns:
        object: parsed JSON
    """
    kwargs.setdefault('object_pairs_hook', object_pairs_hook)
    o = obj.read() if hasattr(obj, 'read') else obj
    return json.loads(o, *args, **kwargs)


def map_items(value, op=None):
    """Iterate over mapping, calling op with key, value

    Args:
        value (object): Any object that implements iteration on keys
        op (function): called with each key, value, in order
            (default: return (key, value))

    Returns:
        list: list of results of op
    """
    if not op:
        return [(k, value[k]) for k in value]
    return [op(k, value[k]) for k in value]


def map_keys(value, op=None):
    """Iterate over mapping, calling op with key

    Args:
        value (object): Any object that implements iteration on keys
        op (function): called with each key, in order (default: return key)

    Returns:
        list: list of results of op
    """
    if not op:
        return [k for k in value]
    return [op(k) for k in value]


def mapping_merge(base, to_merge):
    """Add or replace values from to_merge into base

    Args:
        base (object): Implements setitem
        to_merge (object): implements iter and getitem
    """
    for k in to_merge:
        base[k] = to_merge[k]


def map_to_dict(value):
    """Convert mapping to dictionary

    Args:
        value (object): mapping to convert

    Returns:
        dict: Converted mapping
    """
    return dict(map_items(value))


def map_values(value, op=None):
    """Iterate over mapping, calling op with value

    Args:
        value (object): Any object that implements iteration on values
        op (function): called with each key, in order (default: return value)

    Returns:
        list: list of results of op
    """
    if not op:
        return [value[k] for k in value]
    return [op(value[k]) for k in value]


def object_pairs_hook(*args, **kwargs):
    """Tries to use `Dict` if else uses `dict`

    Returns:
        object: `Dict` or `dict`
    """
    try:
        return Dict(*args, **kwargs)
    except DictNameError:
        return dict(*args, **kwargs)
