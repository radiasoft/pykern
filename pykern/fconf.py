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


TODO: hold state on "self". Maybe a special function fconf_var().get/put

  _mpi_worker_prod(): |
    mpi_worker:
      clusters:
      {% for k, v in _host_mpi_user.items() %}
        "{{ k }}":
          {% for i in v %}
          - {{ _fnl(i) }}
          {% do _host_mpi.append(i) %}
          {% endfor %}
      {% endfor %}
    {% endif %}


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
#TODO: rsconf can supply a base context, which could be used as values

#TODO: use values from base in templates and vars? already exists so
#how to reference values by partial or full paths? ${hostname}?
#hostname cannot be fully evaluated, because that's a separate merging
#process
        self.pkupdate(
            files=PKDict(py=[], yml=[]),
            macros=PKDict(),
        )
        for f in files:
            try:
                self._add_file(f)
            except Exception:
                pkdlog('error parsing file={}', f)
                raise
        res = PKDict()
        for f in self.files.yml:
            self._evaluate(f, res)
        self.result = res

    def _add_file(self, path):
        e = path.ext[1:].lower()
        f = _File(
            data=getattr(self, f'_ext_{e}')(path),
            ext=e,
            path=path,
        )
        if e == 'py':
            self._add_macros(f)
        elif e == 'yml':
            self._add_templates(f)
        else:
            raise ValueError(f'unhandled file ext={e}')
        self.files[e].append(f)

    def _add_macro(self, macro):
        n = macro.name
        if n in self.macros:
            raise ValueError(
                f'duplicate macro={macro.name} path1={self.macros[macro.name].path} path2={macro.path}',
            )
        self.macros[macro.name] = macro

    def _add_macros(self, source):
        m = source.data
        if not m:
            return
        for n, f in m.items():
            self._add_macro(
                _Macro(
                    func=f,
                    name=n,
                    params=tuple(f.__code__.co_varnames),
                    path=source.path,
                ),
            )

    def _add_templates(self, source):
        m = source.data.pkdel('fconf_templates')
        if not m:
            return
        for n, c in m.items():
            m = _TEMPLATE_NAME_RE.search(n)
            if not m:
                raise ValueError(f'invalid macro name={n} path={source.path}')
            n = m.group(1)
            #TODO: duplicate arg check
            self._add_macro(
                _Template(
                    content=c,
                    name=n,
#TODO: check for dups
                    params=tuple((x for x in _ARGS_RE.split(m.group(2)) if x)),
                    path=source.path,
                ),
            )

    def _evaluate(self, source, base):

        # The builtins are useful. PKDict(__builtins__=PKDict())
        global_ns = PKDict()
        local_ns = _Namespace(self)

        def _expr(value):
            m = _MACRO_CALL_RE.search(value)
            if not m:
                return False, None
            return True, _recurse(
                eval(f'{m.group(1)}({_SELF},{m.group(2)})', global_ns, local_ns),
                expr_op=None,
            )

        try:
# pass in global_ns or is there one evaluator
            return _Evaluator(source=source, base=base, expr_op=_expr)
        except Exception:
            pkdlog('Error expanding macros in file={}', f)
            raise

    def _ext_py(self, path):
        m = PKDict()
        for n, o in inspect.getmembers(pykern.pkrunpy.run_path_as_module(path)):
            if inspect.isfunction(o):
                m[n] = o
        return m

    def _ext_yml(self, path):
        return pykern.pkyaml.load_file(path)


class _File(PKDict):

    def pkdebug_str(self):
        return pkio.py_path().bestrelpath(self.path)


class _Macro(PKDict):

    def call(self, namespace, args, kwargs):
#pass evaluator
        return self.func(namespace, *args, **kwargs)


