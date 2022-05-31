# -*- coding: utf-8 -*-
u"""Excel spreadsheet generator

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import decimal
import xlsxwriter


_XL_COLS = None

_NO_CHILDREN = tuple()

_DEFAULT_ROUND_DIGITS = 2

_DIGITS_TO_PLACES = None

#: For sanity sake, we start at 1 with column numbers
_COL_NUM_1 = 1

_ROW_NUM_1 = 1

#: max rows is 1048576 so just use 10M. Used for sort_index
_ROW_MODULUS = 10000000

_OP_MULTI = PKDict({
    '*': PKDict(xl='PRODUCT', func=lambda x, y: x * y, init=1),
    '+': PKDict(xl='SUM', func=lambda x, y: x + y, init=0),
})
_OP_BINARY = PKDict({
    '-': lambda x, y: x - y,
    '/': lambda x, y: x / y,
})
_OP_UNARY = PKDict({
    '-': lambda x: - x,
})

class _Base(PKDict):

    def __init__(self, cfg):
        self.pkupdate(cfg).pksetdefault(defaults=PKDict)
#expensive        self.caller = pykern.pkinspect.caller()

    def cell(self, content, **kwargs):
        kwargs['content'] = content
        return _Cell(kwargs)

    def _cascade_defaults(self, parent_defaults):
        self.defaults.pksetdefault(**parent_defaults)
        for c in self._children():
            c._cascade_defaults(self.defaults)

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

    def _error(self, fmt, *args, **kwargs):
        kwargs['self'] = self
        pkdlog(fmt + '; {self}', *args, **kwargs)
#TODO: print stack
        raise AssertionError('workbook save failed')

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

    def pkdebug_str(self):
        l = ''
        for x in 'link', 'value', 'xl_id':
            l += f',{x}={self[x]}' if x in self else ''
        for x in 'content', 'title', 'path':
            if x in self:
                return f'{self.__class__.__name__}({x}={self[x]}{l})'
        return f'{self.__class__.__name__}({l})'

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
        self._cascade_defaults(PKDict(str_fmt='text', num_fmt='decimal'))
        self._compile_pass1()
        self._compile_pass2()
        self._print()
        self._xl_fmt = PKDict()
        self.xl = xlsxwriter.Workbook(str(self.path))
        for s in self.sheets:
            s._save()
        self.xl.close()
        self._xl_fmt = None
        self.xl = None

    def _children(self):
        return self.sheets


class _Cell(_Base):

    _FMT_BASE = PKDict(
        top=PKDict(top=True),
        bold=PKDict(bold=True),
        currency='$#,##0.0',
        decimal='0.0',
        percent='0.0%',
        text='@',
    )

    def __init__(self, kwargs):
        super().__init__(kwargs)
        self._is_expr = False

    def _children(self):
        return _NO_CHILDREN

    def _compile_pass1(self):
        self._compile_link1()

    def _compile_pass2(self):
        if 'is_compiled' in self:
            if not self.is_compiled:
                self._error('circular referenced cell')
            return
        self.is_compiled = False
        self._compile_content()
        self.is_compiled = True

    def _compile_content(self):
        if self.content is None:
            self._compile_str('')
            return
        elif isinstance(self.content, (float, int)):
            self.content = decimal.Decimal(self.content)
        if isinstance(self.content, str):
            self._compile_str(self.content)
            self.content = self.value
        elif isinstance(self.content, decimal.Decimal):
            self._compile_decimal(self.content)
            self.content = self.value
        elif isinstance(self.content, (list, tuple)):
            self._compile_expr_root()
        else:
            self._error(
                'content type={} not supported',
                type(self.content),
                self,
            )

    def _compile_decimal(self, value):
        self.pksetdefault(
            round_digits=lambda: self.defaults.get('round_digits', _DEFAULT_ROUND_DIGITS),
        )
        self.value = _rnd(value, self.round_digits)
        self.content = str(self.value)
        self.is_decimal = True

    def _compile_expr(self, expr):
        if len(expr) == 0:
            self._error('empty expr')
        e = expr[0]
        if isinstance(e, (float, int, decimal.Decimal)):
            v = decimal.Decimal(e)
            return _Operand(
                content=str(v),
                count=1,
                fmt=None,
                round_digits=None,
                value=v,
                is_decimal=True,
            )
        if e[0].isalpha():
            return self._compile_ref(e, expect_count=None)
        return self._compile_op(expr)

    def _compile_expr_root(self):
        self._is_expr = True
        r = self._compile_expr(self.content)
        # expression's value overrides defaults
        for x in 'fmt', 'round_digits':
            if r.get(x) is not None:
                self.pksetdefault(x, r[x])
        if isinstance(r.value, decimal.Decimal):
            self._compile_decimal(r.value)
            self.content = f'=ROUND({r.content}, {self.round_digits})'
        elif isinstance(r.value, str):
            self._compile_str(r.value)
#TODO: should this be setting a literal string value instead of =content?
            self.content = f'={r.content}'
        else:
            raise AssertionError(f'_compile_expr invalid r={r}')

    def _compile_link1(self):
        if 'link' not in self:
            return
        self.sheet.links.setdefault(self.link, []).append(self)

    def _compile_op(self, expr):
        o = expr[0]
        e = expr[1:]
        if o == '+':
            return self._compile_operands(o, e, expect_count=None)
        if o == '-':
            if len(expr) > 2:
                return self._compile_operands(o, e, expect_count=2)
            return self._compile_operands(o, e, expect_count=1)
        if o == '*':
            return self._compile_operands(o, e, expect_count=None)
        if o == '/':
            return self._compile_operands(o, e, expect_count=2)
        self._error('operator={} not supported', o)

    def _compile_op_binary(self, op, operands):
        if len(operands) == 1:
            self._error('op={} requires two distinct operands={}', op, operands)
        l = operands[0]
        r = operands[1]
        o = _Operand(
            content=f'({l.content}{op}{r.content})',
            count=1,
            value=_OP_BINARY[op](l.value, r.value),
            is_decimal=True,
        )
#TODO: if the fmt is not the same, that may be ok, because no fmt (decimal)
#      for divide, do you have a format, e.g. $/$ has no format by default.
        self._compile_op_options(o, operands)
        return o

    def _compile_op_multi(self, op, operands):
        r = _Operand(count=1, is_decimal=True)
        c = ''
        m = _OP_MULTI[op]
        v = decimal.Decimal(m.init)
        for o in operands:
            if len(c):
                c += ','
            c += o.content
            if 'cells' in o:
                for p in o.cells:
                    v = m.func(v, p.value)
            else:
                v = m.func(v, o.value)
#TODO: fmt doesn't work with PROD, but round_digits is fine
        self._compile_op_options(r, operands)
        return r.pkupdate(
            content=f'{m.xl}({c})',
            value=v,
        )

    def _compile_op_options(self, res, operands):
        for o in operands:
            for x in 'fmt', 'round_digits':
                if o[x] is None:
                    continue
                if x not in res:
                    res[x] = o[x]
#TODO doc that grabs the leftmost fmt or round
                elif res[x] is not None and res[x] != o[x]:
                    res[x] = None
        return res

    def _compile_op_unary(self, op, operands):
        o = operands[0]
        return _Operand(
            content=f'({op}{o.content})',
            count=1,
            fmt=o.get('fmt'),
            is_decimal=True,
            round_digits=o.round_digits,
            value=_OP_UNARY[op](o.value),
        )

    def _compile_operands(self, op, operands, expect_count):
        n = 0
        z = []
        for o in operands:
            if not isinstance(o, (list, tuple)):
                o = [o]
            e = self._compile_expr(o)
            if not e.is_decimal:
                self._error('operand={e.value} must numeric for op={op}')
            z.append(e)
            n += e.count
        if expect_count is None:
            return self._compile_op_multi(op, z)
        if expect_count != n:
            self._error(
                'operator={} expecting {} operands, not operands={}',
                op,
                expect_count,
                operands,
            )
        if expect_count == 1:
            return self._compile_op_unary(op, z)
        if expect_count == 2:
            return self._compile_op_binary(op, z)
        raise AssertionError(f'incorrect expect_count={expect_count}')


    def _compile_ref(self, link, expect_count):
        l = self.sheet.links
        if link not in l:
            self._error(
                'link={} not found', link)
        p = None
        n = 0
        z = []
        for c in sorted(l[link], key=lambda x: x.sort_index):
            c._compile_pass2()
            n += 1
            # _ROW_MODULUS ensures a gap so next col is not +1
            if p is not None and p.sort_index + 1 == c.sort_index:
                p = z[-1][1] = c
                continue
            z.append([c, None])
            p = c
        r = ''
        for x in z:
            if r is not None:
                r += ','
            r = x[0].xl_id
            if x[1] is not None:
                r += ':' + x[1].xl_id
        if expect_count is not None and expect_count != n:
            self._error(
                'incorrect operands={} expect={} count={}',
                l[link],
                expect_count,
                n,
            )
        # _assert_link_pair validates that the cells are the same type
        return _Operand(
            cells=l[link],
            content=r,
            count=n,
            fmt=p.get('fmt'),
            round_digits=p.round_digits,
            value=p.value if n == 1 else None,
            is_decimal=p.is_decimal,
        )

    def _compile_str(self, value):
        self.round_digits = None
        self.value = self.content = value
        self.is_decimal = False

    def _save(self):
        f = self.workbook.xl_fmt(_Fmt(self))
        if self._is_expr:
            self.sheet.xl.write_formula(self.xl_id, self.content, value=self.value, cell_format=f)
        else:
            self.sheet.xl.write(self.xl_id, self.content, f)


class _Fmt(PKDict):

    def __init__(self, cell):

        def _num(fmt):
            if cell.round_digits is None:
                return fmt
            if cell.round_digits == 0:
                x = ''
            else:
                x = '.' + '0' * cell.round_digits
            fmt = fmt.replace('.0', x)
            return fmt

        for k in (
            'font',
            'border',
        ):
            if k in cell.defaults:
                self.update(cell._FMT_BASE[cell.defaults[k]])
        for x in cell.get('fmt', '').split(' '):
            if len(x) == 0:
                continue
            f = cell._FMT_BASE[x]
            if isinstance(f, dict):
                self.update(f)
            else:
                self.num_format = _num(f)
        if 'num_format' not in self:
            self.num_format = _num(
                cell._FMT_BASE[cell.defaults['num_fmt' if cell.is_decimal else 'str_fmt']],
            )

    def __str__(self):
        return ';'.join([f'{k}={self[k]}' for k in sorted(self)])


class _Operand(PKDict):
    pass


class _Row(_Base):

    def __init__(self, cfg):
        """Creates a row
        """
        super().__init__(cfg)
        self.cells = PKDict()

    def add_cells(self, values):
        """Adds `values` to the row/header/footer

        For the footer, the first col must match first header

        Args:
            values (dict): ordered col=label or cell, where col is a keyword name
        Returns:
            self: row/header/footer
        """
        def _cell(col, cell):
            if not isinstance(cell, _Cell):
                cell = _Cell(cell) if isinstance(cell, PKDict) else self.cell(cell)
            return cell.pkupdate(col=col)._relations(self)

        for n, c in values.items():
            if n in self.cells:
                self._error('cell={} already exists in cells={}', n, sorted(self.cells.keys()))
            self.cells[n] = _cell(n, c)
        return self

    def _children(self):
        return self.cells.values()

    def _compile_pass1(self):
        s = set()
        r = self.row_num
        for i, n in enumerate(self.parent.cols, _COL_NUM_1):
            if n not in self.cells:
                self._error('name={} not found', n)
            self.cells[n].pkupdate(
                col_num=i,
                row_num=r,
                sort_index=i * _ROW_MODULUS + r,
#TODO: support sheets
                xl_id=f'{_XL_COLS[i]}{r}',
            )._compile_pass1()

    def _save(self):
        for c in self._children():
            c._save()


class _Footer(_Row):

    def __init__(self, cfg):
        super().__init__(cfg)
        self.defaults.pksetdefault(border='top')


class _Header(_Row):

    def __init__(self, cfg):
        super().__init__(cfg)
        self.defaults.pksetdefault(font='bold')


class _Sheet(_Base):

    def __init__(self, cfg):
        """Appends Sheet to Workbook

        Args:
            cfg (dict): configuration, e.g. title, defaults
        """
        super().__init__(cfg)
        self.tables = []
        self.links = PKDict()

    def table(self, **kwargs):
        """Appends table to sheets

        Args:
            title (str): debug label for the table
            defaults (PKDict): default values, e.g. round_digits
        """
        return self._child(self.tables, _Table, kwargs)


    def _assert_link_pair(self, link, left, right):
        e = None
        for x in (
            ['fmt', left.get('fmt'), right.get('fmt')],
            ['is_decimal', left.is_decimal, right.is_decimal],
            ['type', type(left.value), type(right.value)],
            ['round_digits', left.round_digits, right.round_digits],
        ):
            if x[1] != x[2]:
                self._error(
                    'link={} {} {}={} different from {} {}={}',
                    link,
                    left,
                    x[0],
                    x[1],
                    right,
                    x[0],
                    x[2],
                )

    def _children(self):
        return self.tables

    def _compile_pass1(self):
        r = _ROW_NUM_1
        for t in self._children():
            r = t._compile_pass1(r)

    def _compile_pass2(self):
        super()._compile_pass2()
        for k, v in self.links.items():
            for i in range(len(v) - 1):
                self._assert_link_pair(k, v[i], v[i + 1])

    def _save(self):
        self.xl = self.workbook.xl.add_worksheet(self.title)
        for c in self._children():
            c._save()
        self.xl = None

#TODO: save column width
#  width  max(w.setdefault(y, 0), (len(str(int(x))) + 5) if isinstance(x, float) else len(str(x)))
        # s.set_column(f'{c}:{c}', y)
        # sqref is represented as list of cells separated by spaces
#            if v.fmt == self.TEXT_FMT:
#                i.append(c)
#        if i:
#            s.ignore_errors({'number_stored_as_text': ' '.join(i)})

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
            cells (dict or kwargs): ordered col=cell; coll must match first header
        """
        return self._child(self.footers, _Footer, args, kwargs)

    def header(self, *args, **kwargs):
        """Append a header

        Args:
            cells (dict or kwargs): ordered col=label, where col is a keyword name
        """
        return self._child(self.headers, _Header, args, kwargs)

    def row(self, *args, **kwargs):
        """Append a header

        The first header defines the column names and the width of the table.

        Args:
            cells (dict or kwargs): ordered col=label, where col is a keyword name
        """
        return self._child(self.rows, _Row, args, kwargs)

    def _child(self, children, child, args, kwargs):
        if len(args) == 0:
            c = PKDict() if len(kwargs) == 0 else kwargs
        elif len(args) > 1:
            raise self._error('too many (>1) args={}', args)
        else:
            c = PKDict(args[0])
            c.update(kwargs)
        return super()._child(children, child, PKDict()).add_cells(c)

    def _children(self):
        return self.headers + self.rows + self.footers

    def _compile_pass1(self, row_num):
        self.first_row_num = row_num
        for r in self._children():
            if 'cols' not in self:
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
    x = [chr(ord('A') + i) for i in range(26)]
    v = ([None] * _ROW_NUM_1) + x.copy()
    for c in x:
        v.extend([c + d for d in x])
    _XL_COLS = tuple(v)
    x = ('1',) + tuple(
        (('.' + ('0' * i) + '1') for i in range(16)),
    )
    _DIGITS_TO_PLACES = tuple((decimal.Decimal(d) for d in x))


def _rnd(v, digits):
    return v.quantize(
        _DIGITS_TO_PLACES[digits],
        rounding=decimal.ROUND_HALF_UP,
    )


_init()