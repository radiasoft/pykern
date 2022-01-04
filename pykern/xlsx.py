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

    def _compile_defaults(self, parent_defaults):
        self.defaults.pksetdefault(**parent_defaults)
        for c in self._children():
            c._compile_defaults(self.defaults)

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
        self._compile_defaults(PKDict())
        self._compile()
        return
        w = xlsxwriter.Workbook(str(self.path))
        for s in self.sheets:
            s._save(w.add_worksheet(s.title))
        w.close()

    def _children(self):
        return self.sheets

    def _compile(self):
        for s in self.sheets:
            s._compile()
        # number cells col, row

        # create all links in all spreadsheets
        # compute configuration defaults and classes
        # don't apply defaults yet, because need to inherit from linked cells

        # create formats logically so can share
        # use linked cells


class _Cell(_Base):

    def __init__(self, kwargs):
        super().__init__(kwargs)

    def _compile(self):
        if 'is_compiled' in self:
            if not self.is_compiled:
                self._error('circular referenced cell to {}', self)
            return
        self.is_compiled = False
        self._compile_link()
        self._compile_content()
        self.is_compiled = True

    def _compile_content(self):
        if self.content is None:
#TODO: should this be empty cell?
            self.content = ''
        elif isinstance(self.content, float):
            self.content = decimal.Decimal(self.content)
        if isinstance(self.content, str):
            self.pksetdefault(fmt=lambda: self.defaults.get('str_fmt', 'text'))
        elif isinstance(self.content, int):
            self.pksetdefault(fmt=lambda: self.defaults.get('int_fmt', 'number'))
        elif isinstance(self.content, decimal.Decimal):
            self.pksetdefault(
                round_digits=lambda: self.defaults.get('round_digits', _DEFAULT_ROUND_DIGITS),
                fmt=lambda: self.defaults.get('decimal_fmt', 'number'),
            )
            self.content = _rnd(self.content, self.round_digits)
        elif isinstance(self.content, (list, tuple)):
            self._compile_expression(self.content)
        else:
            self._error(
                'content type={} not supported; {}',
                type(self.content),
                self,
            )

    def _compile_expression(self, expression):
        if len(expression) <= 0:
            self._error('empty expression in {}', self)
        if expression[0] in ('+', '-', '*', '/'):
            compute
        elif expression[0][0].isalpha():
            if len(expression) != 1:
                self._error('simple link expression={} must only contain link {}', expression, self)
            c = self._link(expression[0])
            is is compiled?
            value already rounded and row/col
        for e in expression:

            if isinstance(e, (list, tuple)):
                self._compile_expression(

    def _compile_link(self):
        # Row.Table.Sheet
        l = self.parent.parent.parent.links
        if self.link in l:
            self._error(
                'duplicate link={} in {} and {}', self.link, l[self.linkx], self)
        l[self.link] = self

    def _link(self, link):
        l = self.parent.parent.parent.links
        if link not in l:
            self._error(
                'link={} not found for {}', link, self)
        return l[link]

    def _children(self):
        return _NO_CHILDREN


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

    def _compile(self):
        s = set()
        for i, n in enumerate(self.parent.cols):
            if n not in self.cells:
                self._error('{} not found in {}', n, self)
            self.cells[n].pkupdate(
                row_num=self.row_num,
                col_num=i,
                xl_col=_XL_COLS[i],
            )._compile()


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

    def _compile(self):
        r = 1
        for t in self.tables:
            r = t._compile(r)

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

    def _compile(self, row_num):
        self.first_row_num = row_num
        for r in self._children():
            if 'cols' not in self:
                self.cols = tuple(r.cells.keys())
                self.col_set = frozenset(self.cols)
            r.row_num = row_num
            r._compile()
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
