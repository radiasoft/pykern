# -*- coding: utf-8 -*-
"""Configuration of PyKern and clients

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

# Import the minimum number of modules and none from pykern
# pkconfig is the first module imported by all other modules in pykern
import collections
import re

#: Module to declaration info mapping
_info = collections.OrderedDict()

#: Validate identifer valid
_PARAM_RE = re.compile('^[a-z][a-z0-9_]*$')


def init_all_modules():
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
    pass


def inject_values(values):
    """Update `Params` with pkconfig dictionary.

    `init_all_modules` will be called on all modules so that modules can
    reinitialize.

    Args:
        values (dict): hierarchy of packages and config names
    """
    pass


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
    try:
        frame = inspect.currentframe().f_back
        module = inspect.getmodule(frame)
    finally:
        frame = None
    d = {}
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
    _info[module.__name__] = {
        'module': module,
        'params': p,
        'decls': d,
    }
    return p


class Params(object):
    """Container for parameter values.

    Attributes are the names of the parameters
    """
    pass
