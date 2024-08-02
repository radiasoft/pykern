"""Excel spreadsheet generator

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdformat
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

# max range of operands for SUM, AND, etc.
_MULTI_COUNT = (1, 65535)


class _SimpleBase(PKDict):
    def __str__(self):
        return self.pkdebug_str()

    def pkdebug_str(self):
        l = ""
        for x in "link", "value", "xl_id":
            l += f",{x}={self[x]}" if x in self else ""
        for x in "content", "title", "path", "token", "_content":
            if x in self:
                return f"{self.__class__.__name__}({x}={self[x]}{l})"
        return f"{self.__class__.__name__}({l})"

    def _error(self, fmt, *args, **kwargs):
        # TODO: print stack
        raise AssertionError(pkdformat(fmt + "; {self}", *args, self=self, **kwargs))


class _Base(_SimpleBase):
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
        except Exception:
            pkdlog("workbook save failed; path={}", self.workbook.path)
            raise

    def _assert_link_pair(self, link, left, right):
        e = None
        for x in (
            ["fmt", left.get("fmt"), right.get("fmt")],
            ["is_decimal", left.is_decimal, right.is_decimal],
            ["type", type(left.expr.py_value()), type(right.expr.py_value())],
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
    def compile_pass2_for_link_ref(self):
        self._compile_pass2()

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
        self.expr = _Expr(self.content, self)
        # expression's value overrides defaults
        for k in "fmt", "round_digits":
            if (v := self.expr.get(k)) is not None:
                self.pksetdefault(k, v)
        self.pksetdefault(
            round_digits=lambda: self.defaults.get(
                "round_digits", _DEFAULT_ROUND_DIGITS
            ),
        )
        if (v := self.defaults.get("fmt")) is not None:
            self.pksetdefault(fmt=v)
        self.is_decimal = self.expr.is_decimal()
        self.is_compiled = True

    def _compile_link1(self):
        if "link" in self:
            for l in [self.link] if isinstance(self.link, str) else self.link:
                if not l[0].isalnum():
                    self._error("link={} must begin with alphanumeric", l)
                self.workbook.links.setdefault(l, []).append(self)

    def _save(self):
        f = _Fmt(self)
        self.sheet.width(_XL_COLS[self.col_num], f.width(self))
        f = self.workbook.xl_fmt(f)
        e = self.expr
        if e.is_formula:
            self.sheet.xl.write_formula(
                self.xl_id,
                formula=e.xl_formula_for_cell(self),
                value=e.xl_value_for_cell(self),
                cell_format=f,
            )
        else:
            self.sheet.xl.write(self.xl_id, e.xl_value_for_cell(self), f)
        if self.is_decimal:
            self.sheet.text_cells.append(self.xl_id)


class _Expr(_SimpleBase):
    def __init__(self, content, cell):
        def _formula():
            self.cell = cell
            self.is_formula = True
            self._is_decimal = False
            if len(content) == 0:
                self._error("empty expr")
            if not (self._operator(content) or self._link_ref(content)):
                self._error("invalid op or link as first element of expr={}", content)

        def _literal():
            nonlocal content

            self.resolved_count = 1
            self.is_formula = False
            if content is None:
                content = ""
            elif isinstance(content, (bool, str, decimal.Decimal)):
                # must be here, because bool is a subclass of int
                pass
            elif isinstance(content, (float, int)):
                content = decimal.Decimal(content)
            else:
                self._error(
                    "invalid literal type={} content={}", type(content), content
                )
            self.pksetdefault(
                _py_value=content,
                _is_decimal=isinstance(content, decimal.Decimal),
            )

        pkdc("{}!{}={}", cell.sheet.title, cell.xl_id, content)
        self.is_formula = isinstance(content, (list, tuple))
        if self.is_formula:
            _formula()
        else:
            _literal()
        self._content = content

    def is_decimal(self):
        return self._is_decimal or isinstance(self.py_value(), decimal.Decimal)

    def py_value(self):
        if (rv := self.get("_py_value")) is None:
            self._error("expected an expression with a single value expr={}", self)
        if callable(rv):
            self._py_value = rv = rv()
        if not isinstance(rv, (bool, str, decimal.Decimal)):
            self._error("unexpected expression value={} expr={}", rv, self)
        return rv

    def xl_formula(self):
        if self.is_formula:
            return self._xl_formula
        rv = self.py_value()
        if isinstance(rv, bool):
            return "TRUE" if rv else "FALSE"
        elif isinstance(rv, str):
            return '"' + rv.replace('"', '""') + '"'
        elif isinstance(rv, decimal.Decimal):
            return str(rv)
        raise AssertionError(pkdformat("unexpected value={} expr={}", rv, self))

    def xl_formula_for_cell(self, cell):
        if self.resolved_count > 1:
            raise self._error(
                "cannot render link with operator link={} cell={}", self, cell
            )
        rv = self._xl_formula
        if self.is_decimal():
            rv = f"ROUND({rv},{cell.round_digits})"
        return f"={rv}"

    def xl_value_for_cell(self, cell):
        if self.resolved_count > 1:
            raise self._error(
                "cannot render link with operator link={} cell={}", self, cell
            )
        rv = self.py_value()
        if isinstance(rv, decimal.Decimal):
            return _rnd(rv, cell.round_digits)
        if isinstance(rv, bool):
            return "TRUE" if rv else "FALSE"
        return rv

    def _link_ref(self, content):
        def _compile():
            l = self.cell.workbook.links
            if content[0] not in l:
                self._error("link={} not found cell={}", content, self.cell)
            rv = PKDict(
                cells=l[content[0]],
                last_cell=None,
                pairs=[],
                resolved_count=0,
            )
            for c in sorted(rv.cells, key=lambda x: x.sort_index):
                c.compile_pass2_for_link_ref()
                rv.resolved_count += 1
                # _ROW_MODULUS ensures a gap so columns are separated by more than "+1"
                # and this will never link the wrong column
                if (
                    rv.last_cell is not None
                    and rv.last_cell.sheet == c.sheet
                    and rv.last_cell.sort_index + 1 == c.sort_index
                ):
                    rv.last_cell = rv.pairs[-1].last = c
                    continue
                rv.pairs.append(PKDict(first=c, last=None))
                rv.last_cell = c
            return rv

        def _xl_formula(pairs):
            rv = ""
            for p in pairs:
                if len(rv):
                    rv += ","
                rv += _xl_id(p.first)
                if p.last is not None:
                    rv += ":" + _xl_id(p.last)
            return rv

        def _xl_id(cell):
            r = ""
            if cell.sheet != self.cell.sheet:
                r = f"'{cell.sheet.title}'!"
            return r + cell.xl_id

        if not (
            len(content) == 1
            and isinstance(content[0], str)
            and content[0][0].isalnum()
        ):
            return False
        c = _compile()
        # _assert_link_pair validates that the cells are the same type, fmt, round_digits
        l = c.last_cell
        self.pkupdate(
            _link_ref=content,
            _is_decimal=l.expr.is_decimal(),
            _py_value=(lambda: l.expr.py_value()) if c.resolved_count == 1 else None,
            _xl_formula=_xl_formula(c.pairs),
            cells=c.cells,
            resolved_count=c.resolved_count,
        )
        self._options([l])
        return True

    def _operator(self, content):
        if not (o := _OpSpec.find(content[0])):
            return False
        self.update(o.evaluate(content[1:], self))
        self._options(self._operands.exprs)
        return True

    # TODO(robnagler) doesn't work with "if" or bool ops
    # Needs to be more logical. Works for links, because they are always consistent
    # operators should cascade values
    def _options(self, exprs_or_cells):
        for k in "fmt", "round_digits":
            if self.get(k) is not None:
                continue
            for x in exprs_or_cells:
                if (v := x.get(k)) is None:
                    continue
                if k not in self:
                    self[k] = v
                # TODO doc that grabs the leftmost fmt or round, or throws away
                elif self[k] is not None and self[k] != v:
                    del self[k]
                    break


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
    _WIDTH_BOOL = max(len("TRUE"), len("FALSE"))

    def width(self, cell):
        v = cell.expr.py_value()
        if not cell.is_decimal:
            return self._WIDTH_BOOL if isinstance(v, bool) else len(v)
        n = self._WIDTH_SLOP
        x = v.as_tuple()
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


class _OpSpec(_SimpleBase):
    _instances = PKDict()

    def __init__(self, token, func, **kwargs):
        if token in self._instances:
            raise AssertionError(f"duplicate token={token}")
        super().__init__(kwargs)
        self.pksetdefault(
            _infix=False,
            _is_multi=False,
            operand_count=(2, 2),
            token=token,
        )
        if isinstance(func, str):
            self._py_func = getattr(self, f"_py_func_{func}")
        else:
            self._py_func = self._py_func_binary
            self._py_func_binary_func = func
        if isinstance((f := self.get("_xl_func")), str):
            if x := getattr(self, f"_xl_func_{f}", None):
                self._xl_func = x
            else:
                self._xl_func = self._xl_func_default
                self._xl_func_default_name = f
        elif self._infix:
            self._xl_func = self._xl_func_infix
        else:
            self._xl_func = self._xl_func_default
            self._xl_func_default_name = token
        if isinstance(self._is_decimal, str):
            self._is_decimal = getattr(self, f"_is_decimal_{self._is_decimal}")
        self._instances[token] = self

    @classmethod
    def init(cls):

        def _compare(token, func):
            return cls(token, func, _is_decimal=False, _infix=True)

        def _multi(token, func, init=None, xl=None):
            return cls(
                token,
                "multi",
                _py_func_multi_func=func,
                _py_func_multi_init=(
                    decimal.Decimal(init) if isinstance(init, int) else init
                ),
                _xl_func=xl or token,
                operand_count=_MULTI_COUNT,
                _is_multi=True,
                _is_decimal=True,
            )

        cls("%", lambda x, y: x % y, _xl_func="MOD", _is_decimal=True)
        _multi("*", lambda rv, y: rv * y, 1, "PRODUCT")
        _multi("+", lambda rv, y: rv + y, 0, "SUM")
        _multi("MAX", max)
        _multi("MIN", min)
        cls(
            "-",
            "minus",
            operand_count=(1, 2),
            _is_decimal=True,
            _infix=True,
            _xl_func="minus",
        )
        cls("/", lambda x, y: x / y, _is_decimal=True, _infix=True)
        _compare("<", lambda x, y: x < y)
        _compare("<=", lambda x, y: x <= y)
        _compare("==", lambda x, y: x == y)
        _compare(">", lambda x, y: x > y)
        _compare(">=", lambda x, y: x >= y)
        cls("AND", "and", operand_count=_MULTI_COUNT, _is_decimal=False)
        cls("OR", "or", operand_count=_MULTI_COUNT, _is_decimal=False)
        cls("NOT", "not", operand_count=(1, 1), _is_decimal=False)
        cls("IF", "if", operand_count=(2, 3), _is_decimal="if")

    @classmethod
    def find(cls, token):
        return cls._instances.get(token)

    def evaluate(self, operands, cell):
        o = self._operands(operands, cell)
        return PKDict(
            _is_decimal=(
                self._is_decimal
                if isinstance(self._is_decimal, bool)
                else self._is_decimal(o)
            ),
            _op_spec=self,
            _operands=o,
            _py_value=lambda: self._py_func(o),
            _xl_formula=self._xl_func(o),
            resolved_count=1,
        )

    def _is_decimal_if(self, operands):
        if len(operands.exprs) != 3:
            return False
        return operands.exprs[0].is_decimal() and operands.exprs[1].is_decimal()

    def _operands(self, operands, expr):
        def _count_ok(rv):
            if self._is_multi:
                return self.operand_count[0] <= rv.count <= self.operand_count[1]
            return (
                self.operand_count[0] <= len(rv.exprs) <= self.operand_count[1]
                and len(rv.exprs) == rv.count
            )

        rv = PKDict(count=0, exprs=[])
        for o in operands:
            e = _Expr(o, expr.cell)
            rv.exprs.append(e)
            rv.count += e.resolved_count
        if not _count_ok(rv):
            self._operands_error(rv)
        return rv

    def _operands_error(self, operands):
        x = (
            "; You might need to be more specific link names to avoid automatic link operand grouping."
            # TODO(robnagler) not quite right
            if max(self.operand_count[1], 2) < operands.count
            else ""
        )
        self._error(
            "invalid operand count={} operand_count={} operator={} operands={}{}",
            operands.count,
            self.operand_count,
            self,
            operands.exprs,
            x,
        )

    def _py_func_and(self, operands):
        for e in operands.exprs:
            if not e.py_value():
                return False
        return True

    def _py_func_binary(self, operands):
        return self._py_func_binary_func(
            operands.exprs[0].py_value(), operands.exprs[1].py_value()
        )

    def _py_func_if(self, operands):
        if operands.exprs[0].py_value():
            return operands.exprs[1].py_value()
        if len(operands.exprs) == 2:
            return False
        return operands.exprs[2].py_value()

    def _py_func_minus(self, operands):
        if len(operands.exprs) == 1:
            return -operands.exprs[0].py_value()
        return operands.exprs[0].py_value() - operands.exprs[1].py_value()

    def _py_func_multi(self, operands):
        def _iter():
            for e in operands.exprs:
                if "cells" in e:
                    for c in e.cells:
                        yield c.expr, c.expr.py_value()
                else:
                    yield e, e.py_value()

        rv = self._py_func_multi_init
        for e, v in _iter():
            if not isinstance(v, decimal.Decimal):
                self._error(
                    "not decimal operand type={} value={} operand={}", type(v), v, e
                )
            rv = v if rv is None else self._py_func_multi_func(rv, v)
        return rv

    def _py_func_not(self, operands):
        return not operands.exprs[0].py_value()

    def _py_func_or(self, operands):
        for e in operands.exprs:
            if e.py_value():
                return True
        return False

    def _xl_func_default(self, operands):
        return (
            f"{self._xl_func_default_name}("
            + ",".join((o.xl_formula() for o in operands.exprs))
            + ")"
        )

    def _xl_func_infix(self, operands):
        return f"{self._xl_infix(operands.exprs[0])}{self.token}{self._xl_infix(operands.exprs[1])}"

    def _xl_func_minus(self, operands):
        if len(operands.exprs) == 1:
            return f"{self.token}{self._xl_infix(operands.exprs[0])}"
        return self._xl_func_infix(operands)

    def _xl_infix(self, expr):
        rv = expr.xl_formula()
        return f"({rv})" if expr.pkunchecked_nested_get("op_spec._infix") else rv


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

    def blank_table(self):
        """Create a table with one row, which is blank"""
        self.table(title=f"blank_table-{len(self.tables)}").row()

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
