# -*- coding: utf-8 -*-
u"""PyTest for :mod:`pykern.pkunit`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import os

import py
import pytest

from pykern.pkdebug import pkdc, pkdp
from pykern import pkunit

PY_PATH_LOCAL_TYPE = type(py.path.local())


def test_assert_object_with_json():
    pkunit.empty_work_dir()
    pkunit.assert_object_with_json('assert1', {'a': 1})
    with pytest.raises(AssertionError):
        pkunit.assert_object_with_json('assert1', {'b': 1})


def test_data_dir():
    expect = _expect('pkunit_data')
    d = pkunit.data_dir()
    assert isinstance(d, PY_PATH_LOCAL_TYPE), \
        'Verify type of data_dir is same as returned by py.path.local'
    assert d == expect, \
        'Verify data_dir has correct return value'


def test_data_yaml():
    y = pkunit.data_yaml('t1')
    assert 'v1' == y['k1'], \
        'YAML is read from file in data_dir'


def test_empty_work_dir():
    expect = _expect('pkunit_work')
    if os.path.exists(str(expect)):
        expect.remove(rec=1)
    assert not os.path.exists(str(expect)), \
        'Ensure directory was removed'
    d = pkunit.empty_work_dir()
    assert isinstance(d, PY_PATH_LOCAL_TYPE), \
        'Verify type of empty_work_dir is same as returned by py.path.local'
    assert expect == d, \
        'Verify empty_work_dir has correct return value'
    assert os.path.exists(str(d)), \
        'Ensure directory was created'


def test_import_module_from_data_dir(monkeypatch):
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
        assert 'xyzzy' in e.message
        assert 'pkunit_test.py:{}:test_pkexcept'.format(lineno) in e.message
    except Exception as e:
        pkfail('{}: got exception, but not AssertionError', e)
    else:
        pkfail('did not raise AssertionError')
    try:
        with pkexcept(KeyError):
            raise NameError('whatever')
    except AssertionError as e:
        assert re.search(r'exception was raised.*but expected.*KeyError', e.message)
    except Exception as e:
        pkfail('{}: got exception, but not AssertionError', e)
    else:
        pkfail('did not raise AssertionError')
    try:
        lineno = inspect.currentframe().f_lineno + 2
        with pkexcept('any pattern'):
            pass
    except AssertionError as e:
        assert 'pkunit_test.py:{}:test_pkexcept'.format(lineno) in e.message
        assert 'was not raised' in e.message
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
        assert 'pkunit_test.py:{}:test_pkok xyzzy 333 abc'.format(lineno) in e.message


def _expect(base):
    d = py.path.local(__file__).dirname
    return py.path.local(d).join(base).realpath()
