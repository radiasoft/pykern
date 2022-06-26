# -*- coding: utf-8 -*-
"""File-based configuration

fconf_clear()
fconf_inner() -- already evaluated? yes by default
${} for global_fvars() on namespace? how would it work?
convert rsconf
class for fconf macros, can that just be _Namespace?
escape \\${}

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import contextlib
import copy
import inspect
import pykern.pkrunpy
import re
import pykern.pkyaml
import pykern.pkcollections
import pykern.pkio


#: parse_files macro expansion pattern
_TEMPLATE_NAME_RE = re.compile(r'^([a-z]\w*)\(((?:\s*[a-z]\w*\s*)?(?:,\s*[a-z]\w*\s*)*)\)$', flags=re.IGNORECASE)

_MACRO_CALL_RE = re.compile(r'^([a-z]\w*)\((.*)\)$', flags=re.IGNORECASE+re.DOTALL)

_ARGS_RE = re.compile(r'\s*,\s*|\s+')

_FVAR_RE = re.compile(r'\$\{(\w+)\}')
_FVAR_EXACT_RE = re.compile('^' + _FVAR_RE.pattern + '$')

_SELF = '_self'

_NO_PARAM = object()


class Parser(PKDict):

    def __init__(self, files):
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
        e = _Evaluator(parser=self)
        for f in self.files.yml:
            e.do(source=f)
        self.result = e.global_fvars

    def _add_file(self, path):
        e = path.ext[1:].lower()
        f = _File(
            content=getattr(self, f'_ext_{e}')(path),
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
            raise ValueError(f'duplicate {macro}, other {self.macros[macro.name]}')
        self.macros[macro.name] = macro

    def _add_macros(self, source):
        m = source.content
        if not m:
            return
        for n, f in m.items():
            self._add_macro(
                _Macro(
                    func=f,
                    name=n,
                    params=tuple(f.__code__.co_varnames),
                    source=source,
                ),
            )

    def _add_templates(self, source):
        m = source.content.pkdel('fconf_templates')
        if not m:
            return
        for n, c in m.items():
            m = _TEMPLATE_NAME_RE.search(n)
            if not m:
                raise ValueError(f'invalid macro name={n} {source}')
            n = m.group(1)
            #TODO: duplicate arg check
            self._add_macro(
                _Template(
                    content=c,
                    name=n,
#TODO: check for dups
                    params=tuple((x for x in _ARGS_RE.split(m.group(2)) if x)),
                    source=source,
                ),
            )

    def _ext_py(self, path):
        m = PKDict()
        for n, o in inspect.getmembers(pykern.pkrunpy.run_path_as_module(path)):
            if inspect.isfunction(o):
                m[n] = o
        return m

    def _ext_yml(self, path):
        return pykern.pkyaml.load_file(path)


class _Evaluator(PKDict):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # By not passing __builtins__=PKDict(), builtins are implicitly added.
        # Builtins are useful
        self.global_ns = PKDict()
        self.local_ns = _Namespace(self)
        self.global_fvars = PKDict()
        self.local_fvars = PKDict()

    def do(self, source, **kwargs):
        p = self.local_fvars
        i = 'local_fvars' in kwargs
        if i:
            self.local_fvars = kwargs['local_fvars']
            base = None
        else:
            if not (source.content is None or isinstance(source.content, PKDict)):
                raise ValueError(f'{source} must be PKDict or empty')
            base = self.global_fvars
            self.xpath = _XPath()
        try:
            with self._xpath(kwargs.get('xpath_element')):
                return self._do(source.content, base)
        except Exception:
            if not i:
                pkdlog('Error evaluating {} {}', source, self.xpath)
            raise
        finally:
            self.local_fvars = p

    def _dict(self, new, base):
        if not isinstance(base, PKDict):
            if base is not None:
                raise ValueError(f'mismatched types new={new} base={base}')
            base = PKDict()
        for k, v in new.items():
#TODO: pass v to expr
            with self._xpath(k):
                x = self._expr(k)
                if isinstance(x, PKDict):
                    #TODO better error msgs
                    assert v is None, f'key={k} must not have a value'
                    base.pkmerge(x)
                elif isinstance(x, list):
                    raise ValueError(
                        f'mismatched types expanding macro={k} to value={x}'
                        + ' into dict={res}',
                        )
                else:
                    assert x is not None, f'expanded macro={k} to None'
                    with self._xpath(x):
                        base[x] = self._do(v, base.get(x))
        return base

    def _do(self, new, base):
        if isinstance(new, PKDict):
            return self._dict(new, base)
        if isinstance(new, list):
            return self._list(new, base)
        return self._expr(new)

    def _expr(self, value):

        def _fvar(match):
            n = match.group(1)
            if n not in self.local_fvars:
                TypeError(f'unknown template fvar={n}')
            return self.local_fvars[n]

        with self._xpath(value):
            if not isinstance(value, str):
                # already canonicalized
                return value
            m = _FVAR_EXACT_RE.search(value)
            # This check prevents stringification of data types on exact
            # matches, which is important for non-string fvars
            if m:
                v = _fvar(m)
                if not isinstance(v, str):
                    # already canonicalized
                    return v
            else:
                v = _FVAR_RE.sub(_fvar, value)
            m = _MACRO_CALL_RE.search(v)
            if m:
                return eval(
                    f'{m.group(1)}({_SELF},{m.group(2)})',
                    self.global_ns,
                    self.local_ns,
                )
        return v

    def _list(self, new, base):
        if not isinstance(base, list):
            if base is not None:
                raise ValueError(f'mismatched types new={new} base={base}')
            base = []
        res = []
        for i, e in enumerate(new):
            # lists don't have base values
            with self._xpath(f'[{i}]'):
                x = self._do(e, None)
            if isinstance(x, list):
                res.extend(x)
            else:
                res.append(x)
        return res + base

    @contextlib.contextmanager
    def _xpath(self, element=None):
        """Track element path for errors

        If there is an exception, xpath will hold the place of the exception
        """
        if element is not None:
            self.xpath.push(element)
            pkdp('> {}', self.xpath.top())
            yield
            self.xpath.pop()
            pkdp('<')
        else:
            yield


class _File(PKDict):

    def __str__(self):
        return 'source=' + pykern.pkio.py_path().bestrelpath(self.path)


class _Macro(PKDict):

    def call(self, namespace, args, kwargs):
        return pykern.pkcollections.canonicalize(
            self.func(namespace, *args, **kwargs),
        )

    def _kind(self):
        return 'macro'

    def __str__(self):
        return f'{self._kind}={self.name} {self.source}'


class _Namespace():

    def __init__(self, evaluator):
        self._evaluator = evaluator

    def __func(self, name, exc):
        m = self._evaluator.parser.macros.get(name)
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
        return namespace._evaluator.do(
            base=None,
            local_fvars=self._parse_args(args, kwargs),
            source=self,
            xpath_element=self.name + '()',
        )

    def _kind(self):
        return 'template'

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

    def __str__(self):
        return f'template={self.name}'


class _XPath():

    def __init__(self):
        self.stack = []

    def pkdebug_str(self):
        res = 'XPath:\n'
        for i in self.stack:
            res += self._str(i)
        return res

    def push(self, key):
        f  = inspect.currentframe().f_back.f_back.f_back
        self.stack.append(
            PKDict(key=key, func=f.f_code.co_name, line=f.f_lineno),
        )

    def pop(self):
        self.stack.pop()

    def top(self):
        if self.stack:
            return self._str(self.stack[-1])
        else:
            'None'

    def _str(self, element):
        return f'{element.func}:{element.line} {str(element.key):20}\n'
