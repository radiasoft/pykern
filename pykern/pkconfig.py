# -*- coding: utf-8 -*-
"""Declarative module configuration with dynamic value injection

Module Declaration
------------------

Modules declare their configuration via `init`. Here is how `pkdebug`
declares its config params::

    cfg = pkconfig.init(
        control=(None, re.compile, 'Pattern to match against pkdc messages'),
        want_pid_time=(False, bool, 'Display pid and time in messages'),
        output=(None, _cfg_output, 'Where to write messages either as a "writable" or file name'),
    )

A param tuple contains three values:

    0. Default value, in the expected type
    1. Callable that can convert a string or other type into a valid value
    2. A docstring briefly explaining the configuration element

The returned ``cfg`` object is ready to use after the call. It will contain
the config params as defined or an exception will be raised.

Config Values
-------------

Configuration is returned as nested dicts. The values themselves could
be any Python object. In this case, we have a string and a file object
for the two parameters. We called `os.getcwd` and referred to
`sys.stdout` in param values.

Summary
-------

Here are the steps to configuring an application:

1. When the first module calls `init`, pkconfig gets environment variables
   to create a single dict of param values, unparsed.

2. `init` looks for the module's params in the unparsed values.

3. If the parameter is found, that value is used. Else, the default is merged
   into the dict and used.

4. The parameter value is then resolved with `str.format`. If the value
   is a `list` it will be joined with any previous value (e.g. default).

5. The resolved value is parsed using the param's declared ``parser``.

6. The result is stored in the merged config and also stored in the module's
   `Params` object .

7. Once all params have been parsed for the module, `init` returns the `Params`
   object to the module, which can then use those params to initialize itself.

:copyright: Copyright (c) 2015-2019 RadiaSoft LLC.  All Rights Reserved.
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
import sys

# These modules have very limited imports to avoid loops with config imports
from pykern.pkcollections import PKDict
from pykern import pkconst
from pykern import pkinspect

#: Python version independent value of string instance check
STRING_TYPES = pkconst.STRING_TYPES

#: Environment variable holding channel (defaults to "dev")
CHANNEL_ATTR = "pykern_pkconfig_channel"

_KEY_PATTERN = "^[A-Z][A-Z0-9_]*[A-Z0-9]$"

#: Validate environ key: Must be upper case, cannot begin with non-letter or end with an underscore
_ENV_KEY_RE = re.compile(_KEY_PATTERN)

#: Validate key: Cannot begin with non-letter or end with an underscore
KEY_RE = re.compile(_KEY_PATTERN, flags=re.IGNORECASE)

#: parse_tuple splits strings on this
TUPLE_SEP = ":"

#: Order of channels from least to most stable
VALID_CHANNELS = ("dev", "alpha", "beta", "prod")

#: Channels which can have more verbose output from the server
INTERNAL_TEST_CHANNELS = VALID_CHANNELS[0:2]

#: Configuration for this module: channel
cfg = None

#: Initialized channel (same as cfg.channel)
CHANNEL_DEFAULT = VALID_CHANNELS[0]

#: Attribute to detect parser which can parse None
_PARSE_NONE_ATTR = "pykern_pkconfig_parse_none"

#: Value to add to os.environ (see `reset_state_for_testing`)
_add_to_environ = None

#: All values in environ and add_to_environ
_raw_values = None

#: All values parsed via init()
_parsed_values = None

#: Regex used by `parse_seconds`
_PARSE_SECONDS = re.compile(
    r"^(?:(\d+)d)?(?:(?:(?:(\d+):)?(\d+):)?(\d+))?$",
    flags=re.IGNORECASE,
)

#: Regex used by `parse_bytes`
_PARSE_BYTES = re.compile(r"^(\d+)([kmgtp]?)b?$", flags=re.IGNORECASE)

#: multiplier used for qualifier on `parse_bytes`
_PARSE_BYTES_MULTIPLIER = PKDict(
    k=1024,
    m=1024**2,
    g=1024**3,
    t=1024**4,
)


class ReplacedBy(tuple, object):
    """Container for a required parameter declaration.

    Example::

        cfg = pkconfig.init(
            gone=pkconfig.ReplacedBy('pykern.pkexample.foo'),
        )

    Args:
        new_name: name of new config parameter
    """

    @staticmethod
    def __new__(cls, new_name):
        msg = "replaced by name=${}".format(new_name.upper().replace(".", "_"))
        return super(ReplacedBy, cls).__new__(
            cls,
            (None, lambda x: raise_error(msg), msg),
        )


class Required(tuple, object):
    """Container for a required parameter declaration.

    Example::

        cfg = pkconfig.init(
            any_param=(1, int, 'A parameter with a default'),
            needed=pkconfig.Required(int, 'A parameter without a default'),
        )

    Args:
        converter (callable): how to string to internal value
        docstring (str): description of parameter
    """

    @staticmethod
    def __new__(cls, *args):
        assert len(args) == 2, "{}: len(args)!=2".format(args)
        return super(Required, cls).__new__(cls, (None,) + args)


class RequiredUnlessDev(tuple, object):
    """Container for a required parameter declaration only `in_dev_mode`.

    Only required if `in_dev_mode` is true.

    Example::

        cfg = pkconfig.init(
            maybe_needed=pkconfig.RequiredUnlessDev('dev default', str, 'A parameter with a default'),
        )

    Args:
        dev_default (object): value compatible with type
        converter (callable): how to string to internal value
        docstring (str): description of parameter
    """

    @staticmethod
    def __new__(cls, *args):
        assert len(args) == 3, "{}: len(args)!=3".format(args)
        if in_dev_mode():
            return args
        return Required(args[1], args[2])


def append_load_path(load_path):
    """DEPRECATED"""
    pass


def channel_in(*args, **kwargs):
    """Test against configured channel

    Args:
        args (str): list of channels to valid
        channel (str): channel to test (default: [cfg.channel])

    Returns:
        bool: True if current channel in ``args``
    """
    if not cfg:
        _coalesce_values()
    res = False
    to_test = cfg.channel
    if kwargs and kwargs["channel"]:
        to_test = kwargs["channel"]
        assert to_test in VALID_CHANNELS, "{}: invalid channel keyword arg".format(
            to_test
        )
    for a in args:
        assert a in VALID_CHANNELS, "{}: invalid channel to test".format(a)
        if a == to_test:
            res = True
    return res


def channel_in_internal_test(channel=None):
    """Is this a internal test channel?

    Args:
        channel (str): channel to test (default: [cfg.channel])

    Returns:
        bool: True if current channel in (alpha, dev)
    """
    return channel_in(*INTERNAL_TEST_CHANNELS, channel=channel)


def init(**kwargs):
    """Declares and initializes config params for calling module.

    Args:
        kwargs (dict): param name to (default, parser, docstring)

    Returns:
        Params: `PKDict` populated with param values
    """
    if "_caller_module" in kwargs:
        # Internal use only: _values() calls init() to initialize pkconfig.cfg
        m = kwargs["_caller_module"]
        del kwargs["_caller_module"]
    else:
        if pkinspect.is_caller_main():
            pkconst.builtin_print(
                "pkconfig.init() called from __main__; cannot configure, ignoring",
                file=sys.stderr,
            )
            return None
        m = pkinspect.caller_module()
    mnp = m.__name__.split(".")
    for k in reversed(mnp):
        kwargs = {k: kwargs}
    decls = {}
    _flatten_keys([], kwargs, decls)
    _coalesce_values()
    res = PKDict()
    _iter_decls(decls, res)
    for k in mnp:
        res = res[k]
    return res


def in_dev_mode():
    """Turn on developer features

    Returns:
        bool: value of `pykern.pykern.cfg.dev_mode`

    """
    if not cfg:
        _coalesce_values()
    return cfg.dev_mode


def flatten_values(base, new):
    """Merge flattened values into base

    Keys are made all lowercase.

    Lists instances are prepended and not recursively merged.

    Args:
        base (object): dict-like that is already flattened
        new (object): dict-like that will be flattened and overriden
    Returns:
        dict: modified `base`
    """
    new_values = {}
    _flatten_keys([], new, new_values)
    # TODO(robnagler) Verify that a value x_y_z isn't set when x_y
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
                    n.extend(b)
                else:
                    raise_error(
                        "{}: type mismatch between new value ({}) and base ({})".format(
                            k.msg, n, b
                        ),
                    )
        base[k] = n
    return base


def parse_none(func):
    """Decorator for a parser which can parse None

    Args:
        callable: function to be decorated

    Returns:
        callable: func with attr indicating it can parse None
    """
    setattr(func, _PARSE_NONE_ATTR, True)
    return func


@parse_none
def parse_bool(value):
    """Default parser for `bool` types

    When the parser is `bool`, it will be replaced with this routine,
    which parses strings and None specially. `bool` values
    cannot be defaulted to `None`. They must be True or False.

    String values which return true: t, true, y, yes, 1.

    False values: f, false, n, no, 0, '', None

    Other values are parsed by `bool`.

    Args:
        value (object): to be parsed

    Returns:
        bool: True or False
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if not isinstance(value, STRING_TYPES):
        return bool(value)
    v = value.lower()
    if v in ("t", "true", "y", "yes", "1"):
        return True
    if v in ("f", "false", "n", "no", "0", ""):
        return False
    raise_error("unknown boolean value={}".format(value))


