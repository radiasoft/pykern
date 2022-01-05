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

class _Base(PKDict):

    def __init__(self, cfg):
        self.pkupdate(cfg).pksetdefault(defaults=PKDict)
#expensive        self.caller = pykern.pkinspect.caller()

    def cell(self, content, **kwargs):
        kwargs['content'] = content
        return _Cell(kwargs)

    def _child(self, children, child, kwargs):
        s = child(kwargs)
        s.parent = self
        children.append(s)
        return s

    def _compile_pass1(self, parent_defaults):
        self.defaults.pksetdefault(**parent_defaults)
        for c in self._children():
            c._compile_pass1(self.defaults)

    def _error(self, *args, **kwargs):
        pkdlog(*args, **kwargs)
#TODO: print stack
        raise AssertionError('workbook save failed')

    def pkdebug_str(self):
        l = f',link={self.link}' if 'link' in self else ''
        for x in 'content', 'title', 'path':
            if x in self:
                return f'{self.__class__.__name__}({x}={self[x]}{l})'
        return f'{self.__class__.__name__}({l})'


class Workbook(_Base):

    def __init__(self, **kwargs):
        """Creates Workbook

        Args:
            path (py.path): where to write the spreadsheet
            defaults (PKDict): default values, e.g. round_digits
        """
        super().__init__(kwargs)
        self.sheets = []

    def sheet(self, **kwargs):
        """Append a sheet to a Workbook

        Args:
            title (str): label for the sheet
            defaults (PKDict): default values, e.g. round_digits
        """
        return self._child(self.sheets, _Sheet, kwargs)

    def save(self):
        self._compile_pass1(PKDict())
        self._compile_pass2()
        return
        w = xlsxwriter.Workbook(str(self.path))
        for s in self.sheets:
            s._save(w.add_worksheet(s.title))
        w.close()

    def _children(self):
        return self.sheets

    def _compile_pass2(self):
        for s in self._children():
            s._compile_pass2()
        # number cells col, row

        # create all links in all spreadsheets
        # compute configuration defaults and classes
        # don't apply defaults yet, because need to inherit from linked cells

        # create formats logically so can share
        # use linked cells


class _Cell(_Base):

    def __init__(self, kwargs):
        super().__init__(kwargs)

    def _children(self):
        return _NO_CHILDREN

    def _compile_pass1(self, parent_defaults):
        super()._compile_pass1(parent_defaults)
        self._compile_link()

    def _compile_pass2(self):
        if 'is_compiled' in self:
            if not self.is_compiled:
                self._error('circular referenced cell to {}', self)
            return
        self.is_compiled = False
        self._compile_content()
        self.is_compiled = True

    def _compile_content(self):
        if self.content is None:
            self._compile_str('')
        elif isinstance(self.content, (float, int)):
            self.content = decimal.Decimal(self.content)
        if isinstance(self.content, str):
            self._compile_str(self.content)
        elif isinstance(self.content, decimal.Decimal):
            self._compile_decimal(self.content)
        elif isinstance(self.content, (list, tuple)):
            self._compile_expr_root()
        else:
            self._error(
                'content type={} not supported; {}',
                type(self.content),
                self,
            )

    def _compile_decimal(self, value):
        self.pksetdefault(
            round_digits=lambda: self.defaults.get('round_digits', _DEFAULT_ROUND_DIGITS),
            fmt=lambda: self.defaults.get('decimal_fmt', 'number'),
        )
        self.value = _rnd(self.content, self.round_digits)

    def _compile_expr(self, expr):
        if len(expr) <= 0:
            self._error('empty expr in {}', self)
        if expr[0] in ('+', '-', '*', '/'):
            return self._compile_op(expr)
        elif expr[0][0].isalpha():
            if len(expr) != 1:
                self._error(
                    'simple link expr={} must only contain link={}; {}',
                    expr,
                    expr[0],
                    self,
                )
            return self._compile_ref(expr[0])
        else:
            self._error('expr={} not supported; {}', expr, self)

    def _compile_expr_root(self):
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
            self.content = f'={r.content}'
        else:
            raise AssertionError(f'_compile_expr invalid r={r}')

    def _compile_link(self):
        if 'link' not in self:
            return
        # Row.Table.Sheet
        l = self.parent.parent.parent.links
#TODO: support multiple links in a table
        if self.link in l:
            self._error(
                'duplicate link={} in {} and {}', self.link, l[self.link], self)
        l[self.link] = self

    def _compile_ref(self, link):
        l = self.parent.parent.parent.links
        if link not in l:
            self._error(
                'link={} not found for {}', link, self)
        c = l[link]
        # ensure it is compiled
        c._compile_pass2()
