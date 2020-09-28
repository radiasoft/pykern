# -*- coding: utf-8 -*-
"""PKDict abstraction and utils

`PKDict` is similar to :class:`argparse.Namespace`, but is a dict that allows
you to treat elements as attributes.

:copyright: Copyright (c) 2015-2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
# Limit pykern imports so avoid dependency issues for pkconfig
import copy
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

    def __copy__(self):
        return self.__class__(self)

    def __deepcopy__(self, memo):
        rv = self.copy()
        memo[id(rv)] = rv
        for k, v in rv.items():
            rv[copy.deepcopy(k, memo)] = copy.deepcopy(v, memo)
        return rv

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
        return self.__copy__()

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


class PKDictNameError(NameError):
    """Raised when a key matches a builtin attribute in `dict`."""
    pass

# Deprecated names
Dict = PKDict
DictNameError = PKDictNameError


def json_load_any(obj, *args, **kwargs):
    """Parse json with `PKDict` for object pairs

    Args:
        obj (object): str or object with "read" or py.path
        args (tuple): passed verbatim
        kwargs (dict): object_pairs_hook may be overriden

    Returns:
        object: parsed JSON
    """

    def object_pairs_hook(*args, **kwargs):
        """Tries to use `PKDict` if else uses `dict`

        Returns:
            object: `PKDict` or `dict`
        """
        try:
            return PKDict(*args, **kwargs)
        except PKDictNameError:
            return dict(*args, **kwargs)


    kwargs.setdefault('object_pairs_hook', object_pairs_hook)
    return json.loads(
        obj.read() if hasattr(obj, 'read') else obj,
        *args,
        **kwargs
    )


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