def parse_bytes(value):
    """Parse bytes in `int` or n[KMGT]B? formats

    Args:
        value (object): to be parsed

    Returns:
        int: non-negative number of bytes
    """
    if isinstance(value, int):
        if value < 0:
            raise_error("bytes may not be negative value={}".format(value))
        return value
    if not isinstance(value, str):
        raise_error("bytes must be int or str value={}".format(value))
    m = _PARSE_BYTES.search(value)
    if not m:
        raise_error("bytes must match n[KMGT]B? value={}".format(value))
    v = int(m.group(1))
    x = m.group(2)
    if x:
        v *= _PARSE_BYTES_MULTIPLIER[x.lower()]
    return v


def parse_positive_int(value):
    """Parse is a positive integer

    Args:
        value (object): to be parsed

    Returns:
        int: positive value
    """
    if isinstance(value, str):
        try:
            value = int(value)
        except Exception as e:
            raise_error(f"value={value} not an integer; exception={e}")
    elif not isinstance(value, int):
        raise_error(f"value={value} must be int or str")
    if value <= 0:
        raise_error(f"value={value} must be positive")
    return value


def parse_seconds(value):
    """Parse seconds in `int` or DdH:M:S formats

    Args:
        value (object): to be parsed

    Returns:
        int: non-negative number of seconds
    """
    if isinstance(value, int):
        if value < 0:
            raise_error(f"seconds may not be negative value={value}")
        return value
    if not isinstance(value, str):
        raise_error(f"seconds must be int or str value={value}")
    m = _PARSE_SECONDS.search(value)
    if not m or not any(m.groups()):
        raise_error(f"seconds must match [Dd][[[H:]M:]S] value={value}")
    v = 0
    for x, i in zip((86400, 3600, 60, 1), m.groups()):
        if i is not None:
            v += int(i) * x
    return v


