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
import re


#: file extension for yaml
PATH_EXT = '.yml'

#: parse_files macro expansion pattern
_MACRO_NAME_RE = re.compile(r'^([a-z]\w+)\(\)$', flags=re.IGNORECASE)
_MACRO_CALL_RE = re.compile(r'^([a-z]\w+)\(\)$', flags=re.IGNORECASE)

_SELF = '_self'

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
        self.pkupdate(
            files=PKDict(py=[], yml=[]),
            macros=PKDict(),
        )
        for f in files:
            self._add_file(f)

    def evaluate(self):
        res = PKDict()
        for f in self.files.yml:
            res.pkmerge(self._evaluate(f))
        return res

    def _add_file(self, path):
        e = path.ext[1:].lower()
        f = PKDict(
            data=getattr(self, f'_ext_{e}')(path),
            ext=e,
            path=path,
        )
        self._add_macros(f)
        self.files[e].append(f)

    def _add_macros(self, source):
        m = source.data.pkdel('macros') if source.ext == 'yml' else source.data
        if not m:
            return
        for n, f in m.items():
#            m = _MACRO_NAME_RE.search(n)
#            if not m:
#                raise AssertionError(f'invalid macro name={n} path={source.path}')
#TODO parse args
#            n = m.group(1)
            if n in self.macros:
                raise AssertionError(
                    f'duplicate macro={n} path1={self.macros[n].path} path2={source.path}',
                )
            self.macros[n] = PKDict(name=n, func=f, path=source.path)

    def _evaluate(self, source):

        g = {}
        l = _Namespace(self)

        def _do(data, exp):
            if isinstance(data, dict):
#TODO: macro is weird here in the case of k, need to pass (v) (unevaluated)
                return PKDict({_do(k, exp): _do(v, exp) for k, v in data.items()})
            elif isinstance(data, list):
                return [_do(e, exp) for e in data]
            elif exp and isinstance(data, str):
                m = _MACRO_CALL_RE.search(data)
                if m:
                    return _do(eval(f'{m.group(1)}(_SELF)', g, l), False)
#TODO: if its a function, we have an error, because someone referred to a function like mymacro(other_mac)
            return data

        return _do(source.data, True)

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

class _Namespace():
    def __init__(self, parser):
        self.__parser = parser

    def __getattr__(self, name):
        m = self.__parser.macros.get(name)
        if not m:
            return AttributeError(f'macro name={name}')

        def x(*args, **kwargs):
            return m.func(self, *args, **kwargs)

        return x

    def __getitem__(self, name):
        if name == _SELF:
            return self
        m = self.__parser.macros.get(name)
        if m:
            return m.func
        return KeyError(f'macro name={name}')

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
