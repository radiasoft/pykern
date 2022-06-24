# -*- coding: utf-8 -*-
u"""File-based configuration

fc_arg/child/content is the content argument
fc_raw_child is the raw data (unevaled)
fc_<func> are builtins
depth first eval
templates eval values
templates: is the section
functions: are in python
macros: yield
   they can have variables ${arg}
   in the

template args substituted before eval

for macros that are loops (multi yield)
    the return is always an array or dict
    depending on what context it is executing in

self is dynamic

return value can be dynamic created off self, e.g.
     return seflf.fc_replace(self.fc_parent(), etc.)

# if *args, defer eval args
# if a function begins with_ then must yield and eval is deferred



:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import copy
import inspect
import pykern.pkrunpy
import re
import pykern.pkyaml

#: parse_files macro expansion pattern
_TEMPLATE_NAME_RE = re.compile(r'^([a-z]\w*)\(((?:\s*[a-z]\w*\s*)?(?:,\s*[a-z]\w*\s*)*)\)$', flags=re.IGNORECASE)

_MACRO_CALL_RE = re.compile(r'^([a-z]\w*)\((.*)\)$', flags=re.IGNORECASE+re.DOTALL)

_ARGS_RE = re.compile(r'\s*,\s*|\s+')

_TEMPLATE_CALL_RE = re.compile(r'\$\{(\w+)\}')

_SELF = '_self'

_NO_PARAM = object()

class Parser(PKDict):

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
        if e == 'py':
            self._add_macros(f)
        elif e == 'yml':
            self._add_templates(f)
        else:
            raise AssertionError(f'unhandled file ext={e}')
        self.files[e].append(f)

    def _add_macro(self, **kwargs):
        n = kwargs['name']
        if n in self.macros:
            raise AssertionError(
                f'duplicate macro={n} path1={self.macros[n].path} path2={kwargs["path"]}',
            )
        self.macros[n] = _Macro(kwargs)

    def _add_macros(self, source):
        m = source.data
        if not m:
            return
        for n, f in m.items():
            self._add_macro(
                func=f,
                name=n,
                params=list(f.__code__.co_varnames),
                path=source.path,
            )

    def _add_templates(self, source):
        m = source.data.pkdel('fconf_templates')
        if not m:
            return
        for n, c in m.items():
            m = _TEMPLATE_NAME_RE.search(n)
            if not m:
                raise AssertionError(f'invalid macro name={n} path={source.path}')
            n = m.group(1)
            #TODO: duplicate arg check
            self._add_macro(
                content=c,
                name=n,
#TODO: check for dups
                params=[x for x in _ARGS_RE.split(m.group(2)) if x],
                path=source.path,
            )

    def _call_template(self, decl, args, kwargs):
        p = decl.params[:]
#DOC: no optional params in templates
        z = PKDict({k: _NO_PARAM for k in p})
        n = args.pop(0)
        for a in args:
            if not p:
                raise TypeError(f'too many args={args} macro={decl.name}')
            z[p.pop(0)] = a
        for k, v in kwargs.items():
            if k not in p:
                if k not in decl.params:
                    raise TypeError(f'invalid kwarg={k} macro={decl.name}')
                raise TypeError(f'position arg followed by kwarg={k} macro={decl.name}')
            if z[k] is not _NO_PARAM:
                raise TypeError(f'duplicate kwarg={k} macro={decl.name}')
            z[k] = v
        x = [k for k, v in z.items() if v is _NO_PARAM]
        if x:
            raise TypeError(f'missing args={x} macro={decl.name}')

#TODO: what if this is a complex structure

        def _repl(match):
            n = match.group(1)
            if n not in z:
                TypeError(f'unknown arg={n} referenced in macro={decl.name}')
            return z[n]

#TODO: may need to yaml the result?
        return _TEMPLATE_CALL_RE.sub(_repl, decl.content)

    def _evaluate(self, source):

        g = {}
        l = _Namespace(self)

        def _do(data, exp):
            if isinstance(data, dict):
#TODO: macro is weird here in the case of k, need to pass (v) (unevaluated)
#TODO: do we want objects, can know if it is evaluated?
                return PKDict({_do(k, exp): _do(v, exp) for k, v in data.items()})
            elif isinstance(data, list):
                return [_do(e, exp) for e in data]
            elif exp and isinstance(data, str):
                m = _MACRO_CALL_RE.search(data)
                if m:
                    r = _do(
                        eval(f'{m.group(1)}({_SELF},{m.group(2)})', g, l),
                        False,
                    )
                    # Unlikely a useful output if a callable.
                    # Probably don't want classes either (which are callable).
                    if callable(r):
                        raise AssertionError('macro={m.group(1) returned function={r}')
                    return r

            return data

        return _do(source.data, True)

    def _ext_py(self, path):
        m = PKDict()
        for n, o in inspect.getmembers(pykern.pkrunpy.run_path_as_module(path)):
            if inspect.isfunction(o):
                m[n] = o
        return m

    def _ext_yml(self, path):
        return pykern.pkyaml.load_file(path)


class _Macro(PKDict):
    pass


class _Namespace():

    def __init__(self, parser):
        self.__parser = parser

    def __func(self, name, exc):
        m = self.__parser.macros.get(name)
        if not m:
            raise exc(f'macro name={name}')

        def x(*args, **kwargs):
            a = list(args)
            if not a or a[0] is not self:
                a.insert(0, self)
            if 'func' in m:
                return m.func(*a, **kwargs)
            return self.__parser._call_template(m, a, kwargs)

        return x

    def __getattr__(self, name):
        return self.__func(name, AttributeError)

    def __getitem__(self, name):
        if name == _SELF:
            return self
        return self.__func(name, KeyError)