#: deprecated version of parse_seconds
parse_secs = parse_seconds


@parse_none
def parse_set(value):
    """Default parser for `set` and `frozenset` types

    When the parser is `set` or `frozenset`, it will be replaced with this routine,
    which parses strings, lists, and sets. It splits strings on ':'.

    Args:
        value (object): to be parsed

    Returns:
        frozenset: may be an empty set
    """
    return frozenset(parse_tuple(value))


@parse_none
def parse_tuple(value):
    """Default parser for `tuple` types

    When the parser is `tuple`, it will be replaced with this routine,
    which parses strings, lists, sets, and tuples. It splits strings on ':'.

    Args:
        value (object): to be parsed

    Returns:
        tuple: may be an empty tuple

    """
    if value is None:
        return tuple()
    if isinstance(value, tuple):
        return value
    if isinstance(value, (list, set, frozenset)):
        return tuple(value)
    assert isinstance(
        value, STRING_TYPES
    ), "unable to convert type={} to tuple; value={}".format(type(value), value)
    return tuple(value.split(TUPLE_SEP))


def raise_error(msg):
    """Call when there is a config problem"""
    raise AssertionError(msg)


def reset_state_for_testing(add_to_environ=None):
    """Clear the raw values and append add_to_environ

    Only used for unit tests. ``add_to_environ`` overrides previous
    value.

    Args:
        add_to_environ (dict): values to augment to os.environ
    """
    global _raw_values, _add_to_environ
    _raw_values = None
    _add_to_environ = copy.deepcopy(add_to_environ)


