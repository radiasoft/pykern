# -*- coding: utf-8 -*-
u"""PyTest for :mod:`pykern.pkinspect`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import subprocess
import sys

import pytest
import py

from pykern import pkinspect
from pykern import pkio
from pykern import pkunit


def test_module_basename():
    p1 = pkunit.import_module_from_data_dir('p1')
    assert pkinspect.module_basename(p1) == 'p1'
    m1 = pkunit.import_module_from_data_dir('p1.m1')
    assert pkinspect.module_basename(m1) == 'm1'
    assert pkinspect.module_basename(m1.C) == 'm1'
    assert pkinspect.module_basename(m1.C()) == 'm1'
    assert pkinspect.module_basename(m1) == 'm1'
    assert pkinspect.module_basename(m1.C) == 'm1'
    assert pkinspect.module_basename(m1.C()) == 'm1'
    p2 = pkunit.import_module_from_data_dir('p1.p2')
    assert pkinspect.module_basename(p2) == 'p2'
    m2 = pkunit.import_module_from_data_dir('p1.p2.m2')
    assert pkinspect.module_basename(m2) == 'm2'


def test_caller():
    import inspect
    m1 = pkunit.import_module_from_data_dir('p1.m1')
    c = m1.caller()
    expect = inspect.currentframe().f_lineno - 1
    assert expect == c.lineno, \
        '{}: unexpected lineno, should be {}'.format(c.lineno, expect)
    expect = 'test_caller'
    assert expect == c.name, \
        '{}: expected function name {}'.format(c.name, expect)
    this_module = sys.modules[__name__]
    c = m1.caller(ignore_modules=[this_module])
    assert expect != c.name, \
        '{}: should not be {}'.format(c.name, expect)
    my_caller = pkinspect.caller()
    expect = my_caller._module
    assert expect == c._module, \
        '{}: should be {}'.format(c._module, expect)


def test_caller_module():
    m1 = pkunit.import_module_from_data_dir('p1.m1')
    assert __name__ == m1.caller_module().__name__, \
        'caller_module should return this module'


def test_is_caller_main():
    m1 = pkunit.import_module_from_data_dir('p1.m1')
    assert not m1.is_caller_main(), \
        'When not called from main, is_caller_main is False'
    with pkio.save_chdir(pkunit.data_dir()):
        subprocess.check_call([
            sys.executable,
            '-c',
            'from p1 import m1; assert m1.is_caller_main()'])


def test_is_valid_identifier():
    assert pkinspect.is_valid_identifier('_'), \
        'a single underscore is valid'
    assert pkinspect.is_valid_identifier('A_3'), \
        'any letters and numbers is valid'
    assert not pkinspect.is_valid_identifier('1abc'), \
        'a leading number is invalid'
    assert not pkinspect.is_valid_identifier(''), \
        'empty string is invalid'


def test_submodule_name():
    m2 = pkunit.import_module_from_data_dir('p1.p2.m2')
    assert pkinspect.submodule_name(m2) == 'p2.m2'


def test_root_pkg():
    m2 = pkunit.import_module_from_data_dir('p1.p2.m2')
    assert pkinspect.root_package(m2) == 'p1'
