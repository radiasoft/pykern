# -*- coding: utf-8 -*-
"""Declarative module configuration with dynamic value injection

Module Declaration
------------------

Modules declare their configuration via `init`. Here is how `pkdebug`
declares its config params:

    cfg = pkconfig.init(
        control=(None, re.compile, 'Pattern to match against pkdc messages'),
        want_pid_time=(False, bool, 'Display pid and time in messages'),
        output=(None, _cfg_output, 'Where to write messages either as a "writable" or file name'),
    )

A param tuple contains three values:

    0. Default value, in the expected type
    1. Callable that can convert a string or the expected type into a value
    2. A docstring briefly explaining the configuration element

The returned ``cfg`` object is ready to use after the call. It will contain
the config params as defined or an exception will be raised.

Channel Files
-------------

Configuration files are python modules, which define functions for each channel
to be configured. A channel is a stage of deployment. There are four channels:

    dev
        This is the default channel. It's what developers use to configure
        their systems.

    alpha
        The first stage of a deployment. The configuration supports automated
        testing. Customer data is stored on alpha systems.

    beta
        First stage of customer use. The configuration supports both test
        and real users. Since there is customer data, encryption keys
        should be something randomly generated.

    prod
        Production systems contain customer data so they should be
        configured for backups, privacy, and scaling.

The name of the channel is specified by the environment variable
``$PYKERN_PKCONFIG_CHANNEL``. If not set, the channel will be ``dev``.

Config Modules
--------------

Every application must have a module similar to `pykern.base_pykconfig`,
but named ``<root_pkg>.base_pyconfig``. This module holds the basic application
configuration for the different channels. It will be merged with instance
specific configuration contained in the two files ``~/.pykern_pyconfig.py``
and then ``~/.<root_pkg>_pyconfig.py`` if they exist. These modules are
imported without names to avoid cluttering the module namespace.

Configuration can be further refined in two ways. If the environment
variable ``$PYKERN_PKCONFIG_FILE`` is defined, it will be read
like the dot files above and merged with the other rules, and the channel
function will be called so it's exactly the same structure.  If the
variable ``$<ROOT_PKG>_PKCONFIG_FILE``, it will be read and merged
after the ``$PYKERN_PKCONFIG_FILE``.

One last level of configuration is environment variables for individual
parameters. If an environment variable exists that matches the upper
case, underscored parameter name, it will override all other values.
This is typically used for debugging or passing values into a docker
container. For example, you can set ``$PYKERN_PKDEBUG_OUTPUT`` to
``/dev/tty`` if you want debugging output to go to the terminal instead
of stderr.

Config Params
-------------

The values of parameters in config files are specified in nested
dictionaries. The channel function must return a type level dictionary
with the package roots as the first keys, then the submodules, and
which then point to parameters.

Suppose we have ``my_app`` that uses Flask and wants pkdebug to stdout
in development. Here's what ``my_app/base_pkcoonfig.py`` might contain::

    import os
    import sys

    def dev():
        return {
            'my_app': {
                'flask_init': {
                    'db': 'sqlite://' + os.getcwd() + '/my_app.db',
                },
            },
            'pykern': {
                'pkdebug': {
                    'output': sys.stdout,
                },
            },
        }

Configuration is returned as nested dicts. The values themselves could
be any Python object. In this case, we have a string and a file object for the two
parameters. We called `os.getcwd` and referred to `sys.stdout` in param values.

Param values can refer to other param values using `format` values. Suppose there
was a value called ``run_dir``, and we wanted the ``db`` to be stored in that
directory. Here's what the config might look like:

    def dev():
        return {
            'my_app': {
                'flask_init': {
                    'run_dir': py.path.local().join('run'),
                    'db': 'sqlite://{MY_APP_FLASK_INIT_RUN_DIR}/my_app.db',
                },
            },
        }

The value is run through `str.format` until the value stops
changing. All `os.environ` values can be referenced here as well.
Only string values are resolved with `str.format`. Other objects are
passed verbatim to the parser.

Summary
-------

Here are the steps to configuring the system.

1. When the first module calls `init` or `inject_params`, pkconfig
   reads all module config and environment variables to create a
   single dict of param values, unparsed, by calling `merge` repeatedly.

2. `init` looks for the module's params by indexing with (root_pkg, submodule, param)
   in the merged config.

3. If the parameter is found, that value is used. Else, the default is merged
   into the dict and used.

4. The parameter value is then resolved with jinja2.

5. The resolved value is parsed using the param's declared ``parser``.

6. The result is stored in the merged config and also stored in the module's
   `Params` object .

7. Once all params have been parsed for the module, `init` returns the `Params`
   object to the module, which can then use those params to initialize itself.


:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

# Import the minimum number of modules and none from pykern
# pkconfig is the first module imported by all other modules in pykern
import collections
import copy
import importlib
import inspect
import os
import re
import six

# These modules have very limited imports to avoid loops
from pykern import pkcollections
from pykern import pkinspect
from pykern import pkrunpy

#: Name of the module (required) for a package
BASE_MODULE = '{}.base_pkconfig'

#: Name of the file to load in user's home directory if exists
HOME_FILE = os.path.join('~', '.{}_pkconfig.py')

#: Validate key: Cannot begin with non-letter or end with an underscore
KEY_RE = re.compile('^[a-z][a-z0-9_]*[a-z0-9]$', flags=re.IGNORECASE)

#: Root package implicit
PYKERN_PACKAGE = 'pykern'

#: Environment variable holding the search path
SEARCH_PATH_ENV_NAME = 'PYKERN_PKCONFIG_SEARCH_PATH'

#: Order of channels from least to most stable
VALID_CHANNELS = ('dev', 'alpha', 'beta', 'prod')

#: Instantiated channel
channel = None

#: Where to search for packages
_search_path = [PYKERN_PACKAGE]

#: All values in _search_path coalesced
_values = None

class DoNotFormat(str, object):
    """Container for string values, which should not be formatted

    Example::

        def dev():
            return {
                'pkg': {
                    'module': {
                        'cfg1': pkconfig.DoNotFormat('eg. a jinja {{template}}'),
                        'cfg2': 'This string will be formatted',
                    },
                },
            }
    """
    def __format__(self, *args, **kwargs):
        raise AssertionError(
            '{}: you cannot refer to this formatted value'.format(str(self)))


class Required(tuple, object):
    """Container for a required parameter declaration.

    Example::

        cfg = pkconfig.init(
            any_param=(1, int, 'A parameter with a default'),
            needed=pkconfig.Required(int, 'A parameter with a default'),
        )

    Args:
        converter (callable): how to string to internal value
        docstring (str): description of parameter
    """
    @staticmethod
    def __new__(cls, *args):
        assert len(args) == 2, \
            '{}: incorrect number of args'.format(args)
        return super(Required, cls).__new__(cls, (None,) + args)


def init(**kwargs):
    """Declares and initializes config params for calling module.

    Args:
        kwargs (dict): param name to (default, parser, docstring)

    Returns:
        Params: an empty object which will be populated with parameter values
    """
    m = pkinspect.caller_module()
    assert pkinspect.root_package(m) in _search_path, \
        '{}: module root not in search_path ({})'.format(m.__name__, _search_path)
    mnp = m.__name__.split('.')
    for k in reversed(mnp):
        kwargs = {k: kwargs}
    decls = {}
    _flatten_keys([], kwargs, decls)
    values = _coalesce_values()
    res = pkcollections.OrderedMapping()
    _iter_decls(decls, values, res)
    for k in mnp:
        res = res[k]
    return res


def insert_search_path(search_path):
    """Called by entry point modules to insert into the search path.

    If root_pkg is already set, will assert value to make sure not different
    else it will exit.
    """
    global _search_path
    if not search_path:
        return
    if isinstance(search_path, six.string_types):
        search_path = search_path.split(':')
    for p in reversed(search_path):
        if not p in _search_path:
            _search_path.insert(0, p)


class _Declaration(object):
    """Initialize a single parameter declaration

    Args:
        name (str): for error output
        value (tuple or dict): specification for parameter

    Attributes:
        default (object): value to be assigned if not explicitly configured
        docstring (str): documentation for the parameter
        group (Group): None or Group instance
        parser (callable): how to parse a configured value
        required (bool): the param must be explicitly configured
    """
    def __init__(self, value):
        if isinstance(value, dict):
            self.group = value
            self.parser = None
            self.default = None
            self.docstring = ''
            #TODO(robnagler) _group_has_required(value)
            self.required = False
        else:
            assert len(value) == 3, \
                '{}: declaration must be a 3-tuple ({}.{})'.format(value, name)
            self.default = value[0]
            self.parser = value[1]
            self.docstring = value[2]
            assert callable(self.parser), \
                '{}: parser must be a callable ({}.{})'.format(self.parser, name)
            self.group = None
            self.required = isinstance(value, Required)


class _Key(str, object):
    @staticmethod
    def __new__(cls, value, parts):
        self = super(_Key, cls).__new__(cls, value)
        self.parts = parts
        self.lc = '.'.join(parts)
        return self


def _clean_environ():
    res = {}
    for k in os.environ:
        if KEY_RE.match(k):
            res[k] = os.environ[k] if len(os.environ[k]) > 0 else None
    return res


def _coalesce_values():
    """Coallesce pkconfig_defaults, file(s), and environ vars.

    Args:
        root_pkg (str): package to start with.
    """
    global _values
    if _values:
        return _values
    global channel
    #TODO(robnagler) sufficient to set package and rely on HOME_FILE?
    insert_search_path(os.getenv(SEARCH_PATH_ENV_NAME, None))
    # Use current channel as the default in case called twice
    #TODO(robnagler) channel comes from file or environ
    #TODO(robnagler) import all modules then evaluate values
    #  code may initialize channel or search path
    #TODO(robnagler) insert_search_path needs to be allowed in modules so
    #  reread path after each file/module load
    #TODO(robnagler) cache _values(), because need to be consistent
    c = os.getenv('PYKERN_PKCONFIG_CHANNEL', VALID_CHANNELS[0])
    assert c in VALID_CHANNELS, \
        '{}: invalid $PYKERN_PKCONFIG_CHANNEL; must be {}'.format(c, VALID_CHANNELS)
    channel = c
    values = {}
    for p in _search_path:
        # Packages must have this module always, even if empty
        m = importlib.import_module(BASE_MODULE.format(p))
        _values_flatten(values, getattr(m, channel)())
    for p in _search_path:
        fname = os.path.expanduser(HOME_FILE.format(p))
        # The module itself may throw an exception so can't use try, because
        # interpretation of the exception doesn't make sense. It would be
        # better if run_path() returned a special exception when the file
        # does not exist.
        if os.path.isfile(fname):
            m = pkrunpy.run_path_as_module(fname)
            _values_flatten(values, getattr(m, channel)())
    if fname:
        m = pkrunpy.run_path_as_module(fname)
        _values_flatten(values, getattr(m, channel)())
    _values_flatten(values, _clean_environ())
    _values = values
    return values


def _flatten_keys(key_parts, values, res):
    for k in values:
        v = values[k]
        kp = key_parts + k.split('.')
        ku = '_'.join(kp).upper()
        #: Validate identifer valid
        k = _Key(ku, kp)
        assert KEY_RE.search(ku), \
            '{}: invalid key must match {}'.format(k.lc, KEY_RE)
        assert not k in res, \
            '{}: duplicate key'.format(k.lc)
        if isinstance(v, dict):
            _flatten_keys(kp, v, res)
        else:
            # Only store leaves
            res[k] = v


def _iter_decls(decls, values, res):
    for k in sorted(decls.keys()):
        #TODO(robnagler) deal with keys with '.' in them (not possible)
        d = _Declaration(decls[k])
        r = res
        for kp in k.parts[:-1]:
            if kp not in r:
                r[kp] = pkcollections.OrderedMapping()
            r = r[kp]
        kp = k.parts[-1]
        if d.group:
            r[kp] = pkcollections.OrderedMapping()
            continue
        r[kp] = _resolver(d)(k, d, values)
        values[k] = r[kp]


def _resolver(decl):
    if dict == decl.parser:
        return _resolve_dict
    if list == decl.parser:
        return _resolve_list
    return _resolve_value


def _resolve_dict(key, decl, values):
    #TODO(robnagler) assert required
    res = pkcollections.OrderedMapping(
        copy.deepcopy(decl.default) if decl.default else {})
    assert isinstance(res, (dict, pkcollections.OrderedMapping)), \
        '{}: default ({}) must be a dict'.format(key.lc, decl.default)
    key_prefix = key + '_'
    for k in reversed(sorted(values.keys())):
        if k != key and not k.startswith(key_prefix):
            continue
        r = res
        if len(k.parts) == 1:
            # os.environ has only one part (no way to split on '.')
            # so we have to assign the key's suffix manually
            r[k.parts[0][len(key_prefix):]] = values[k]
            print(r)
        else:
            kp = k.parts[len(key.parts):-1]
            for k2 in kp:
                if not k2 in r:
                    r[k2] = pkcollections.OrderedMapping()
                else:
                    assert isinstance(r[k2], (dict, pkcollections.OrderedMapping)), \
                        '{}: type collision on existing non-dict ({}={})'.format(
                            k.lc, k2, r[k2])
                r = r[k2]
            r[k.parts[-1]] = values[k]
    return res


def _resolve_list(key, decl, values):
    #TODO(robnagler) assert required
    res = copy.deepcopy(decl.default) if decl.default else []
    assert isinstance(res, list), \
        '{}: default ({}) must be a list'.format(key.lc, decl.default)
    if key not in values:
        assert not decl.required, \
            '{}: config value missing and is required'.format(k)
        return res
    if not isinstance(values[key], list):
        if values[key] is None:
            return None
        raise AssertionError(
            '{}: value ({}) must be a list or None'.format(key.lc, values[key]))
    return values[key] + res


def _resolve_value(key, decl, values):
    if key in values:
        res = values[key]
    else:
        assert not decl.required, \
            '{}: config value missing and is required'.format(key.lc)
        res = decl.default
    seen = {}
    #TODO(robnagler) this fails when a DoNotFormat is formatted by
    while isinstance(res, six.string_types) \
        and not res in seen \
        and not isinstance(res, DoNotFormat):
        seen[res] = 1
        res = res.format(**values)
    if res is None:
        return None
    return decl.parser(res)


def _values_flatten(base, new):
    new_values = {}
    _flatten_keys([], new, new_values)
    #TODO(robnagler) Verify that a value x_y_z isn't set when x_y
    # exists already as a None. The other way is ok, because it
    # clears the value unless of course it's not a dict
    # then it would be a type collision
    for k in sorted(new_values.keys()):
        n = new_values[k]
        if k in base:
            b = base[k]
            if isinstance(b, list) or isinstance(n, list):
                if b is None or n is None:
                    pass
                elif isinstance(b, list) and isinstance(n, list):
                    n = n + b
                else:
                    raise AssertionError(
                        '{}: type mismatch between new value ({}) and base ({})'.format(
                            k.lc, n, b))
        base[k] = n