def to_environ(cfg_keys, values=None, exclude_re=None):
    """Export config (key, values) as dict for environ

    cfg_keys is a list of dotted words (``['pykern.pkdebug.control']``).

    Simple globs (``pykern.pkdebug.*``) are supported, which match
    any word character. This can be used to ensure there is enough depth,
    e.g. pykern.*.* means there must be at least two undercores in
    the environment variable.

    Only environ and add_to_environ config will be considered, not
    default values, which will be assumed to be processed the same
    way in a subprocess using this environ.

    Args:
        cfg_keys (iter): keys to find values for
        values (mapping): use for configuration to parse [actual config]
        exclude_re (object): compile re or str to ignore matches
    Returns:
        PKDict: keys and values (str)
    """
    c = flatten_values({}, values) if values else _coalesce_values()
    res = PKDict()

    if exclude_re and isinstance(exclude_re, STRING_TYPES):
        exclude_re = re.compile(exclude_re, flags=re.IGNORECASE)

    def a(k, v):
        if exclude_re and exclude_re.search(k):
            return
        if not isinstance(v, STRING_TYPES):
            if v is None:
                v = ""
            elif isinstance(v, bool):
                v = "1" if v else ""
            elif isinstance(v, (frozenset, list, set, tuple)):
                v = TUPLE_SEP.join(v)
            else:
                v = str(v)
        res[k.upper()] = v

    for k in cfg_keys:
        k = k.lower().replace(".", "_")
        if "*" not in k:
            if k in c:
                a(k, c[k])
            continue
        r = re.compile(k.replace("*", r"\w+"), flags=re.IGNORECASE)
        for x, v in c.items():
            if r.search(x):
                a(x, v)
    return res


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
            self.docstring = ""
            # TODO(robnagler) _group_has_required(value)
            self.required = False
            return
        assert len(value) == 3, "{}: declaration must be a 3-tuple".format(value)
        self.default = value[0]
        self.parser = value[1]
        self.docstring = value[2]
        assert callable(self.parser), "{}: parser must be a callable: ".format(
            self.parser, self.docstring
        )
        self.group = None
        self.required = isinstance(value, Required)
        self._fixup_parser()

    def _fixup_parser(self):
        if self.parser == bool:
            t = (int,)
            self.parser = parse_bool
        elif self.parser == tuple:
            t = (tuple,)
            self.parser = parse_tuple
        elif self.parser in (set, frozenset):
            t = (frozenset, set, tuple)
            self.parser = parse_set
        else:
            return
        if self.required:
            return
        # better error message than what parser might put out
        assert isinstance(
            self.default, t
        ), "default={} must be a type={} docstring={}".format(
            self.default,
            [str(x) for x in t],
            self.docstring,
        )
        # validate the default
        self.default = self.parser(self.default)


class _Key(str, object):
    """Internal representation of a key for a value

    The str value is lowercase joined with ``_``. For debugging,
    ``msg`` is printed (original case, joined on '.'). The parts
    are saved for creating nested values.
    """

    @staticmethod
    def __new__(cls, parts):
        self = super(_Key, cls).__new__(cls, "_".join(parts).lower())
        self.parts = parts
        self.msg = ".".join(parts)
        return self


def _clean_environ():
    """Ensure os.environ keys are valid (no bash function names)

    Also sets empty string to `None`.

    Returns:
        dict: copy of a cleaned up `os.environ`
    """

    def _value(env, k):
        return env[k] if len(env[k]) > 0 else None

    def _add_others(env, res):
        for k in sorted(env.keys()):
            if KEY_RE.search(k):
                x = k.upper()
                if x not in res:
                    res[x] = _value(env, k)

    def _add_uppers(env, res):
        for k in sorted(env.keys()):
            if _ENV_KEY_RE.search(k):
                res[k] = _value(env, k)
                del env[k]

    res = {}
    env = os.environ.copy()
    # TODO(robnagler) this makes it easier to set debugging, but it's a hack
    if "pkdebug" in env and "PYKERN_PKDEBUG_CONTROL" not in env:
        env["PYKERN_PKDEBUG_CONTROL"] = env["pkdebug"]
    if _add_to_environ:
        env.update(_add_to_environ)
    _add_uppers(env, res)
    _add_others(env, res)
    return res


def _coalesce_values():
    """Coalesce environ and add_to_environ

    Sets up channel.

    Returns:
        dict: raw values
    """
    global _raw_values, _parsed_values
    global cfg
    if _raw_values:
        return _raw_values
    values = {}
    env = _clean_environ()
    flatten_values(values, env)
    channel = values.get(CHANNEL_ATTR, CHANNEL_DEFAULT)
    assert channel in VALID_CHANNELS, "{}: invalid ${}; must be {}".format(
        channel, CHANNEL_ATTR.upper(), VALID_CHANNELS
    )
    values[CHANNEL_ATTR] = channel
    _raw_values = values
    _parsed_values = dict(((_Key([k]), v) for k, v in env.items()))
    a = PKDict(
        _caller_module=sys.modules[__name__],
        channel=Required(str, "which (stage) function returns config"),
    )
    cfg = init(**a)
    a.dev_mode = (channel_in("dev"), bool, "controls development features")
    cfg = init(**a)
    return _raw_values


