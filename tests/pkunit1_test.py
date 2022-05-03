# -*- coding: utf-8 -*-
u"""conforming case_dirs

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest

def test_case_dirs():
    from pykern import pkunit

    for d in pkunit.case_dirs():
        if d.basename == 'xlsx':
            return
        i = d.join('in.txt').read()
        pkunit.pkeq(d.basename + '\n', i)
        d.join('out.txt').write(i)

def test_xlsx_to_csv_conversion():
    from pykern import pkunit
    for d in pkunit.case_dirs():
        if d.basename == 'xlsx':
            dir = d
    actual = dir.join('example.csv').read()
    expect = pkunit.data_dir().join('xlsx.out/example.csv').read()
    pkunit.pkeq(expect, actual)