class _Template(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
#TEST: duplicate params, invalid params, etc.
        s = set()
        for p in self.params:
            if p in s:
                raise TypeError(f'duplicate param={p} in template={self.name}')
            s.add(p)

    def call(self, namespace, args, kwargs):
#pass evaluator
        return self._evaluate(namespace, self._parse_args(args, kwargs))

    def _evaluate(self, namespace, kwargs):

        def _expr(value):
            return True, _TEMPLATE_CALL_RE.sub(_repl, value)

        def _repl(match):
            n = match.group(1)
            if n not in kwargs:
                TypeError(f'unknown arg={n} referenced in macro={self.name}')
            return kwargs[n]

        return _recurse(self.content, _expr)


    def _parse_args(self, args, kwargs):
        p = list(self.params)
        res = PKDict({k: _NO_PARAM for k in p})
#DOC: no optional params in templates
        for a in args:
            if not p:
                raise TypeError(f'too many args={args} macro={self.name}')
            res[p.pop(0)] = a
        for k, v in kwargs.items():
            if k not in p:
                if k not in self.params:
                    raise TypeError(f'invalid kwarg={k} macro={self.name}')
                raise TypeError(f'position arg followed by kwarg={k} macro={self.name}')
            if res[k] is not _NO_PARAM:
                raise TypeError(f'duplicate kwarg={k} macro={self.name}')
            res[k] = v
        x = [k for k, v in res.items() if v is _NO_PARAM]
        if x:
            raise TypeError(f'missing args={x} macro={self.name}')
        return res


class _Namespace():

    def __init__(self, parser):
        self.__parser = parser

    def __func(self, name, exc):
        m = self.__parser.macros.get(name)
        if not m:
            raise exc(f'macro name={name}')

        def x(*args, **kwargs):
            a = list(args)
            if a and a[0] is self:
                a.pop(0)
            return m.call(self, a, kwargs)

        return x

    def __getattr__(self, name):
        return self.__func(name, AttributeError)

    def __getitem__(self, name):
        if name == _SELF:
            return self
        return self.__func(name, KeyError)


class _Evaluator(PKDict):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.result = self.old
        if 'path' in
        self._do(self.value)


    def _do(self, new, base, ancestors):

        if isinstance(new, dict) or isinstance(base, dict):
            _dict()
        elif isinstance(new, list) or isinstance(base, list):
            if isinstance(t, (types.GeneratorType, set, tuple)):
                    t = list(t)
                if s is None or t is None:
                    # Just replace, because t overrides type in case of None
                    pass
                elif isinstance(s, list) and isinstance(t, list):
                    # prepend the to_merge values; creates a new list
                    self[k] = t + s
                    # strings, numbers, etc. are hashable, but dicts and lists are not.
                    # this test ensures we don't have dup entries in lists.
                    y = [x for x in self[k] if isinstance(x, collections.abc.Hashable)]
                    assert len(set(y)) == len(y), \
                        f'duplicates in key={k} list values={self[k]}'
                    continue
                else:
                    raise _type_err(k, s, t)
            elif type(s) != type(t) and not (s is None or t is None):
                raise _type_err(k, s, t)
            self[k] = t
        return self




        def _dict():
                if s is None:
                    pass
                elif t is None:
                    # Just replace, because t's type (None) overrides in case of None.
                    pass
                elif isinstance(s, dict) and isinstance(t, dict):
                    s.pkmerge(t)
                    continue
                else:
                    raise _type_err(k, s, t)

            x = list(value.keys())
                self._do(k, parent=value)


    #TODO: macro is weird here in the case of k, need to pass (v) (unevaluated)
    #TODO: do we want objects, can know if it is evaluated?
            return PKDict({
                _recurse(k, expr_op): _recurse(v, expr_op) for k, v in value.items()
            })

        def _expr()
            try:
                k, r = expr_op(value)
                if k:
                    return pkcollections.canonicalize(r)
    #if in key context:
    #    list: replace with list if empty dict
    #    dict: merge
    #    otherwise is a key
            except Exception:
                pkdlog('Error expanding macro={}', value)
                raise
            return value

        if isinstance(value, PKDict):
            return _dict()
        elif isinstance(value, list):
            return _list()
        elif expr_op and isinstance(value, str):
            return _expr()
        return value


    def _do_list(self, value, parent=None)
            return [

                _recurse(e, expr_op) for e in value
            ]

    def _do_dict(self, value,
