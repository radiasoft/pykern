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
# Limit pykern imports so avoid dependency issues for pkconfig
import json

class PKDict(dict):
    """A subclass of dict that allows items to be read/written as attributes.

    The purpose of this is as a convenience in coding. You
    can refer to dictionary keys as attributes as long as they
    don't collide with the object's attributes. You should always
    use the `dict` interface to refer to the items of the dictionary
    programmatically, just like you would do with Javascript.

    You can reference any dict key as an attribute as long as it
    does not conflict with an attribute. For example, this works::

        x = PKDict()
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
        raise PKDictNameError('{}: you cannot delete attributes', name)

    def __getattr__(self, name):
        if name in self:
            return self[name]
        # must match what CPython does exactly:
        # https://github.com/python/cpython/blob/d583738a87c3019dcfe06ed4a0002d1d6c9e9762/Objects/object.c#L899
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name in dir(self):
            raise PKDictNameError(
                '{}: invalid key for PKDict matches existing attribute'.format(name))
        super(PKDict, self).__setitem__(name, value)

    def copy(self):
        return self.__class__(self)

    def pkdel(self, name, default=None):
        """Delete item if exists and return value

        The code will survive against concurrent access, but is not thread safe.

        Never throws KeyError.

        Args:
            name (object): item to delete
        Returns:
            object: value (if exists) or default
        """
        try:
            return self[name]
        except KeyError:
            return default
        finally:
            try:
                del self[name]
            except KeyError:
                pass

    def pknested_get(self, dotted_key):
        """Split key on dots and return nested get calls

        Throws KeyError if the dictionary key doesn't exist.

        Args:
            dotted_key (str): what

        Returns:
            object: value of element
        """
        d = self
        for k in dotted_key.split('.'):
            d = d[k]
        return d

    def pksetdefault(self, *args, **kwargs):
        """Get value or set it, possibly after evaluating arg.

        Must pass an even number of args or kwargs, but not both. Each pair
        is interpreted as (key, value).

        If self does not have `key`, then it will be set. If `value` is a callable,
        it will be called to get the value to set.

        Values will be called if they are callable

        Args:
            key (object): value to get or set
            value (object): if callable, will be called, else verbatim
        Returns:
            object: self
        """
        assert not (args and kwargs), \
            'one of args or kwargs must be set, but not both'
        if args:
            assert len(args) % 2 == 0, \
                'args must be an even number (pairs of key, value)'
            i = zip(args[0::2], args[1::2])
        else:
            i = kwargs.items()
        for k, v in i:
            if k not in self:
                self[k] = v() if callable(v) else v
        return self

    def pkunchecked_nested_get(self, dotted_key):
        """Split key on dots and return nested get calls

        If the element does not exist or is not indexable, fails silently with None.

        Args:
            dotted_key (str): what

        Returns:
            object: value of element or None
        """
        d = self
        for k in dotted_key.split('.'):
            try:
                d = d[k]
            except Exception:
                return None
        return d

    def pkupdate(self, *args, **kwargs):
        """Call `dict.update` and return ``self``.
        """
        super(PKDict, self).update(*args, **kwargs)
        return self

    def setdefault(self, *args, **kwargs):
        """DEPRECATED"""
        if len(args) <= 2 and not kwargs:
            return super(PKDict, self).setdefault(*args)
        if args:
            assert len(args) % 2 == 0, \
                'args must be an even number (pairs of key, value)'
            assert not kwargs, 'cannot set both args and kwargs'
            for k, v in zip(args[0::2], args[1::2]):
                if k not in self:
                    self[k] = v
            return self
        assert kwargs, 'must set args or kwargs'
        for k, v in kwargs.items():
            if k not in self:
                self[k] = v
        return self

    def update(self, *args, **kwargs):
        """DEPRECATED"""
        super(PKDict, self).update(*args, **kwargs)
        return self


class PKDictNameError(NameError):
    """Raised when a key matches a builtin attribute in `dict`."""
    pass

# Deprecated names
Dict = PKDict
DictNameError = PKDictNameError

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
    """Read json file or str with ``object_pairs_hook=PKDict``

    Args:
        obj (object): str or object with "read" or py.path
        args (tuple): passed verbatim
        kwargs (dict): object_pairs_hook overriden

    Returns:
        object: parsed JSON
    """
    kwargs.setdefault('object_pairs_hook', object_pairs_hook)
    return json.loads(
        obj.read() if hasattr(obj, 'read') else obj,
        *args,
        **kwargs
    )


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
    Returns:
        object: base
    """
    for k in to_merge:
        base[k] = to_merge[k]
    return base


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
    """Tries to use `PKDict` if else uses `dict`

    Returns:
        object: `PKDict` or `dict`
    """
    try:
        return PKDict(*args, **kwargs)
    except PKDictNameError:
        return dict(*args, **kwargs)


def unchecked_del(obj, *keys):
    """Deletes the keys from obj

    Args:
        obj (object): What to delete from (usually dict)
        keys (object): What to delete
    """
    for k in keys:
        try:
            del obj[k]
        except KeyError:
            pass
