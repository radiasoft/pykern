"""Excel spreadsheet generator

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import decimal
import xlsxwriter
import re


_XL_COLS = None

_NO_CHILDREN = tuple()

_DEFAULT_ROUND_DIGITS = 2

_DIGITS_TO_PLACES = None

_SPACES = re.compile(r"\s+")

#: For sanity sake, we start at 1 with column numbers
_COL_NUM_1 = 1

_ROW_NUM_1 = 1

#: max rows is 1048576 so just use 10M. Used for sort_index
_ROW_MODULUS = 10000000

class _SimpleBase(PKDict):
    def __str__(self):
        return self.pkdebug_str()

    def pkdebug_str(self):
        l = ""
        for x in "link", "value", "xl_id":
            l += f",{x}={self[x]}" if x in self else ""
        for x in "content", "title", "path":
            if x in self:
                return f"{self.__class__.__name__}({x}={self[x]}{l})"
        return f"{self.__class__.__name__}({l})"

    def _error(self, fmt, *args, **kwargs):
        # TODO: print stack
        raise AssertionError(pkdformat(fmt + "; {self}", *args, self=self, **kwargs))


class _Base(SimpleBase):
    def __init__(self, cfg):
        super().__init__()
        self.pkupdate(cfg).pksetdefault(defaults=PKDict)

    def cell(self, content_or_cell, **kwargs):
        """Convert content or a cell config to a `_Cell`

        If `content_or_cell` is a PKDict, is used to configure a cell. `kwargs` must be empty.

        If `content_or_cell` is a `_Cell`, returns itself. `kwargs` must be empty.

        Otherwise, `content_or_cell` is treated as content and `_Cell` is created with the content and `kwargs`.

        Args:
            content_or_cell (object): see above

        Returns:
            _Cell: instance
        """
        if isinstance(content_or_cell, _Cell):
            assert not kwargs
            return content_or_cell
        elif isinstance(content_or_cell, dict):
            assert not kwargs
            return _Cell(content_or_cell)
        else:
            kwargs["content"] = content_or_cell
            return _Cell(kwargs)

    def _cascade_defaults(self, parent_defaults):
        self.defaults.pksetdefault(**parent_defaults)
        for c in self._children():
            c._cascade_defaults(self.defaults)
        # TODO(robnagler): document clearing defaults with None
        for k in [k for k, v in self.defaults.items() if v is None]:
            del self.defaults[k]

    def _child(self, children, child, kwargs):
        s = child(kwargs)
        s._relations(self)
        children.append(s)
        return s

    def _compile_pass1(self):
        for c in self._children():
            c._compile_pass1()

    def _compile_pass2(self):
        for c in self._children():
            c._compile_pass2()

    def _relations(self, parent):
        self.parent = parent
        if isinstance(parent, _Sheet):
            self.sheet = parent
            self.workbook = parent.workbook
        elif isinstance(parent, Workbook):
            self.workbook = parent
        else:
            self.sheet = parent.sheet
            self.workbook = parent.workbook
        return self

    def _print(self):
        pkdlog(self)
        for c in self._children():
            c._print()


class Workbook(_Base):
    def __init__(self, **kwargs):
        """Creates Workbook

        Args:
            path (py.path): where to write the spreadsheet
            defaults (PKDict): default values, e.g. round_digits
        """
        super().__init__(kwargs)
        self.sheets = []
        # for consistency in error messages
        self.workbook = self
        self.links = PKDict()

    def xl_fmt(self, cfg):
        """Get the Excel format for cfg

        Args:
            cfg (PKDict): key values that are supported by xlsxwriter

        Returns:
            Format: object which represents format
        """
        k = str(cfg)
        return self._xl_fmt.pksetdefault(k, lambda: self.xl.add_format(cfg))[k]

    def sheet(self, **kwargs):
        """Append a sheet to a Workbook

        Args:
            title (str): label for the sheet
            defaults (PKDict): default values, e.g. round_digits
        """
        return self._child(self.sheets, _Sheet, kwargs)

    def save(self):
        try:
            self._cascade_defaults(PKDict(str_fmt="text", num_fmt="decimal"))
            self._compile_pass1()
            self._compile_pass2()
            self._xl_fmt = PKDict()
            self.xl = xlsxwriter.Workbook(str(self.path))
            for s in self.sheets:
                s._save()
            self.xl.close()
            self._xl_fmt = None
            self.xl = None
        except as Exception:
            pkdlog("workbook save failed; path={}", workbook.path)
            raise

    def _assert_link_pair(self, link, left, right):
        e = None
        for x in (
            ["fmt", left.get("fmt"), right.get("fmt")],
            ["is_decimal", left.is_decimal, right.is_decimal],
            ["type", type(left.value), type(right.value)],
            ["round_digits", left.round_digits, right.round_digits],
        ):
            if x[1] != x[2]:
                self._error(
                    "link={} {} {}={} different from {} {}={}",
                    link,
                    left,
                    x[0],
                    x[1],
                    right,
                    x[0],
                    x[2],
                )

    def _children(self):
        return self.sheets

    def _compile_pass2(self):
        super()._compile_pass2()
        for k, v in self.links.items():
            for i in range(len(v) - 1):
                self._assert_link_pair(k, v[i], v[i + 1])


class _Cell(_Base):
    def _children(self):
        return _NO_CHILDREN

    def _compile_pass1(self):
        self._compile_link1()

    def _compile_pass2(self):
        if "is_compiled" in self:
            if not self.is_compiled:
                self._error("circular referenced cell={}", self)
            return
        self.is_compiled = False
        self.expr = _Expr(self)
        # expression's value overrides defaults
        for k in "fmt", "round_digits":
            if (v := self.expr.get(k)) is not None:
                self.pksetdefault(k, v)
        self.pksetdefault(
            round_digits=lambda: self.defaults.get("round_digits", _DEFAULT_ROUND_DIGITS),
            fmt=lambda: self.defaults.get("fmt"),
        )
        self.is_decimal = self.expr.is_decimal()
        self.is_compiled = True

    def _compile_link1(self):
        if "link" in self:
            for l in [self.link] if isinstance(self.link, str) else self.link:
                if not l[0].isalnum():
                    self._error("link={} must begin with alphanumeric", l)
                self.workbook.links.setdefault(l, []).append(self)

    def _compile_link_ref(self, link):
        def _xl_id(other):
            r = ""
            if other.sheet != self.sheet:
                r = f"'{other.sheet.title}'!"
            return r + other.xl_id

        l = self.workbook.links
        if link not in l:
            self._error("link={} not found", link)
        p = None
        n = 0
        z = []
        for c in sorted(l[link], key=lambda x: x.sort_index):
            c._compile_pass2()
            n += 1
            # _ROW_MODULUS ensures a gap so columns are separated by more than "+1"
            # and this will never link the wrong column
            if (
                p is not None
                and p.sheet == c.sheet
                and p.sort_index + 1 == c.sort_index
            ):
                p = z[-1][1] = c
                continue
            z.append([c, None])
            p = c
        r = ""
        for x in z:
            if len(r):
                r += ","
            r += _xl_id(x[0])
            if x[1] is not None:
                r += ":" + _xl_id(x[1])
        # _assert_link_pair validates that the cells are the same type
        return _Operand(
            cells=l[link],
            content=r,
            count=n,
            fmt=p.get("fmt"),
            # TODO(robnagler)
            # default round_digits: if p has round_digits explicit, does not
            # matter, because target round digits overrides, always. format
            # is different, though.
            round_digits=p.round_digits,
            value=p.value if n == 1 else None,
            is_decimal=p.is_decimal,
        )

    def _save(self):
        f = _Fmt(self)
        self.sheet.width(_XL_COLS[self.col_num], f.width(self))
        f = self.workbook.xl_fmt(f)
        e = self.expr
        if e.is_formula:
            self.sheet.xl.write_formula(
                self.xl_id, formula=e.render_xl_formula(self), value=e.render_xl_value(self), cell_format=f
            )
        else:
            self.sheet.xl.write(self.xl_id, self.render_xl_value(self), f)
        if self.is_decimal:
            self.sheet.text_cells.append(self.xl_id)


class _Fmt(PKDict):
    _MAP = PKDict(
        top=PKDict(top=True),
        bold=PKDict(bold=True),
        currency="$#,##0.0",
        decimal="0.0",
        percent="0.0%",
        text="@",
    )
    _SPECIAL = re.compile("[$%]")
    _WIDTH_SLOP = 1

    def width(self, cell):
        if not cell.is_decimal:
            return len(cell.value)
        n = self._WIDTH_SLOP
        x = cell.value.as_tuple()
        i = len(x.digits) + x.exponent
        n += i
        if "," in self.num_format:
            n += i // 3
        n += cell.round_digits
        if n and self._SPECIAL.search(self.num_format):
            n += 1
        return n

    def __init__(self, cell):
        def _num(name, attr, digits):
            if digits is None:
                return attr
            if name == "percent":
                digits -= 2
            return attr.replace(
                ".0",
                "" if digits <= 0 else "." + "0" * digits,
            )

        for k in (
            "font",
            "border",
        ):
            if k in cell.defaults:
                self.update(self._MAP[cell.defaults[k]])
        for x in _SPACES.split(cell.get("fmt", "")):
            if len(x) == 0:
                continue
            f = self._MAP[x]
            if isinstance(f, dict):
                self.update(f)
            else:
                self.num_format = _num(x, f, cell.round_digits)
        if "num_format" not in self:
            h = cell.defaults["num_fmt" if cell.is_decimal else "str_fmt"]
            self.num_format = _num(h, self._MAP[h], cell.round_digits)

    def __str__(self):
        return ";".join([f"{k}={self[k]}" for k in sorted(self)])


class _Expr(SimpleBase):
    def __init__(self, content):
        def _formula():
            self.is_formula = True
            if len(content) == 0:
                self._error("empty expr")
            if not (self._operator(content) or self._link.new(content)):
                self._error("invalid op or link as first element of expr={}", content)

        def _literal():
            self.resolved_count = 1
            self.is_formula = False
            if content is None:
                content = ""
            elif isinstance(content, (float, int)):
                content = decimal.Decimal(content)
            elif not isinstance(content, (str, decimal.Decimal)):
                self._error("invalid literal type={} content={}", type(content), content)
            self.pksetdefault(py_value=content)

        if (self.is_formula := isinstance(content, (list, tuple))):
            _formula(content)
        else:
            _literal(content)
        self._content = content

    def is_decimal(self):
        return isinstance(self.py_value, decimal.Decimal)

    def render_xl_value(self, cell):
        if self.resolved_count > 1:
            raise self._error("cannot render link with operator link={} cell={}", self, cell)
        rv = self.py_value
        if isinstance(rv, decimal.Decimal):
            return _rnd(rv, cell.round_digits)
        if isinstance(rv, bool):
            return "TRUE" if rv else "FALSE"
        return rv

    def render_xl_formula(self, cell):
        if self.resolved_count > 1:
            raise self._error("cannot render link with operator link={} cell={}", self, cell)
        rv = self.xl_formula
        if self.is_decimal():
            return f"=ROUND({rv},{cell.round_digits})"
        return "=" + rv

    def _compile_operands(self, op, operands, op_spec):
        def _literal(value):
            if isinstance(value, (float, int, decimal.Decimal)):
                v = decimal.Decimal(value)
                return _Operand(
                    content=str(v),
                    count=1,
                    fmt=None,
                    round_digits=None,
                    value=v,
                    is_decimal=True,
                )
            if isinstance(value, bool):
                return _Operand(
                    content="TRUE" if value else "FALSE",
                    count=1,
                    fmt=None,
                    round_digits=None,
                    value=value,
                    is_decimal=False,
                )
            if isinstance(value, str):
                if '"' in value:
                    self._error("double quotes in string literal={}", str)
                return _Operand(
                    content=f'"{value}"',
                    count=1,
                    fmt=None,
                    round_digits=None,
                    value=value,
                    is_decimal=False,
                )
            self._error("unsupported literal={} type={}", value, type(value))



    def _operator(self, content):
        def _options(operands):
            for o in operands:
                for x in "fmt", "round_digits":
                    if o.get(x) is None:
                        continue
                    if x not in res:
                        self[x] = o[x]
                    # TODO doc that grabs the leftmost fmt or round
                    elif self[x] is not None and self[x] != o[x]:
                        self[x] = None
            return self

        if (o := _OpSpec.evaluate(value[0], value[1:], expr)):
            self.resolved_count = 1
            _options(o)
        return False


    def _xl_formula():
        if (rv := self.get("xl_formula")) is not None:
            return rv
        rv = self.py_value
        if isinstance(rv, bool):
            return "TRUE" if rv else "FALSE"
        elif isinstance(rv, str):
            return '"' + rv.sub('"', '""') + '"'
        else:
            raise AssertionError(pkdformat("unexpected value={} expr={}", rv, self))
        return rv

class _Link(SimpleBase):

    @classmethod
    def new(value, expr):
        # TODO(robnagler) document that links must begin with alnum
        if len(value) == 1 and isinstance(value[0], str) and value[0][0].isalnum():
            return _Link(value[0], expr)
        return None


class _OpSpec(SimpleBase):
    _instances = PKDict()

    def __init__(self, token, func, **kwargs):
        if token in self._instances:
            raise AssertionError(f"duplicate token={token}")
        self.token = token
        self._infix = not token.alnum()
        if isinstance(func, str):
            self._py_func = getattr(self, f"_py_func_{func}")
        else:
            self._py_func = self._py_func_default
            self._py_func_default_func = func
        if isinstance((f := self.get("_xl_func")), str):
            self._xl_func = self._xl_func_default
            self._xl_func_default_name = f
        elif self._infix:
            self._xl_func = self._xl_func_infix
        else:
            self._xl_func = self._xl_func_default
            self._xl_func_default_name = token
        self.pksetdefault(
            operand_count=(2, 2),
        )
        self._instances[token] = self

    @classmethod
    def init(cls):
        def _multi(token, func, init, xl):
            cls(token, "multi", _py_func_multi_func=func, _py_func_multi_init=init, _xl_func=xl, operand_count=(1, 65535))

        cls("%", lambda x, y: x % y, _xl_func="MOD")
        _multi("*", lambda x, y: x * y, 1, "PRODUCT")
        _multi("+": lambda x, y: x + y, 0, "SUM")
        cls("-", "minus", operand_count=(1, 2))
        cls("/", lambda x, y: x / y)
        cls("<", lambda x, y: x < y),
        cls("<=", lambda x, y: x <= y),
        cls("==", lambda x, y: x == y),
        cls(">", lambda x, y: x > y),
        cls(">=", lambda x, y: x >= y),
        cls("IF", "if", operand_count=(2, 3))


    @classmethod
    def evaluate(cls, token, operands):
        if not (self := cls._instances.get(token)):
            return False
        o = self._operands(operands)

    def _operands(self, operands):
        rv = PKDict(count=0, operands=[])
        for o in operands:
            e = _Expr(o)
            rv.operands.append(e)
            rv.count += e.resolved_count
        if self.operand_count[0] <= rv.count <= self.operand_count[1]:
            return rv
        x = (
            "; You might need to be more specific link names to avoid automatic link operand grouping."
            #TODO(robnagler) not quite right
            if max(self.operand_count[1], 2) < rv.count
            else ""
        )
        self._error(
            "invalid operand count={} operand_count={} operator={} operands={}{}",
            rv.count,
            self.operand_count,
            self,
            rv.operands,
            x,
        )

    def _multi(self, op, operands):
        v = decimal.Decimal(spec.init)
        for o in operands:
            if "cells" in o:
                for p in o.cells:
                    v = spec.func(rv, p.py_value)
            else:
                v = spec.func(rv, o.py_value)
        self.pkupdate(
            xl_formula=self._compile_op_content("multi", op, operands),
            value=v,
        )
    def _unary(self):
        # when there are other kinds, we'll handle that
        if spec != "-":
            raise AssertionError(f"unknown unary operator={spec}")
        self.pkupdate(
            xl_formula=self._xl_formula(spec, ,
            py_value=-o.py_value,
        )

    def xl_formula(self, operands):
        return self._xl_func(operands)

    def _xl_func_multi(self, operands):
        # typechec?


    def _compile_op_binary(self, op, operands):
        o = _Operand(
            content=self._compile_op_content("binary", op, operands),
            count=1,
            value=_OP_SPECS[op].func(operands[0].value, operands[1].value),
            is_decimal=_OP_SPECS[op].get("is_decimal", True),
        )
        # TODO: if the fmt is not the same, that may be ok, because no fmt (decimal)
        #      for divide, do you have a format, e.g. $/$ has no format by default.
        self._compile_op_options(o, operands)
        return o

    def _compile_op_content(self, kind, op, operands):
        if not (s := _OP_SPECS.get(op)):
            self._error("unknown op={} for operands={}", op, operands)
        if kind != s.kind:
            raise AssertionError(
                f"op={op} arg kind={kind} does not match spec={s.kind}"
            )
        if kind == "binary":
            if len(operands) != 2:
                self._error("op={} requires two distinct operands={}", op, operands)
            if "xl" in s:
                return f"{s.xl}({operands[0].content},{operands[1].content})"
            return f"{operands[0].content}{op}{operands[1].content}"
        if kind == "ternary":
            if len(operands) != 3:
                self._error("op={} requires three distinct operands={}", op, operands)
            return f"{op}({operands[0].content},{operands[1].content},{operands[2].content})"
        if kind != "multi":
            raise AssertionError(f"invalid kind={kind} op={op}")
        return f"{s.xl}(" + ",".join((o.content for o in operands)) + ")"

    def _compile_op_multi(self, op, operands):
        def _value(spec):
            rv = decimal.Decimal(spec.init)
            for o in operands:
                if "cells" in o:
                    for p in o.cells:
                        rv = spec.func(rv, p.value)
                else:
                    rv = spec.func(rv, o.value)
            return rv

        r = _Operand(count=1, is_decimal=True)
        self._compile_op_options(r, operands)
        return r.pkupdate(
            content=self._compile_op_content("multi", op, operands),
            value=_value(_OP_SPECS[op]),
        )


    def _compile_op_ternary(self, op, operands):
        o = _Operand(
            content=self._compile_op_content("ternary", op, operands),
            count=1,
            value=_OP_SPECS[op].func(
                operands[0].value, operands[1].value, operands[2].value
            ),
            # TODO(robnagler) only works with IF need a better way of determining
            is_decimal=operands[1].is_decimal,
        )
        # TODO: if the fmt is not the same, that may be ok, because no fmt (decimal)
        #      for divide, do you have a format, e.g. $/$ has no format by default.
        self._compile_op_options(o, operands)
        return o


class _Row(_Base):
    def __init__(self, cfg):
        """Creates a row"""
        super().__init__(cfg)
        self.cells = PKDict()

    def add_cell(self, col, content_or_cell, **kwargs):
        """Adds a cell to `col` in `self`

        Args:
            col (str): name of column to add
            content_or_cell (object): See `_Base.cell` for arguments
        """
        if col in self.cells:
            self._error(
                "cell={} already exists in cells={}", col, sorted(self.cells.keys())
            )
        self.cells[col] = (
            self.cell(content_or_cell, **kwargs).pkupdate(col=col)._relations(self)
        )
        return self

    def add_cells(self, *args, **kwargs):
        """Adds `values` to the row/header/footer

        For the footer, the first col must match first header

        Args:
            values (dict or list, tuple): ordered col=label/cell, where col is a keyword name or list of cells
            kwargs (dict): ordered col=label/cell
        Returns:
            self: row/header/footer
        """
        if len(args) == 0:
            # Allow empty case for call to row(), header(), etc.
            c = PKDict() if len(kwargs) == 0 else kwargs
        elif len(args) > 1:
            raise self._error("too many (>1) args={}", args)
        else:
            if isinstance(args[0], dict):
                c = PKDict(args[0])
            elif isinstance(args[0], (tuple, list)):
                # Really only useful for headers case
                c = PKDict(zip(args[0], args[0]))
            else:
                self._error("invalid cell={}", args[0])
            c.update(kwargs)
        for k, v in c.items():
            self.add_cell(k, v)
        return self

    def _children(self):
        return self.cells.values()

    def _compile_pass1(self):
        for k, v in self.cells.items():
            if k not in self.parent.cols:
                self._error("column={} does not exist; cell={}", k, v)
        s = set()
        r = self.row_num
        for i, n in enumerate(self.parent.cols, _COL_NUM_1):
            if n not in self.cells:
                self._error("column={} not found", n)
            self.cells[n].pkupdate(
                col_num=i,
                row_num=r,
                sort_index=i * _ROW_MODULUS + r,
                xl_id=f"{_XL_COLS[i]}{r}",
            )._compile_pass1()

    def _save(self):
        for c in self._children():
            c._save()


class _Footer(_Row):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.defaults.pksetdefault(border="top")


class _Header(_Row):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.defaults.pksetdefault(font="bold")


class _Sheet(_Base):
    def __init__(self, cfg):
        """Appends Sheet to Workbook

        Args:
            cfg (dict): configuration, e.g. title, defaults
        """
        super().__init__(cfg)
        self.tables = []

    def table(self, **kwargs):
        """Appends table to sheets

        Args:
            title (str): debug label for the table
            defaults (PKDict): default values, e.g. round_digits
        """
        return self._child(self.tables, _Table, kwargs)

    def width(self, col, width):
        if col not in self._col_widths or self._col_widths[col] <= width:
            self._col_widths[col] = width

    def _children(self):
        return self.tables

    def _compile_pass1(self):
        r = _ROW_NUM_1
        for t in self._children():
            r = t._compile_pass1(r)

    def _save(self):
        self.xl = self.workbook.xl.add_worksheet(self.title)
        self.text_cells = []
        self._col_widths = PKDict()
        for c in self._children():
            c._save()
        for c, w in self._col_widths.items():
            self.xl.set_column(f"{c}:{c}", width=w)
        if self.text_cells:
            # sqref is represented as list of cells separated by spaces
            self.xl.ignore_errors({"number_stored_as_text": " ".join(self.text_cells)})
        self.xl = None
        self.text_cells = None
        self._col_widths = None


class _Table(_Base):
    def __init__(self, cfg):
        """Append a table to Sheet

        The first row (be it header, row, or footer) defines the
        column names and the maximum width of the table.

        The column names must match this first row. A cell content
        may be None, which is an empty row.

        Args:
            cfg (dict): configuration, e.g. defaults
        """
        super().__init__(cfg)
        self.headers = []
        self.rows = []
        self.footers = []

    def footer(self, *args, **kwargs):
        """Append a footer

        The first footer will be separated from the table with top border.

        Args:
            cells (dict, kwargs, list): ordered col=cell; coll must match first header
        """
        return self._child(self.footers, _Footer, args, kwargs)

    def header(self, *args, **kwargs):
        """Append a header

        The first header defines the column names and the width of the table.

        Args:
            cells (dict, kwargs, list): ordered col=label, where col is a keyword name
        """
        return self._child(self.headers, _Header, args, kwargs)

    def row(self, *args, **kwargs):
        """Append a row

        Args:
            cells (dict, kwargs, list): ordered col=label, where col is a keyword name
        """
        return self._child(self.rows, _Row, args, kwargs)

    def _child(self, children, child, args, kwargs):
        return super()._child(children, child, PKDict()).add_cells(*args, **kwargs)

    def _children(self):
        return self.headers + self.rows + self.footers

    def _compile_pass1(self, row_num):
        self.first_row_num = row_num
        for r in self._children():
            if "cols" not in self:
                self.cols = tuple(r.cells.keys())
                self.col_set = frozenset(self.cols)
            r.row_num = row_num
            r._compile_pass1()
            row_num += 1
        return row_num

    def _save(self):
        for c in self._children():
            c._save()


def _init():

    global _XL_COLS, _DIGITS_TO_PLACES
    if _XL_COLS:
        return
    # really, you can 16384 columns, but we only support 702 (26 + 26*26)
    x = [chr(ord("A") + i) for i in range(26)]
    v = ([None] * _ROW_NUM_1) + x.copy()
    for c in x:
        v.extend([c + d for d in x])
    _XL_COLS = tuple(v)
    x = ("1",) + tuple(
        (("." + ("0" * i) + "1") for i in range(16)),
    )
    _DIGITS_TO_PLACES = tuple((decimal.Decimal(d) for d in x))
    _OpSpec.init()


def _rnd(v, digits):
    return v.quantize(
        _DIGITS_TO_PLACES[digits],
        rounding=decimal.ROUND_HALF_UP,
    )


_init()
