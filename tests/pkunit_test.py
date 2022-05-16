# -*- coding: utf-8 -*-
u"""PyTest for :mod:`pykern.pkunit`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pkgutil

import py
from pykern.pkunit import data_dir
import pytest

def test_assert_object_with_json():
    from pykern import pkunit

    pkunit.empty_work_dir()
    pkunit.assert_object_with_json('assert1', {'a': 1})
    with pytest.raises(AssertionError):
        pkunit.assert_object_with_json('assert1', {'b': 1})


def test_data_dir():
    import py.path
    from pykern import pkunit

    expect = _expect('pkunit_data')
    d = pkunit.data_dir()
    assert isinstance(d, type(py.path.local())), \
        'Verify type of data_dir is same as returned by py.path.local'
    assert d == expect, \
        'Verify data_dir has correct return value'


def test_data_yaml():
    from pykern import pkunit

    y = pkunit.data_yaml('t1')
    assert 'v1' == y['k1'], \
        'YAML is read from file in data_dir'


def test_empty_work_dir():
    from pykern import pkunit
    import py.path
    import os

    expect = _expect('pkunit_work')
    if os.path.exists(str(expect)):
        expect.remove(rec=1)
    assert not os.path.exists(str(expect)), \
        'Ensure directory was removed'
    d = pkunit.empty_work_dir()
    assert isinstance(d, type(py.path.local())), \
        'Verify type of empty_work_dir is same as returned by py.path.local'
    assert expect == d, \
        'Verify empty_work_dir has correct return value'
    assert os.path.exists(str(d)), \
        'Ensure directory was created'


def test_file_eq():
    import array
    import pykern.pkunit
    import pykern.pkio

    a = array.ArrayType('d', [1])
    pykern.pkunit.file_eq('file_eq1.json', actual=a)

    with pykern.pkunit.pkexcept(TypeError):
        pykern.pkunit.file_eq('file_eq2.txt', actual=dict())
    d = pykern.pkunit.empty_work_dir()
    pykern.pkio.write_text(d.join('file_eq3.txt'), 'something')
    with pykern.pkunit.pkexcept('both exist'):
        pykern.pkunit.file_eq('file_eq3.txt', actual='something else')


def test_import_module_from_data_dir(monkeypatch):
    from pykern import pkunit

    real_data_dir = pkunit.data_dir()
    fake_data_dir = None
    def mock_data_dir():
        return fake_data_dir
    monkeypatch.setattr(pkunit, 'data_dir', mock_data_dir)
    fake_data_dir = str(real_data_dir.join('import1'))
    assert 'imp1' == pkunit.import_module_from_data_dir('p1').v, \
        'import1/p1 should be from "imp1"'
    fake_data_dir = str(real_data_dir.join('import2'))
    assert 'imp2' == pkunit.import_module_from_data_dir('p1').v, \
        'import2/p1 should be from "imp2"'


def test_pkexcept():
    import re, inspect
    from pykern.pkunit import pkexcept, pkfail

    with pkexcept(KeyError, 'should see a KeyError'):
        {}['not found']
    with pkexcept('KeyError.*xyzzy'):
        {}['xyzzy']
    try:
        lineno = inspect.currentframe().f_lineno + 2
        with pkexcept(KeyError, 'xyzzy'):
            pass
    except AssertionError as e:
        assert 'xyzzy' in str(e.args)
        assert 'pkunit_test.py:{}:test_pkexcept'.format(lineno) in str(e.args)
    except Exception as e:
        pkfail('{}: got exception, but not AssertionError', e)
    else:
        pkfail('did not raise AssertionError')
    try:
        with pkexcept(KeyError):
            raise NameError('whatever')
    except AssertionError as e:
        assert re.search(r'exception was raised.*but expected.*KeyError', str(e.args))
    except Exception as e:
        pkfail('{}: got exception, but not AssertionError', e)
    else:
        pkfail('did not raise AssertionError')
    try:
        lineno = inspect.currentframe().f_lineno + 2
        with pkexcept('any pattern'):
            pass
    except AssertionError as e:
        assert 'pkunit_test.py:{}:test_pkexcept'.format(lineno) in str(e.args)
        assert 'was not raised' in str(e.args)
    except Exception as e:
        pkfail('{}: got exception, but not AssertionError', e)
    else:
        pkfail('did not raise AssertionError')



def test_pkok():
    from pykern.pkunit import pkok
    import inspect

    assert 1 == pkok(1, 'should not see this'), \
        'Result of a successful ok is the condition value'
    lineno = inspect.currentframe().f_lineno + 2
    try:
        pkok(0, 'xyzzy {} {k1}', '333', k1='abc')
    except AssertionError as e:
        # May not match exactly, because depends on start directory
        assert 'pkunit_test.py:{}:test_pkok xyzzy 333 abc'.format(lineno) in str(e.args)


def test_pkre_convert():
    from pykern.pkunit import pkre
    r = r'A'
    for s in ('A', b'A', r'A', u'A'):
        pkre(r, s)

def test_xlsx_to_csv_conversion():
    from pykern import pkio
    from pykern.pkunit import file_eq, data_dir

    pkio.write_binary(data_dir().join('example.xlsx'), pkio.read_binary(data_dir().join('actual_excel.xlsx')))
    file_eq(expect_path='example.csv', actual_path=data_dir().join('example.xlsx'))

def _expect(base):
    import py.path

    d = py.path.local(__file__).dirname
    return py.path.local(d).join(base).realpath()
