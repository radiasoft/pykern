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


def test_write_text():
    d = pkunit.empty_work_dir()
    expect_res = d.join('anything')
    expect_content = 'something'
    res = pkio.write_text(str(expect_res), expect_content)
    assert expect_res == res, \
        'Verify result is file path as py.path.Local'
    with open(str(expect_res)) as f:
        assert expect_content == f.read(), \
            'When write_file is called, it should write "something"'