def _flatten_keys(key_parts, values, res):
    """Turns values into non-nested dict with `_Key` keys, flat

    Args:
        key_parts (list): call with ``[]``
        values (dict): nested dicts of config values
        res (dict): result container (call with ``{}``)
    """
    for k in values:
        v = values[k]
        k = _Key(key_parts + k.split("."))
        assert KEY_RE.search(k), "{}: invalid key must match {}".format(k.msg, KEY_RE)
        assert not k in res, "{}: duplicate key".format(k.msg)
        if isinstance(v, dict):
            _flatten_keys(k.parts, v, res)
        else:
            # Only store leaves
            res[k] = v


def _iter_decls(decls, res):
    """Iterates decls and resolves values into res

    Args:
        decls (dict): nested dictionary of a module's cfg values
        res (PKDict): result configuration for module
    """
    for k in sorted(decls.keys()):
        # TODO(robnagler) deal with keys with '.' in them (not possible?)
        d = _Declaration(decls[k])
        r = res
        for kp in k.parts[:-1]:
            if kp not in r:
                r[kp] = PKDict()
            r = r[kp]
        kp = k.parts[-1]
        if d.group:
            r[kp] = PKDict()
            continue
        try:
            r[kp] = _resolver(d)(k, d)
        except Exception as e:
            pkinspect.append_exception_reason(e, f"key={kp}, value={decls[k]}")
            raise
        _parsed_values[k] = r[kp]


def _resolver(decl):
    """How to resolve values for declaration

    Args:
        decl (_Declaration): what to resolve

    Returns:
        callable: `_resolve_dict`, `_resolve_list`, or `_resolve_value`
    """
    if dict == decl.parser:
        return _resolve_dict
    if list == decl.parser:
        return _resolve_list
    return _resolve_value


def _resolve_dict(key, decl):
    # TODO(robnagler) assert "required"
    res = PKDict(copy.deepcopy(decl.default) if decl.default else {})
    assert isinstance(res, dict), "{}: default ({}) must be a dict".format(
        key.msg, decl.default
    )
    key_prefix = key + "_"
    for k in reversed(sorted(_raw_values.keys())):
        if k != key and not k.startswith(key_prefix):
            continue
        r = res
        if len(k.parts) == 1:
            # os.environ has only one part (no way to split on '.')
            # so we have to assign the key's suffix manually
            ki = k.parts[0][len(key_prefix) :]
            # TODO(robnagler) if key exists, preserve case (only for environ)
        else:
            kp = k.parts[len(key.parts) : -1]
            for k2 in kp:
                if not k2 in r:
                    r[k2] = PKDict()
                else:
                    assert isinstance(
                        r[k2], dict
                    ), "{}: type collision on existing non-dict ({}={})".format(
                        k.msg, k2, r[k2]
                    )
                r = r[k2]
            ki = k.parts[-1]
        r[ki] = _raw_values[k]
    return res


def _resolve_list(key, decl):
    # TODO(robnagler) assert required
    res = copy.deepcopy(decl.default) if decl.default else []
    assert isinstance(res, list), "{}: default ({}) must be a list".format(
        key.msg, decl.default
    )
    if key not in _raw_values:
        assert not decl.required, "{}: config value missing and is required".format(k)
        return res
    if not isinstance(_raw_values[key], list):
        if _raw_values[key] is None:
            return None
        raise_error(
            "{}: value ({}) must be a list or None".format(key.msg, _raw_values[key]),
        )
    return _raw_values[key] + res


def _resolve_value(key, decl):
    if key in _raw_values:
        res = _raw_values[key]
    else:
        assert not decl.required, "{}: config value missing and is required".format(
            key.msg
        )
        res = decl.default
    # TODO(robnagler) FOO_BAR='' will not be evaluated. It may need to be
    # if None is not a valid option and there is a default
    if res is None and not hasattr(decl.parser, _PARSE_NONE_ATTR):
        return None
    return decl.parser(res)


def _z(msg):
    """Useful for debugging this module"""
    with open("/dev/tty", "w") as f:
        f.write(str(msg) + "\n")
