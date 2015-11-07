# -*- coding: utf-8 -*-
"""Configuration of PyKern and clients

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

# Import the minimum number of modules and none from pykern
# pkconfig is the first module imported by all other modules in pykern
import collections
import importlib
import re


#: Module to declaration info mapping
_info = collections.OrderedDict()


#: Validate identifer valid
_PARAM_RE = re.compile('^[a-z][a-z0-9_]*$')


#: Order of channels from least to most stable
CHANNELS = ('develop', 'alpha', 'beta', 'production')


def extend(postfix):
    """Extend the previous list value with ``postfix``

    Example::

        'my_app.some_module': {
            'param1': {
                'key1': pkconfig.extend([4, 5]),
            }),
        }

    Suppose the previous value of ``param1`` is::

        'param1': {
            'key1': [1, 2, 3],
            'key2': 'other value',
        }


    The result of `extend` would be::

        'param1': {
            'key1': [1, 2, 3, 4, 5],
            'key2': 'other value',
        }

    Args:
        postfix (list): the value to append
    """
    assert isinstance(value, list), \
        '{}: postfix must be a list'.format(value)
    return _MergeOp(postfix, 'extend')


def init_all_modules(root_pkg):
    """Initializes `Params` returned by `register` and calls `pkconfig_init_hander`.

    Each module is initialized in the order that `register` was called.
    The config values are parsed and inserted into the `Params` object for
    the module and then it's `pkconfig_init_hander` is called, if defined.

    This is the "boot" of the program. Modules should avoid initializing globals
    before this routine is called.

    Modules can expect multiple initializations during their
    life. This might happen if a module is reloaded or `inject_values`
    is called.
    """
    v = _values(root_pkg)


def inject_values(values):
    """Update `Params` with pkconfig dict

    `init_all_modules` will be called on all modules so that modules can
    reinitialize.

    Args:
        values (dict): hierarchy of packages and config names
    """
    pass


def overwrite(replacement):
    """Overwrite previous value with ``replacement``, do not `update`

    Example::

        'my_app.some_module': {
            'param1': pkconfig.overwrite('new value'),
            'param2': 'other value',
        },

    This would overwrite the previous ``my_app.some_module`` value
    for ``param1`` possibly contained in pykconfig_defaults or some
    other pkconfig file.

    By default, you would only have to overwrite for parameters of
    type `list` or `dict`.

    Args:
        replacement (object): what to overwrite previous value with
    """
    return _MergeOp(replacement, 'overwrite')


def prepend(prefix):
    """Insert ``prefix`` in the previous list value

    This is the default behavior for merging when the old
    and new values are both an instance of  `list`.

    Example::

        'my_app.some_module': {
            'param1': pkconfig.prepend([1, 2]),
        }

    Suppose the previous value of ``param1`` is::

        'param1': pkconfig.prepend([4, 5]),

    The result of `extend` would be::

        'param1': [1, 2, 4, 5],

    Args:
        prefix (list): the value to insert before old value
    """
    assert isinstance(value, list), \
        '{}: prefix must be a list'.format(prefix)
    return MergeOp(prefix, 'prepend')


def pkconfig_init_hander():
    """Called after `Params` returned by `register` are updated.

    Used to (re-)initialize globals with configuration provided.
    """
    pass


def register(**kwargs):
    """Declares config params for calling module.

    Args:
        kwargs (dict): param name to (default, parser, docstring)

    Returns:
        Params: an empty object which will be populated with parameter values
    """
    global _info
    try:
        frame = inspect.currentframe().f_back
        module = inspect.getmodule(frame)
    finally:
        frame = None
    d = {}
    mn = module.__name__
    for k in kwargs:
        assert _ELEMENT_RE.search(k), \
            '{}.{}: must be a lowercase identifier (no leading underscore)'.format(n, k)
        v = kwargs[k]
        assert len(v) == 3, \
            '{}: declaration must be a 3-tuple ({}.{})'.format(v, n, k)
        assert hasattr(v[1], '__call__'), \
            '{}: parser must be a callable ({}.{})'.format(v[1], n, k)
        d[k] = dict(zip(('default', 'parser', 'docstring'), v))
    p = Params(d)
    _info[mn] = {
        'module': module,
        'params': p,
        'decls': d,
    }
    return p


def update(to_merge):
    """Update the previous dict value with ``to_merge`` (recursively).

    This is the default behavior for merging when the old
    and new values are both an instance of  `dict`.

    The merge is recursive. Recursion does not traverse non-dict
    elements or when an `overwrite` element is encountered.

    Example::

        'my_app.some_module': {
            'param1': pkconfig.update({
                'key1': 'v1',
                'key2': 'v2',
                'key3': {
                    'keyA': 'vA',
                    'keyB': 'vB',
                },
            }),
        }

    Suppose the previous value of ``param1`` is::

        'param1': {
            'key1': 'v1 old',
            'key3': {
                'keyA': 'vA old',
                'keyC': 'vC',
            },
            'key4': 'v4',
        }


    The result of the `update` would be::

        'param1': {
            'key1': 'v1',
            'key2': 'v2',
            'key3': {
                'keyA': 'vA',
                'keyB': 'vB',
                'keyC': 'vC',
            },
            'key4': 'v4',
        }

    Args:
        to_merge (dict): what to replace in previous value
    """
    assert isinstance(value, dict), \
        '{}: new must be a dict'.format(to_merge)
    return _MergeOp(to_merge, 'update')


class Params(object):
    """Container for parameter values.

    Attributes are the names of the parameters.
    """
    pass


def _values(root_pkg):
    """Coallesce pkconfig_defaults, file(s), and environ vars.

    Args:
        root_pkg (str): package to start with.
    """
    channel = os.getenv('PYKERN_CHANNEL', CHANNELS[0])
    assert channel in CHANNELS, \
        '{}: invalid $PYKERN_CHANNEL; must be {}'.format(channel, CHANNELS)
    ev = {}
    #TODO(robnagler) Path hardwired allow no import of pykern
    for p in (root_pkg,) + (None if root_pkg == 'pykern' else ('pykern',)):
        try:
            m = importlib.import_module(p + '.pkconfig_defaults'))
            _values_merge(getattr(m, channel)(), v)
        except ImportError:
            pass
    # Bring in a file?


def _values_merge(new, base):
    """Merge `new` into `base`, recursively.

    Args:
        new (dict): what to use for update
        base (dict): old values to be replaced, possibly
    """
    for nk in new:
        if nk in base:
            if type(base[nk]) == type(new[nk]) and isinstance(new[nk], (list, dict)):
                op = 'prepend' if isinstance(new[nk], list) else 'update'
                new[nk] = _MergeOp(op, new[nk])
            if isinstance(new[nk], _MergeOp):
                base[nk] = new[nk].op(base[nk])
                continue
        base[nk] = new[nk]


def _values_flatten(values):
    """Flatten names of parameters to absolute values

    Asserts no name overrides and verifies all names

    Args:
        values (dict): hierarchical param structure

    Returns:
        dict: flattened names
    """
    seen = {}
    return {}


class _MergeOp(object):
    """Marks values with behavior ``op`` for merging

    Args:
        op (str): name of the method to perform operation
        value (any): object to be merged
    """
    def __init__(self, op, value):
        self.op = getattr(self, op)
        self.value = value


    def extend(self, base):
        """Joins `base` and `new`

        Args:
            base (list): value to be extended

        Returns:
            list: ``self.value + base``
        """
        return base + self.value

    def overwrite(self, base):
        """Overwrites base with value

        Args:
            base (object): ignored

        Returns:
            object: ``self.value``
        """
        return self.value

    def prepend(self, base):
        """Joins `new` and `base`

        Args:
            base (list): value to be prepended to

        Returns:
            list: ``self.value + base``
        """
        return self.value + base

    def update(self, base):
        """Recursively merge dicts

        Args:
            base (dict): value to be merged into

        Returns:
            list: ``self.value + base``
        """
        return _values_merge(self.value, base or {})
