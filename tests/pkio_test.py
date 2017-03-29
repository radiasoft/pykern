# -*- coding: utf-8 -*-
u"""PyTest for :mod:`pykern.pkio`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import glob
import os
import py
import pytest


def test_has_file_extension():
    from pykern.pkunit import pkeq
    from pykern import pkio

    pkeq(True, pkio.has_file_extension('x.ABC', 'abc'))
    pkeq(True, pkio.has_file_extension(py.path.local('x.abc'), ('abc', 'def')))


def test_py_path():
    from pykern import pkunit
    from pykern import pkio
    from pykern.pkunit import pkeq

    with pkunit.save_chdir_work():
        d = pkunit.data_dir()
        pkeq(d, pkio.py_path(d))



def test_save_chdir():
    from pykern import pkunit
    from pykern import pkio

    expect_prev = py.path.local().realpath()
    expect_new = py.path.local('..').realpath()
    try:
        with pkio.save_chdir(expect_new) as new:
            assert expect_new == new, \
                'save_chdir returns current directory before chdir'
            assert expect_new == py.path.local().realpath(), \
                'When in save_chdir, expect current directory to be new directory'
            os.chdir('..')
            assert expect_new != py.path.local().realpath(), \
                'When in save_chdir, expect chdir to still work'
            raise IndentationError()
    except IndentationError as benign_exception:
        pass
    assert expect_prev == py.path.local().realpath(), \
        'When exception is raised, current directory should be reverted.'
    expect_new = pkunit.empty_work_dir().join('new_folder').realpath()
    with pytest.raises(OSError):
        with pkio.save_chdir(expect_new) as new:
            assert False, \
                'When save_chdir given non-existent dir, should throw exception'
    with pkio.save_chdir(expect_new, mkdir=True) as new:
        assert expect_new == py.path.local().realpath(), \
            'When save_chdir given non-existent dir and mkdir=True, should pass'


def test_unchecked_remove():
    """Also tests mkdir_parent"""
    from pykern import pkunit
    from pykern import pkio

    with pkunit.save_chdir_work():
        fn = 'f1'
        # Should not throw an exception
        pkio.unchecked_remove(fn)
        pkio.write_text(fn, 'hello')
        pkio.unchecked_remove(fn)
        assert not os.path.exists(fn), \
            'When file removed, should be gone'
        for f in ('d1', 'd2/d3'):
            assert py.path.local(f) == pkio.mkdir_parent(f), \
                'When mkdir_parent is called, returns path passed in'
        assert os.path.exists('d1'), \
            'When single directory, should exist'
        assert os.path.exists('d2/d3'), \
            'When nested directory, should exist'
        with pytest.raises(AssertionError):
            pkio.unchecked_remove('.')
        with pytest.raises(AssertionError):
            pkio.unchecked_remove(os.getcwd())
        with pytest.raises(AssertionError):
            pkio.unchecked_remove('/')


def test_walk_tree_and_sorted_glob():
    """Looks in work_dir"""
    from pykern import pkunit
    from pykern import pkio

    with pkunit.save_chdir_work() as pwd:
        for f in ('d1/d7', 'd2/d3', 'd4/d5/d6'):
            pkio.mkdir_parent(f)
        expect = []
        for f in ['d1/d7/f1', 'd4/d5/f2', 'd2/d3/f3']:
            pkio.write_text(f, '')
            expect.append(py.path.local(f))
        assert sorted(expect) == list(pkio.walk_tree('.')), \
            'When walking tree, should only return files'
        assert [expect[2]] == list(pkio.walk_tree('.', 'f3')), \
            'When walking tree with file_re, should only return matching files'
        assert [expect[0]] == list(pkio.walk_tree('.', '^d1')), \
            'When walking tree with file_re, file to match does not include dir being searched'
        assert pkio.sorted_glob('*[42]') == [py.path.local(f) for f in ('d2', 'd4')]


def test_write_text():
    """Also tests read_text"""
    from pykern import pkunit
    from pykern import pkio

    d = pkunit.empty_work_dir()
    expect_res = d.join('anything')
    expect_content = 'something'
    res = pkio.write_text(str(expect_res), expect_content)
    assert expect_res == res, \
        'Verify result is file path as py.path.Local'
    with open(str(expect_res)) as f:
        assert expect_content == f.read(), \
            'When write_text is called, it should write "something"'
    assert expect_content == pkio.read_text(str(expect_res)), \
        'When read_text, it should read "something"'
