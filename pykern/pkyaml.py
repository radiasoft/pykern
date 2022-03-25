# -*- coding: utf-8 -*-
u"""Wrapper for :mod:`ruamel`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern.pkdebug import pkdp, pkdlog
from pykern import pkinspect
from pykern import pkio
from pykern import pkresource
from pykern.pkcollections import PKDict
import collections.abc
import copy
import ruamel.yaml


#: file extension for yaml
PATH_EXT = '.yml'


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
    y = ruamel.yaml.YAML()
    if pretty:
        y.indent(mapping=2, sequence=4, offset=2)
    y.dump(_fixup_dump(obj), stream=pkio.open_text(filename, mode='wt'), **kwargs)


def load_file(filename):
    """Read a file, making sure all keys and values are locale.

    Args:
        filename (str or py.path): file to read (Note: ``.yml`` will not be appended)

    Returns:
        object: `PKDict` or list
    """
    return load_str(pkio.read_text(filename))


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
        ruamel.yaml.YAML(typ='safe').load(value),
    )


def parse_files(to_parse):
    return _Parser(to_parse)


def _fixup_dump(obj):
    if isinstance(obj, PKDict):
        return {k: _fixup_dump(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_fixup_dump(v) for v in obj]
    return obj


def _fixup_load(obj):
    """Convert all objects to locale strings and PKDict"""
    if isinstance(obj, dict):
        r = PKDict()
        for k, v in obj.items():
            r[pkcompat.locale_str(k)] = _fixup_load(v)
        return r
    if isinstance(obj, (list, tuple)):
        return [_fixup_load(v) for v in obj]
    if type(obj) == bytes or type(obj) == str and hasattr(obj, 'decode'):
        return pkcompat.locale_str(obj)
    return obj


class _Parser(PKDict):

    def __init__(self, files):
        self.files = PKDict(py=[], yml=[])
        self.macros = PKDict()
        for f in files:
            self._add_file(f)

    def evaluate(self):
        res = PKDict()
        for f in self.files.py:
            self._add_macros(f.data, f.path)
        for f in self.files.yml:
            m = f.data.pkdel('macros')
            res.pkmerge(f.data)
            if m:
                self._add_macros(m, f.path)
        return res

    def _add_file(self, path):
        e = path.ext[1:].lower()
        self.files[e].append(
            PKDict(
                data=getattr(self, f'_ext_{e}')(path),
                path=path,
            ),
        )

    def _add_macros(self, macros, source):
        for n, f in macros.items():
            if n in self.macros:
                raise AssertionError(f'duplicate macro={n} source1={f.source} source2={source}')
            self.macros[n] = PKDict(name=n, func=f, source=source)

    def _ext_py(self, path):
        import inspect
        import pykern.pkrunpy

        m = PKDict()
        for n, o in inspect.getmembers(pykern.pkrunpy.run_path_as_module(path)):
            if inspect.isfunction(o):
                m[n] = o
        return m

    def _ext_yml(self, path):
        return load_file(path)

    # parse yaml and python and hold
    # no global state except macros, which cannot collide
    # client provides context (channel, host) with eval (HostDb)
    # macro content can be evaled (or not) by (macro) caller (object which must be evaluated)?)
    # so can build control structures or whatever
    # merge_dict doesn't need replace_db that's done by a macro
    # order of merging is defined by client as an iterator over the tree (see rsconf.host_db)
    # eval happens real time. parsing for macros (full value elements only x: a() not x: a()b)


#class _ParserNames():
#    def x(self):
#        print(self.z)
#        return 33
#
#    def __getitem__(self, v):
#        print(v)
#        return lambda: 33
#
#e='x()+1'
#self=T()
#print(eval(e, {}, self))
