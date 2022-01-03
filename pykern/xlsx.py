# -*- coding: utf-8 -*-
u"""Excel spreadsheet generator

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkinspect
import xlsxwriter

_XL_COLS = None


class _Base(PKDict):

    def __init__(self, cfg):
        self.pkupdate(cfg)
#expensive        self.caller = pykern.pkinspect.caller()

    def cell(self, content, **kwargs):
        kwargs['content'] = content
        return _Cell(kwargs)

    def _child(self, children, child, kwargs):
        s = child(kwargs)
        s.parent = self
        children.append(s)
        return s

    def _error(self, *args, **kwargs):
        pkdlog(*args, **kwargs)
#TODO: print stack
        raise AssertionError('workbook save failed')

    def pkdebug_str(self):
        for x in 'content', 'title', 'path':
            if x in self:
                return f'{self.__class__.__name__}({x}={self[x]})'
        return f'{self.__class__.__name__}()'


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
z        """
        return self._child(self.sheets, _Sheet, kwargs)

    def save(self):
        self._compile()
        return
        w = xlsxwriter.Workbook(str(self.path))
        for s in self.sheets:
            s._save(w.add_worksheet(s.title))
        w.close()

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
        pkdp(self)
        # create all links in all spreadsheets
        # compute defaults


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

        self.cells = PKDict(
            {n: _cell(n, c) for n, c in cells.items()},
        )

    def _compile(self):
        s = set()
        for i, n in enumerate(self.parent.cols):
            if n not in self.cells:
                self._error('{} not found in {}', n, self)
            self.cells[n].pkupdate(
                row=self.row,
                col=i,
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

    def table(self, **kwargs):
        """Appends table to sheets

        Args:
            title (str): debug label for the table
            defaults (PKDict): default values, e.g. round_digits
        """
        return self._child(self.tables, _Table, kwargs)


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

    def _compile(self, row):
        self.first_row = row
        for x in self.headers, self.rows, self.footers:
            for r in x:
                if 'cols' not in self:
                    self.cols = tuple(r.cells.keys())
                    self.col_set = frozenset(self.cols)
                r.row = row
                r._compile()
                row += 1
        return row


def _init():
    global _XL_COLS
    if _XL_COLS:
        return
    # really, you can 16384 columns, but we only support 702 (26 + 26*26)
    x = [chr(ord('A') + i) for i in range(26)]
    v = x.copy()
    for c in x:
        v.extend([c + d for d in x])
    _XL_COLS = tuple(v)


_init()
