# -*- coding: utf-8 -*-
"""Declarative module configuration with dynamic value injection

Module Declaration
------------------

Modules declare their configuration via `init`. Here is how `pkdebug`
declares its config params:

    _cfg = pkconfig.init(
        control=(re.compile, None, 'Pattern to match against pkdc messages'),
        want_pid_time=(bool, False, 'Display pid and time in messages'),
        output=(_cfg_output, None, 'Where to write messages either as a "writable" or file name'),
    )

A param tuple contains three values:

    0. Default value, in the expected type
    1. Callable that can convert a string or the expected type into a value
    2. A docstring briefly explaining how the configuration works.

The returned ``_cfg`` object is ready to use after the call. It will contain
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
``$PYKERN_CHANNEL``. If not set, the channel will be ``dev``.

Config Mudules
--------------

Every application must have a module similar to `pykern.base_pykconfig`,
but named ``<root_pkg>.base_pyconfig``. This module holds the basic application
configuration for the different channels. It will be merged with instance
specific configuration contained in the two files ``~/.pykern_pyconfig.py``
and then ``~/.<root_pkg>_pyconfig.py`` if they exist. These modules are
imported without names to avoid cluttering the module namespace.

Configuration can be further refined in two ways. If the environment
variable ``$PYKERN_PKCONFIG_MODULE`` is defined, it will be read
like the dot files above and merged with the other rules, and the channel
function will be called so it's exactly the same structure.  If the
variable ``$<ROOT_PKG>_PKCONFIG_MODULE``, it will be read and merged
after the ``$PYKERN_PKCONFIG_MODULE``.

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

Configuration is returned as a three level dict. The values themselves could
be any Python object. In this case, we have a string and a file object for the two
parameters. We called `os.getcwd` and referred to `sys.stdout` in param values.

Param values can refer to other param values using `jinja2` values. Suppose there
was a value called ``run_dir``, and we wanted the ``db`` to be stored in that
directory. Here's what the config might look like:

    def dev():
        return {
            'my_app': {
                'flask_init': {
                    'run_dir': py.path.local().join('run'),
                    'db': 'sqlite://{{my_app.flask_init.run_dir}}/my_app.db',
                },
            },
        }

The value is run through `jinja2` (multiple times) until it is fully resolved
(no more jinja2 values). Values are converted to strings before they are passed
to jinja2, and only after all config values are merged.

Only string values are resolved with jinja2. Other objects are passed verbatim
to the parser.

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

# Very limited imports to avoid loops
from pykern import pkrunpy

#: Order of channels from least to most stable
CHANNELS = ('dev', 'alpha', 'beta', 'prod')

#: Instantiated channel
channel = CHANNELS[0]

#: Name of the module (required) for a package
BASE_MODULE = '{}.base_pkconfig'

#: Name of the file to load in user's home directory if exists
HOME_FILE = os.path.join('~', '.{}_pkconfig.py')

PYKERN_PACKAGE = 'pykern'

#: Module to declaration info mapping
_modules = collections.OrderedDict()

#: Validate identifer valid
_PARAM_RE = re.compile('^[a-z][a-z0-9_]*$')


#: Root package (may be pykern)
_root_pkg = None


#: Merged values
_merged = None


class _Merge(object):
    """Marks values with behavior ``op`` for merging

    Args:
        op (str): name of the method to perform operation
        value (any): object to be merged
    """
    def __init__(self, value):
        # All values go through this copy so we don't need to
        # do any other copies.
        self.value = copy.deepcopy(value)

    def __prepend(self, base):
        return self.value + base

    def __overwrite(self, base):
        return self.value

    def ___extend(self, base):
        return base + self.value



class Extend(_Merge):
    """Extend the previous list value with ``postfix``

    Example::

        'my_app.some_module': {
            'param1': {
                'key1': pkconfig.Extend([4, 5]),
            }),
        }

    Suppose the previous value of ``param1`` is::

        'param1': {
            'key1': [1, 2, 3],
            'key2': 'other value',
        }


    The result of `Extend` would be::

        'param1': {
            'key1': [1, 2, 3, 4, 5],
            'key2': 'other value',
        }

    Args:
        postfix (list): the value to append
    """
    def __init__(self, postfix):
        assert isinstance(postfix, list), \
            '{}: postfix must be a list'.format(postfix)
        return super(Extend, self).__init__(postfix)

    def _op(self, base):
        """Joins ``self.value`` and ``base``

        Args:
            base (list): value to be prepended to

        Returns:
            list: ``base + self.value``
        """
        return base + self.value



class Overwrite(_Merge):
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
    def __init(self, replacement):
        return super(Overwrite, self).__init__(replacement, 'overwrite')

    def _op(self, base):
        """Overwrites ``base`` with ``self.value``

        Args:
            base (object): ignored

        Returns:
            object: ``self.value``
        """
        return self.value


class Prepend(_Merge):
    """Insert ``prefix`` in the previous list value

    This is the default behavior for merging when the old
    and new values are both an instance of  `list`.

    Example::

        'my_app.some_module': {
            'param1': pkconfig.Prepend([1, 2]),
        }

    Suppose the previous value of ``param1`` is::

        'param1': pkconfig.Prepend([4, 5]),

    The result of `extend` would be::

        'param1': [1, 2, 4, 5],

    Args:
        prefix (list): the value to insert before old value
    """
    def __init(self, prefix):
        super(Prepend, self).__init__(prefix)

    def _op(self, base):
        return self.value + base


class Required(tuple, object):
    """Container for a required parameter declaration.

    Example::

        _cfg = pkconfig.init(
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


class Update(_Merge):
    """Update the previous dict value with ``to_merge`` (recursively).

    This is the default behavior for merging when the old
    and new values are both an instance of  `dict`.

    The merge is recursive. Recursion does not traverse non-dict
    elements or when an `overwrite` element is encountered.

    Example::

        'my_app.some_module': {
            'param1': pkconfig.Update({
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
    def __init__(self, to_merge):
        assert isinstance(value, dict), \
            '{}: new must be a dict'.format(to_merge)
        return super(Update, self).__init__(to_merge)

    def _op(self, base):
        """Recursively merge dicts

        Args:
            base (dict): value to be merged into

        Returns:
            list: ``self.value + base``
        """
        assert isinstance(base, dict), \
            '{}: base for update must be dict'.format(base)
        for nk in self.value:
            if nk in base:
                if type(base[nk]) == type(new[nk]) and isinstance(new[nk], (list, dict)):
                    op = Prepend if isinstance(new[nk], list) else Update
                    new[nk] = op(new[nk])

                if isinstance(new[nk], _Merge):
                    base[nk] = new[nk].op(base[nk])
                    continue
            base[nk] = new[nk]
        return (self.value, base or {})


def init(**kwargs):
    """Declares and initializes config params for calling module.

    Args:
        kwargs (dict): param name to (default, parser, docstring)

    Returns:
        Params: an empty object which will be populated with parameter values
    """
    caller = _Caller()
    decls = {}
    mn = caller.module.__name__
    _flatten_keys(mn.split('.'), kwargs, decls)
    for k in decls:
        decls[k] = _Declaration(decls[k])
    res = {}
    values = _values()
    return _iter_decls(mn.split('.'), kwargs, decls, values, res)


def _flatten_keys(key_parts, values, res):
    for k in values:
        v = values[k]
        kp = key_parts + k.split('.')
        ku = '_'.join(kp).upper()
        if isinstance(v, dict):
            _flatten_keys(kp, v, res)
        else:
            assert not ku in res, \
                '{}: duplicate key'.format('.'.join(kp))
            res[ku] = v


def _iter_decls(key_parts, kwargs, decls, values, res):
    for k in kwargs:
        #TODO(robnagler) deal with keys with '.' in them (not possible)
        kp = key_parts + k.split('.')
        ku = '_'.join(kp).upper()
        #TODO(robnagler) groups are not in decls, they don't have values, but
        # this is ok, I think.
        if not ku in decls:
            res[k] = {}
            _iter_decls(kp, kwargs[k], decls, values, res[k])
        else:
            d = decls[ku]
            if ku in values:
                v = values[ku]
                res[k] = None if v is None else d.parser(v)
            else:
                assert not d.required, \
                    '{}: config value missing and is required'.format(ku)
                res[k] = d.default
    return res

def _split_key(key):
    return re.split(r'[_\.]', key)


class _Caller(object):
    """Information about point of call of a declaration or value

    Attributes:
        filename (str): caller's file
        lineno (int): line in filename
        module (module): module defined by filename (may be __main__)
    """
    def __init__(self):
        try:
            frame = inspect.currentframe().f_back.f_back
            self.lineno = frame.f_lineno
            self.filename = frame.f_code.co_filename
            self.module = inspect.getmodule(frame)
        finally:
            frame = None


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
            assert hasattr(value[1], '__call__'), \
                '{}: parser must be a callable ({}.{})'.format(value[0], name)
            self.default = value[0]
            self.parser = value[1]
            self.docstring = value[2]
            self.group = None
            self.required = isinstance(value, Required)


def set_root_package(root_pkg):
    """Called by entry point moodules only to set the root_pkg

    If root_pkg is already set, will assert value to make sure not different
    else it will exit.
    """
    global _root_pkg
    if _root_pkg:
        assert _root_pkg in (PYKERN_PACKAGE, root_pkg), \
            '{}: root_pkg different from already set value ({})'.format(
                root_pkg, _root_pkg)
    _root_pkg = root_pkg


def _values():
    """Coallesce pkconfig_defaults, file(s), and environ vars.

    Args:
        root_pkg (str): package to start with.
    """
    global channel
    # Use current channel as the default in case called twice
    c = os.getenv('PYKERN_CHANNEL', channel)
    assert c in CHANNELS, \
        '{}: invalid $PYKERN_CHANNEL; must be {}'.format(c, CHANNELS)
    channel = c
    pkgs =  [_root_pkg]
    if _root_pkg != PYKERN_PACKAGE:
        pkgs.append(PYKERN_PACKAGE)
    values = {}
    for p in pkgs:
        # Packages must have this module always, even if empty
        m = importlib.import_module(BASE_MODULE.format(p))
        # Need all entry points?
        _values_flatten(values, getattr(m, channel)())
    for p in pkgs:
        fname = os.path.expanduser(HOME_FILE.format(p))
        # The module itself may throw an exception so can't use try, because
        # interpretation of the exception doesn't make sense. It would be
        # better if run_path() returned a special exception when the file
        # does not exist.
        if os.path.isfile(fname):
            m = pkrunpy.run_path_as_module(fname)
            _values_flatten(values, getattr(m, channel)())
    fname = os.getenv('PYKERN_PKCONFIG_FILE', None)
    if fname:
        m = pkrunpy.run_path_as_module(fname)
        _values_flatten(values, getattr(m, channel)())
    # Bring in all environ values
    _values_flatten(values, os.environ)
    return values


def _values_flatten(base, new):
    new_values = {}
    _flatten_keys([], new, new_values)
    base.update(new_values)


def _values_merge(base, new):
    for nk in new:
        n = new[nk]
        if nk in base:
            b = base[nk]
            if type(b) == type(n):
                if isinstance(b, list):
                    b = n + b
                elif isinstance(b, dict):
                    _values_merge(b, n)
                else:
                    b = n
            else:
                b = n
        else:
            b = n
        base[nk] = b


'''
        @staticmethod
        def __jinja(v, k):
            je = jinja2.Environment(
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True,
            )
            for f in range(10):
                new_v = je.from_string(v).render(_merged)
                if new_v == v:
                    return new_v
            raise AssertionError('{}: recursion too deep for param ({})'.format(v, k))

def inject_params(values):
    """Update `Params` with pkconfig dict

    Must be called before affected modules. Typically used only for tests.
    For other purposes, environment variables are preferred.

    Example::

        import pkconfig
        pkconfig.inject_params({
            'pykern': {
                'pkdebug': {
                    'control': 'some control',
                },
            },
        })

        # The module to be tested
        import pkdebug

    Args:
        values (dict): hierarchy of packages and config names
    """
    pass

'''
