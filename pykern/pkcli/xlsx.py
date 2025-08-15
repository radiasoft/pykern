"""manipulate Excel spreadsheets

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pandas
import pykern.pkcli
import pykern.pkio


def to_csv(xlsx_path, sheet=None, csv_path=None):
    """Dump sheets from xlsx_path

    Args:
        xlsx_path (str or py.path): what to parse
        sheet (str or int): dump a specfic sheet [None: all]
        csv_path (str or py.path): where to write [base#N.csv]
    Returns:
        tuple: list of csv files created
    """
    return ToCSV(xlsx_path, sheet, csv_path).result


class ToCSV:

    def __init__(self, xlsx_path, sheet, csv_path):
        if csv_path is not None:
            csv_path = pykern.pkio.py_path(csv_path)
        self._xlsx_path = pykern.pkio.py_path(xlsx_path)
        self._xlsx = pandas.ExcelFile(str(self._xlsx_path))
        self._csv_path = csv_path or self._xlsx_path
        self.result = (
            tuple(self._multiple()) if sheet is None else (self._one(sheet, csv_path),)
        )

    def _multiple(self):
        for i in range(len(self._xlsx.sheet_names)):
            yield self._one(i, None)

    def _one(self, sheet, csv_path):
        if csv_path is None:
            csv_path = self._csv_path.new(
                purebasename=f"{self._csv_path.purebasename}#{sheet}",
                ext=".csv",
            )
        try:
            sheet = int(sheet)
        except ValueError:
            pass
        d = self._xlsx.parse(index_col=None, sheet_name=sheet)
        d.columns = d.columns.map(lambda c: "" if "Unnamed" in str(c) else str(c))
        d.to_csv(
            str(csv_path),
            encoding="utf-8",
            index=False,
            lineterminator="\r\n",
        )
        return csv_path
