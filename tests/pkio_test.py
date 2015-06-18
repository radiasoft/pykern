# -*- coding: utf-8 -*-
u"""PyTest for :mod:`pykern.pkio`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import os
import pytest

import py

from pykern import pkio
from pykern import pkunit


def test_save_chdir():
    expect_prev = py.path.local(os.getcwd()).realpath()
    expect_new = py.path.local('..').realpath()
    try:
        with pkio.save_chdir(str(expect_new)) as prev:
            assert expect_prev == prev, \
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


def test_unchecked_remove():
    """Also tests mkdir_parent"""
    with pkunit.save_chdir_work():
        fn = 'f1'
        # Should not throw an exception
        pkio.unchecked_remove(fn)
        pkio.write_text(fn, 'hello')
        pkio.unchecked_remove(fn)
        assert not os.path.exists(fn), \
            'When file removed, should be gone'
        pkio.mkdir_parent('d1', 'd2/d3')
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


def test_walk_tree():
    """Creates looks in data_dir"""
    with pkunit.save_chdir_work():
        pkio.mkdir_parent('d1/d7', 'd2/d3', 'd4/d5/d6')
        expect = []
        for f in ['d1/d7/f1', 'd4/d5/f2', 'd2/d3/f3']:
            pkio.write_text(f, '')
            expect.append(py.path.local(f))
        assert sorted(expect) == list(pkio.walk_tree('.')), \
            'When walking tree, should only return files'
        assert [expect[2]] == list(pkio.walk_tree('.', 'f3')), \
            'When walking tree with file_re, should only return matching files'


def test_write_text():
    """Also tests read_text"""
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