#TODO: support multiple links in a table
        x = f'{self.xl_col}{self.row_num}'
        if c.parent.parent.parent != self.parent.parent.parent:
            x = f'{c.parent.parent.parent.title}!{x}'
        return PKDict(
            value=c.value,
            content=x,
            fmt=c.fmt,
        )

    def _compile_str(self, value):
        self.pksetdefault(fmt=lambda: self.defaults.get('str_fmt', 'text'))
        self.value = value


class _Row(_Base):

    def __init__(self, cells):
        """Creates a row of cells

        Args:
            cells (dict): ordered col=cell; coll must match first header
        """
        def _cell(col, cell):
            if not isinstance(cell, _Cell):
                cell = _Cell(cell) if isinstance(cell, PKDict) else self.cell(cell)
            return cell.pkupdate(col=col, parent=self)

        super().__init__(
            PKDict(
                cells=PKDict(
                    {n: _cell(n, c) for n, c in cells.items()},
                ),
            ),
        )

    def _children(self):
        return self.cells.values()

    def _compile_pass2(self):
        s = set()
        for i, n in enumerate(self.parent.cols):
            if n not in self.cells:
                self._error('{} not found in {}', n, self)
            self.cells[n].pkupdate(
                row_num=self.row_num,
                col_num=i,
                xl_col=_XL_COLS[i],
            )._compile_pass2()


class _Footer(_Row):
# how to pass on defaults. That may be just rendering.
    pass


class _Header(_Row):
    pass


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


    def _children(self):
        return self.tables

    def _compile_pass2(self):
        r = 1
        for t in self._children():
            r = t._compile_pass2(r)

#    def _save(self, xl):
#        if fmt == self.TEXT_FMT:
#            number_stored_as_text.append(c)
#        for
## Sheet2!A1
#
#        # set width
#        # we know width of floats, decimals because they are already rounded
#
##  width  max(w.setdefault(y, 0), (len(str(int(x))) + 5) if isinstance(x, float) else len(str(x)))
#        for c, v in self._data.items():
#            f = _fmt(v.fmt)
#            x = _val(v.content)
#            if isinstance(x, str) and x.startswith('='):
#                s.write_formula(c, x, cell_format=f, value=_val(v.value))
#            else:
#                s.write(c, x, f)
#            if v.value is None:
#                continue
#            if v.fmt == self.TEXT_FMT:
#                i.append(c)
#            y = c[0:1]
#            #TODO(robnagler): 5 accounts for $,.00, but it's not quite right
#            #TODO(robnagler) probably want even columns for tab columns so just have a global min
#            x = _val(v.value)
#            w[y] = max(w.setdefault(y, 0), (len(str(int(x))) + 5) if isinstance(x, float) else len(str(x)))
#        for c, y in w.items():
#            s.set_column(f'{c}:{c}', y)
#        # sqref is represented as list of cells separated by spaces
#        if i:
#            s.ignore_errors({'number_stored_as_text': ' '.join(i)})
#
#
#            xl.set_column(f'{c}:{c}', y)
#        # sqref is represented as list of cells separated by spaces
#        if number_stored_as_text:
#            s.ignore_errors({'number_stored_as_text': ' '.join(number_stored_as_text)})
#

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

    def footer(self, **cells):
        """Append a footer

        The first footer will be separated from the table with top border.

        Args:
            cells (dict): ordered col=cell; coll must match first header
        """
        return self._child(self.footers, _Footer, cells)

    def header(self, **cells):
        """Append a header

        Args:
            cells (dict): ordered col=label, where col is a keyword name
        """
        return self._child(self.headers, _Header, cells)

    def row(self, **cells):
        """Append a header

        The first header defines the column names and the width of the table.

        Args:
            cells (dict): ordered col=label, where col is a keyword name
        """
        return self._child(self.rows, _Row, cells)

    def _children(self):
        return self.headers + self.rows + self.footers

    def _compile_pass2(self, row_num):
        self.first_row_num = row_num
        for r in self._children():
            if 'cols' not in self:
                self.cols = tuple(r.cells.keys())
                self.col_set = frozenset(self.cols)
            r.row_num = row_num
            r._compile_pass2()
            row_num += 1
        return row_num


def _init():
    global _XL_COLS, _DIGITS_TO_PLACES
    if _XL_COLS:
        return
    # really, you can 16384 columns, but we only support 702 (26 + 26*26)
    x = [chr(ord('A') + i) for i in range(26)]
    v = x.copy()
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
