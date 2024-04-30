"""Wrapper for :mod:`yaml`

:copyright: Copyright (c) 2015-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from pykern import pkcompat
from pykern import pkinspect
from pykern import pkio
from pykern import pkresource
import ruamel.yaml


#: file extension for yaml
PATH_EXT = ".yml"


def dump_pretty(obj, filename, pretty=True, **kwargs):
    """Formats as yaml as string

    If an object is not encoded by default, will call str() on the
    object.

    Unlike `pkjson.dump_pretty`, returns nothing.

    Args:
        obj (object): any Python object
        filename (str or py.path): where to write
        pretty (bool): pretty print [True]
        kwargs (object): other arguments to `ruamel.yaml.dump`
    """
    try:
        y = ruamel.yaml.YAML()
        if pretty:
            y.indent(mapping=2, sequence=4, offset=2)
            y.dump(
                _fixup_dump(obj), stream=pkio.open_text(filename, mode="wt"), **kwargs
            )
    except Exception:
        pkdlog("error writing file={}", filename)
        raise


def load_file(filename):
    """Read a file, making sure all keys and values are locale.

    Args:
        filename (str or py.path): file to read (Note: ``.yml`` will not be appended)

    Returns:
        object: `PKDict` or list
    """
    try:
        return load_str(pkio.read_text(filename))
    except Exception:
        pkdlog("error file={}", filename)
        raise


def load_resource(basename):
    """Read a resource, making sure all keys and values are locale

    Args:
        basename (str): file to read without yml suffix

    Returns:
        object: `PKDict` or list
    """
    return load_file(
        pkresource.filename(basename + PATH_EXT, pkinspect.caller_module()),
    )


def load_str(value):
    """Read a value, making sure all keys and values are locale.

    Args:
        value (str): string to parse

    Returns:
        object: `PKDict` or list
    """
    return _fixup_load(
        ruamel.yaml.YAML(typ="safe").load(value),
    )


def _fixup_dump(obj):
    if isinstance(obj, PKDict):
        return {k: _fixup_dump(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_fixup_dump(v) for v in obj]
    return obj


def _fixup_load(obj):
    """Convert all objects to locale strings and PKDict"""

    def _scalar(v):
        if isinstance(v, (bytes, bytearray)):
            return pkcompat.locale_str(v)
        return v

    if isinstance(obj, dict):
        return PKDict({_scalar(k): _fixup_load(v) for k, v in obj.items()})
    if isinstance(obj, (list, tuple)):
        return [_fixup_load(v) for v in obj]
    return _scalar(obj)
