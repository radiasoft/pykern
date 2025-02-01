"""PKDict abstraction and utils

`PKDict` is similar to :class:`argparse.Namespace`, but is a dict that allows
you to treat elements as attributes.

:copyright: Copyright (c) 2015-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# Limit pykern imports so avoid dependency issues for pkconfig
import copy
import collections.abc
import decimal
import types
import pykern.pkcompat


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
        raise PKDictNameError("{}: you cannot delete attributes", name)

    def __getattr__(self, name):
        if name in self:
            return self[name]
        # must match what CPython does exactly:
        # https://github.com/python/cpython/blob/d583738a87c3019dcfe06ed4a0002d1d6c9e9762/Objects/object.c#L899
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __setattr__(self, name, value):
        if name in dir(self):
            raise PKDictNameError(
                "{}: invalid key for PKDict matches existing attribute".format(name)
            )
        self[name] = value

    def copy(self):
        """Override `dict.copy` to ensure the class of the return object is correct.

        Necessary because dict.copy will return a dict rather than PKDict.
        Calls `self.__class__(self)` which makes a shallow copy.
        Subclasses that do not accept this constructor form will need to override this method.

        Returns:
             object: shallow copy of self
        """
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

    def pkmerge(self, to_merge, make_copy=True):
        """Add `to_merge` to `self`

        Types are assumed to match and are not converted, e.g. dict is
        not converted to PKDict. Again, use `canonicalize` if you want
        to avoid type incompatibilities.

        `to_merge`'s values override `self`'s so if say, `to_merge` is ``{'x': None}``,
        then ``self.x`` will be `None` at the end of this call even if it had a value
        before.

        Lists from to_merge are prepended on this same principle, that
        is, to_merge "overrides" self, and prepending is defined as
        overriding. Lists must contain unique elements and duplicates will
        cause an error.

        This function recurses only on PKDicts.

        Args:
            to_merge (dict): elements will be copied into `self`
            make_copy (bool): deepcopy `to_merge` before merging [True]

        Returns:
            PKDict: self
        """

        def _type_err(key, base, merge):
            return AssertionError(
                f"key={key} type mismatch between (self) base={base} and to_merge={merge}"
            )

        if make_copy:
            to_merge = copy.deepcopy(to_merge)

        for k in list(to_merge.keys()):
            t = to_merge[k]
            s = self.get(k)
            if isinstance(s, dict) and isinstance(t, dict):
                s.pkmerge(t, make_copy=False)
            elif isinstance(s, list) and isinstance(t, list):
                # prepend the to_merge values (see docstring above)
                # NOTE: creates a new list
                self[k] = t + s
                # strings, numbers, etc. are hashable, but dicts and lists are not.
                # this test ensures we don't have dup entries in lists.
                y = [x for x in self[k] if isinstance(x, collections.abc.Hashable)]
                assert len(set(y)) == len(
                    y
                ), f"duplicates in key={k} list values={self[k]}"
            elif type(s) == type(t) or s is None or t is None:
                # Just replace, because t overrides type in case of None.
                # And if s is None, it doesn't matter.
                self[k] = t
            else:
                raise _type_err(k, s, t)
        return self

    def pknested_get(self, qualifiers):
        """Split key on dots or iterable and return nested get calls

        If `qualifiers` is a str, will split on dots. Otherwise, will be iterated.

        If an element is a list or tuple, tries to index as int.

        Throws KeyError if the dictionary key doesn't exist.

        Args:
            qualifiers (str or iterable): see above

        Returns:
            object: value of element
        """
        d = self
        for k in qualifiers.split(".") if isinstance(qualifiers, str) else qualifiers:
            try:
                d = d[k]
            except TypeError:
                try:
                    d = d[int(k)]
                    continue
                except (ValueError, TypeError):
                    pass
                raise
        return d

    def pknested_set(self, qualifiers, value):
        """Set nested location identified by `qualifiers` to `value`

        If `qualifiers` is a str, will split on dots. Otherwise, will be iterated.

        If an element does not exist, creates it as a PKDict.

        DOES NOT SUPPORT ints (lists) at this time.

        Args:
            qualifiers (str or iterable): see above
            value (any): assigned to qualifier's location in self

        Returns:
            object: self
        """
        q = qualifiers.split(".") if isinstance(qualifiers, str) else list(qualifiers)
        d = self
        for k in q[:-1]:
            if k not in d:
                d[k] = PKDict()
            d = d[k]
        d[q[-1]] = value
        return self

    def pksetdefault(self, *args, **kwargs):
        """Set values for keys if key not already in self

        Accepts args or kwargs, but not both.
        `args` must be an even number and are interpreted in (key, value) order.
        `kwargs` are accepted as key=value.

        If self does not have `key`, then it will be set to
        `value`. If `key` is already in self, its value is not changed.
        If `value` is a callable, it will be called, and
        `key` will be set to the returned value.

        Args:
            key (object): key that will be assigned `value` if not already set
            value (object): if callable, will be called, else verbatim
        Returns:
            object: self
        """
        if args and kwargs:
            raise AssertionError("one of args or kwargs must be set, but not both")
        if args:
            if len(args) % 2 != 0:
                raise AssertionError(
                    "args must be an even number (pairs of key, value)"
                )
            i = zip(args[0::2], args[1::2])
        else:
            i = kwargs.items()
        for k, v in i:
            self.__pksetdefault_one(k, v)
        return self

    def pksetdefault1(self, *args, **kwargs):
        """Get value if exists else set

        Accepts one key and one value, either as two positional args
        (``key, value``); or one keyword arg (``key=value``).


        If self does not have `key`, then it will be set to
        `value`. If `value` is a callable, it will be called, and
        `key` will be set to the returned value.

        Args:
            key (object): value to get or set
            value (object): if callable, will be called, else verbatim
        Returns:
            object: ``self[key]``; either `value` if just set, or preexisting value

        """
        if args and kwargs:
            raise AssertionError("one of args or kwargs must be set, but not both")
        if args:
            if len(args) == 2:
                return self.__pksetdefault_one(*args)
        elif len(kwargs) == 1:
            for k, v in kwargs.items():
                return self.__pksetdefault_one(k, v)
        raise AssertionError("must pass exactly one key and value")

    def pkunchecked_nested_get(self, qualifiers, default=None):
        """Split key on dots or iterable and return nested get calls

        If `qualifiers` is a str, will split on dots. Otherwise, will be iterated.

        If the element does not exist or is not indexable, fails silently and returns `default`.

        Throws KeyError if the dictionary key doesn't exist.

        Args:
            qualifiers (str or iterable):

        Returns:
            object: value of element
        """
        try:
            return self.pknested_get(qualifiers)
        except (KeyError, IndexError, TypeError, ValueError):
            return default

    def pkupdate(self, *args, **kwargs):
        """Call `dict.update` and return ``self``."""
        super(PKDict, self).update(*args, **kwargs)
        return self

    def __pksetdefault_one(self, key, value):
        if key not in self:
            self[key] = value() if callable(value) else value
        return self[key]


class PKDictNameError(NameError):
    """Raised when a key matches a builtin attribute in `dict`."""

    pass


def canonicalize(obj):
    """Convert to lists and PKDicts for simpler serialization

    Traverse `obj` to convert all values to forms that are compatible
    with serialization protocols like YAML or JSON.

    Simple objects are ensured to match their types e.g. bool, float,
    int, and str.  Objects that are instances of these, are converted
    to these to ensure they are basic types, that is,
    ``canonicalize(str_subclass('a'))`` will be converted to ``str('a')``.

    bytes and bytearrays will be converted to str.

    decimal.Decimal will converted to float.

    All objects are traversed. If no objects need to be converted,
    `obj` will be returned unmodified.

    Generators and iterables are converted to lists.

    Circularities are not detected so infinite recursion can occur.

    Args:
        obj (object): what to convert

    Returns:
        object: converted object (may or may not be the same)
    """
    o = obj
    if o is None:
        return o
    # Order matters so we don't convert bools to ints, since bools are ints.
    for x in (
        (bool,),
        (int,),
        (float,),
        (str,),
        (decimal.Decimal, float),
        ((bytes, bytearray), pykern.pkcompat.from_bytes),
        (
            dict,
            lambda y: PKDict({canonicalize(k): canonicalize(v) for k, v in y.items()}),
        ),
        (types.GeneratorType, lambda y: list(canonicalize(i) for i in y)),
        (collections.abc.Iterable, lambda y: list(canonicalize(i) for i in iter(y))),
    ):
        if isinstance(o, x[0]):
            return x[-1](o)
    raise ValueError(f"unable to canonicalize type={type(o)} value={repr(o):100}")


# Deprecated names
Dict = PKDict
DictNameError = PKDictNameError


def object_pairs_hook(*args, **kwargs):
    """Tries to use `PKDict` if PKDictNameError uses `dict`

    Useful for json, msgpack, etc.

    Works with msgpack's object_hook as well.

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
