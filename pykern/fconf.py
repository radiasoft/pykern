"""Python and YAML configuration file parser.

FConf reads Python and YAML files and produces a single, merged
PKDict. FConf is not a replacement for `pykern.pkconfig`. Rather it is
for complex configuration input files to programs that often require
programmatic generation. FConf was written for
`RSConf <https://git.radiasoft.org/rsconf>`_.

The Basic YAML configuration look like this::

    fconf_macros:
      make_uri(host):
          "https://${host}"

    some:
       - item
    uri: make_uri('sirepo.com')

Macros in the `fconf_macros` are simple replacements.  They cannot have
loops or other conditions. These are reserved for Python files.

A macro use must be a full text element. It cannot be embedded in
text, e.g.  ``curl make_uri('sirepo.com')``, that's because macros can
return data structures. The syntax is pure Python. Unlike YAML strings,
the arguments have to be quoted, because they will be evaluated by the Python
interpreter.

More complex macros can be programmed in a Python file::

    import math

    def hypotenuse(self, a, b):
        return math.sqrt(a ** 2, b ** 2)

Using in YAML looks the same::

    long_side: hypotenuse(3, 4)

Note that the arguments were not quoted here, because they are integers.

The typical usage is::

    fconf.parse_all(some_dir)

where `some_dir` is a `py.path` that contains python and yaml files to parse.
You can also call `Parser` directly with the a list of files to parse.

As noted, the arguments to a macro are Python. Actually, the entire
value is a Python expression, and the only requirement is that it
begin with a Python word, which can be any Python function. For example::

    count_down:
      - reversed(range(4))

Produces the following Python Structure::

    {'count_down': [3, 2, 1, 0]}

This allows for a lot of possibilities within the YAML alone.

The Python and YAML macros can call each other. Inside a Python file,
just use self to call something::

    def count_up(self, top):
        return reversed(self.count_down(top))

Note that the above count_down example used a special feature of
result merging. When a Macro returns a list (generator, tuple, etc.)
in a list context, it will merge with the list. Strings are used in
place. For example::

    mixed:
      - range(3)
      - make_uri('sirepo.com')

Produces::

    {'mixed': [0, 1, 2, 'https://sirepo.com']}

The same is true of dicts. For example::

    fconf_macros:
      base(num):
        v${num}.radia.run:
          description: VM ${num}

    all_hosts:
      base(3):
      base(5):

Produces::

    {
        "all_hosts": {
            "v3.radia.run": {
                "description": "VM 3",
            },
            "v5.radia.run": {
                "description": "VM 5",
            },
        },
    }

There are some other useful features. You can refer to any previous
declared value using variable expansion. For example::

    a:
      b:
        c: 3
    d: ${a}
    e: ${a.b.c}


Produces::

    {
        'a': {'b': {'c': 3}},
        'd': {'b': {'c': 3}},
        'e': 3,
    }

This allows for flexible constants. Those global strings can be used
in YAML Macros.

YAML files are evaluated before they are merged. However, they are all
merged before the next file is evaluated. This allows a main
"constants" file, for example, to direct the flow of the subsequent files.

Workarounds
-----------

Most strings do not need to be quoted in YAML, but with the extra syntax of FConf,
there are some special cases, for example, this fails::

  a: 1
  b: [ ${a} ]


It gets the error ``ruamel.yaml.parser.ParserError: while parsing a
flow sequence in "<unicode string> did not find expected ',' or
']'``. To work around, simply put in quotes::

  a: 1
  b: [ "${a}" ]

Another case is inline Python with braces like this::

  a: c({"d": "e"})

Just quote with single quotes::

  a: 'c({"d": "e"})'

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
import pykern.pkinspect
import pykern.pkio


#: matches word(word1, ...). Words have to begin with a letters
_TEXT_MACRO_DEF = re.compile(
    r"^([a-z]\w*)\(((?:\s*[a-z]\w*\s*)?(?:,\s*[a-z]\w*\s*)*)\)$", flags=re.IGNORECASE
)

_MACRO_CALL = re.compile(r"^([a-z]\w*)\((.*)\)$", flags=re.IGNORECASE + re.DOTALL)

_ARG_SEP = re.compile(r"\s*,\s*|\s+")

#: Matches result value and macro argument expansions. FVAR stands for Fconf Variable
_FVAR = re.compile(r"\$\{(\S+)\}")

#: Use an exact pattern so we can know that the result could be a data structure
_FVAR_EXACT = re.compile(f"^{_FVAR.pattern}$")

_RESERVED_PREFIX = "fconf_"

_SELF = _RESERVED_PREFIX + "self"

_NO_PARAM = object()

_BUILTINS_EXT = "builtins"


class Parser(PKDict):
    def __init__(self, files, base_vars=None):
        self.pkupdate(
            files=PKDict(),
            macros=PKDict(),
        )
        self._add_file(pykern.pkio.py_path(f"fconf.{_BUILTINS_EXT}"))
        for f in files:
            try:
                self._add_file(f)
            except Exception as e:
                pykern.pkinspect.append_exception_reason(e, f"fconf.Parser.file={f}")
                raise
        if "yml" not in self.files:
            raise ValueError("must supply at least one '.yml' file")
        e = _Evaluator(
            global_fvars=PKDict() if base_vars is None else copy.deepcopy(base_vars),
            parser=self,
        )
        for f in self.files.yml:
            e.start(source=f)
        self.result = e.global_fvars

    def _add_file(self, path):
        e = path.ext[1:].lower()
        if e == "yaml":
            e = "yml"
        f = _File(
            content=getattr(self, f"_ext_{e}")(path),
            ext=e,
            path=path,
        )
        if e in ("py", _BUILTINS_EXT):
            self._add_macros(f)
        elif e == "yml":
            self._add_text_macros(f)
        else:
            raise ValueError(f"unhandled file ext={e}")
        self.files.setdefault(e, []).append(f)

    def _add_macro(self, macro):
        n = macro.name
        if n in self.macros:
            raise ValueError(f"duplicate {macro}, other {self.macros[macro.name]}")
        if n.startswith(_RESERVED_PREFIX) and macro.source.ext != _BUILTINS_EXT:
            raise ValueError(f"macro={macro} may not begin with {_RESERVED_PREFIX}")
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
                    # TODO(robnagler) assert varnames don't begin with fconf_
                    params=tuple(f.__code__.co_varnames),
                    source=source,
                ),
            )

    def _add_text_macros(self, source):
        m = source.content.pkdel("fconf_macros")
        if not m:
            return
        for n, c in m.items():
            m = _TEXT_MACRO_DEF.search(n)
            if not m:
                raise ValueError(f"invalid macro name={n} {source}")
            n = m.group(1)
            # TODO: duplicate arg check
            self._add_macro(
                _YAMLMacro(
                    content=c,
                    name=n,
                    # TODO(robnagler): check for dups
                    # TODO(robnagler): assert varnames don't begin with fconf_
                    params=tuple((x for x in _ARG_SEP.split(m.group(2)) if x)),
                    source=source,
                ),
            )

    def _ext_builtins(self, path):
        return self._functions(_Builtins)

    def _ext_py(self, path):
        return self._functions(
            pykern.pkrunpy.run_path_as_module(path), co_filename=str(path)
        )

    def _ext_yml(self, path):
        return pykern.pkyaml.load_file(path)

    def _functions(self, obj, co_filename=None):
        import types

        m = PKDict()
        for n, o in inspect.getmembers(obj):
            # Ensure that macro comes from the file, not an import
            if inspect.isfunction(o) and (
                not co_filename or co_filename == o.__code__.co_filename
            ):
                m[n] = o
        return m


def parse_all(path, base_vars=None, glob="*"):
    """Parse all the Python and YAML files in `directory`

    Files are read in sorted order with all Python files first and
    YAML files next. YAML file evaluation happens in that same order.

    Args:
        path (py.path): directory that ``*.py`` and ``*.yml`` files
        base_vars (PKDict): initial variable state. May be hierarchical. [None]
        glob (str): basename to search in in directory
    Returns:
        PKDict: evaluated and merged files plus base_vars
    """

    def _glob(ext):
        return pykern.pkio.sorted_glob(path.join(f"{glob}.{ext}"))

    # yml & yaml need to be sorted together
    return Parser(_glob("py") + sorted(_glob("yml") + _glob("yaml"))).result


class _Builtins:
    @staticmethod
    def fconf_var(namespace, name):
        return namespace._evaluator.fconf_var(name)


class _Evaluator(PKDict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # By NOT passing __builtins__=PKDict(), builtins are implicitly added.
        # Python builtins are useful
        self.global_ns = PKDict()
        self.local_ns = _Namespace(self)
        self.local_fvars = PKDict()

    def fconf_var(self, name):
        try:
            return self.global_fvars.pknested_get(name)
        except KeyError:
            # Do not cascade the exception.
            pass
        raise KeyError(f"unknown macro param or fconf_var={name}")

    def start(self, source, **kwargs):
        p = self.local_fvars
        i = "local_fvars" in kwargs
        if i:
            self.local_fvars = kwargs["local_fvars"]
            base = None
        else:
            if not (source.content is None or isinstance(source.content, PKDict)):
                raise ValueError(f"{source} must be PKDict or empty")
            base = self.global_fvars
            self.xpath = _XPath()
        try:
            with self._xpath(kwargs.get("xpath_element")):
                return self._do(source.content, base)
        except Exception as e:
            if not i:
                pykern.pkinspect.append_exception_reason(
                    e,
                    f"fconf._Evaluator.source={source}\n{self.xpath.stack_as_str()}",
                )
            raise
        finally:
            self.local_fvars = p

    def _dict(self, new, base):
        if not isinstance(base, PKDict):
            if base is not None:
                raise ValueError(f"mismatched types new={new} base={base}")
            base = PKDict()
        for k, v in new.items():
            # TODO: pass v to expr
            with self._xpath(k):
                x = self._expr(k)
                with self._xpath(None if x == k else x):
                    if isinstance(x, PKDict):
                        # TODO better error msgs
                        assert v is None, f"key={k} must not have a value"
                        base.pkmerge(x, make_copy=False)
                    elif isinstance(x, list):
                        raise ValueError(
                            f"mismatched types expanding macro={k} to value={x}"
                            + " into dict={res}",
                        )
                    else:
                        assert x is not None, f"expanded macro={k} to None"
                        base[x] = self._do(v, base.get(x))
        return base

    def _do(self, new, base):
        if isinstance(new, PKDict):
            return self._dict(new, base)
        if isinstance(new, list):
            return self._list(new, base)
        return self._expr(new)

    def _expr(self, value):
        def _fvar_op(match, native=False, use_repr=False):
            n = match.group(1)
            if n in self.local_fvars:
                res = self.local_fvars[n]
            else:
                res = self.fconf_var(n)
            if use_repr:
                return repr(res)
            return res if native else str(res)

        def _fvar_sub(value, use_repr=False):
            with self._xpath(value):
                m = None if use_repr else _FVAR_EXACT.search(value)
                # This check prevents stringification of data types on exact
                # matches, which is important for non-string fvars
                if m:
                    res = _fvar_op(m, native=True)
                    if not isinstance(res, str):
                        # already canonicalized
                        return True, res
                else:
                    res = _FVAR.sub(
                        lambda x: _fvar_op(x, use_repr=use_repr),
                        value,
                    )
                return False, res

        if not isinstance(value, str):
            # already canonicalized
            return value
        k, v = _fvar_sub(value)
        if k:
            return v
        with self._xpath(v):
            m = _MACRO_CALL.search(v)
        if not m:
            return v
        with self._xpath(v):
            a = _fvar_sub(m.group(2))[1] if len(m.group(2)) > 0 else ""
            s = f"{_SELF}," if m.group(1) in self.parser.macros else ""
            v = f"{m.group(1)}({s}{a})"
            with self._xpath(v):
                return pykern.pkcollections.canonicalize(
                    eval(v, self.global_ns, self.local_ns),
                )

    def _list(self, new, base):
        if not isinstance(base, list):
            if base is not None:
                raise ValueError(f"mismatched types new={new} base={base}")
            base = []
        res = []
        for i, e in enumerate(new):
            # lists don't have base values
            with self._xpath(f"[{i}]"):
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
            pkdc("{}", element)
            yield
            self.xpath.pop()
        else:
            yield


class _File(PKDict):
    def __str__(self):
        return "source=" + pykern.pkio.py_path().bestrelpath(self.path)


class _Macro(PKDict):
    def call(self, namespace, args, kwargs):
        return self.func(namespace, *args, **kwargs)

    def _kind(self):
        return "pymacro"

    def __str__(self):
        return f"{self._kind}={self.name} {self.source}"


class _Namespace:
    def __init__(self, evaluator):
        self._evaluator = evaluator

    def __func(self, name, exc):
        def _canonicalize(value):
            """Allow functions at the top level

            There are cases when it is useful to pass functions even to YAML macros.
            """
            if inspect.isfunction(value):
                return value
            return pykern.pkcollections.canonicalize(value)

        def _wrapper(*args, **kwargs):
            a = list(args)
            if a and a[0] is self:
                a.pop(0)
            return m.call(
                self,
                [_canonicalize(x) for x in a],
                PKDict({k: _canonicalize(v) for k, v in kwargs.items()}),
            )

        m = self._evaluator.parser.macros.get(name)
        if not m:
            raise exc(f"macro name={name}")

        return _wrapper

    def __getattr__(self, name):
        return self.__func(name, AttributeError)

    def __getitem__(self, name):
        if name == _SELF:
            return self
        return self.__func(name, KeyError)


class _XPath:
    def __init__(self):
        self.stack = []

    def push(self, key):
        f = inspect.currentframe().f_back.f_back.f_back
        self.stack.append(
            PKDict(key=key, func=f.f_code.co_name, line=f.f_lineno),
        )

    def pop(self):
        self.stack.pop()

    def __str__(self):
        return "/".join([k.key for k in self.stack])

    def stack_as_str(self):
        res = "Evaluator stack:\n"
        for i in self.stack:
            res += self._str(i)
        return res

    def _str(self, element):
        return f"{element.func}:{element.line} {str(element.key):.100}\n"


class _YAMLMacro(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TEST: duplicate params, invalid params, etc.
        s = set()
        for p in self.params:
            if p in s:
                raise TypeError(f"duplicate param={p} in macro={self.name}")
            s.add(p)

    def call(self, namespace, args, kwargs):
        return namespace._evaluator.start(
            base=None,
            local_fvars=self._parse_args(args, kwargs),
            source=self,
            xpath_element=self.name + "()",
        )

    def _kind(self):
        return "macro"

    def _parse_args(self, args, kwargs):
        p = list(self.params)
        res = PKDict({k: _NO_PARAM for k in p})
        # DOC: there are no optional params in text_macros
        for a in args:
            if not p:
                raise TypeError(f"too many args={args} macro={self.name}")
            res[p.pop(0)] = a
        for k, v in kwargs.items():
            if k not in p:
                if k not in self.params:
                    raise TypeError(f"invalid kwarg={k} macro={self.name}")
                raise TypeError(f"position arg followed by kwarg={k} macro={self.name}")
            if res[k] is not _NO_PARAM:
                raise TypeError(f"duplicate kwarg={k} macro={self.name}")
            res[k] = v
        x = [k for k, v in res.items() if v is _NO_PARAM]
        if x:
            raise TypeError(f"missing args={x} macro={self.name}")
        return res

    def __str__(self):
        return f"macro={self.name}"
