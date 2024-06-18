"""test xlsx

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_1():
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    import pykern.pkio
    import pykern.pkrunpy
    import pykern.pkunit
    import sys
    import xml.dom.minidom
    import zipfile

    # If you see a failure, xmllint is helpful:
    #   xmllint --format worksheets/sheet1.xml
    for d in pykern.pkunit.case_dirs():
        with pykern.pkunit.ExceptToFile():
            p = "workbook.xlsx"
            m = pykern.pkrunpy.run_path_as_module("case.py")
            with zipfile.ZipFile(m.PATH, "r") as z:
                z.extractall()


# TODO(robnagler) once we switch to python 3.8+
#                for i in z.infolist():
#                    p = pykern.pkio.py_path(i.filename)
#                    pykern.pkio.mkdir_parent_only(p)
#                    p.write(
#                        xml.dom.minidom.parseString(z.read(i)).toprettyxml(indent='  '),
#                    )
#
