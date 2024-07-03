# -*- coding: utf-8 -*-
"""PyTest for :mod:`pykern.pkinspect`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_append_exception_reason():
    from pykern import pkinspect
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq

    # Run through the cases because there are so many
    r = "xyzzy"
    for e, a in (
        (PKDict(), PKDict()),
        (PKDict(reason=1), PKDict(reason=1)),
        (PKDict(reason="xyzzy"), PKDict(reason="")),
        (PKDict(args=("xyzzy",)), PKDict(args=None)),
        (PKDict(args=("xyzzy",)), PKDict(args=())),
        (PKDict(args=(1,)), PKDict(args=(1,))),
        (PKDict(args=("hello; xyzzy",)), PKDict(args=("hello",))),
    ):
        pkinspect.append_exception_reason(a, r)
        pkeq(e, a)


def test_module_basename():
    from pykern import pkinspect
    from pykern import pkunit

    p1 = pkunit.import_module_from_data_dir("p1")
    assert pkinspect.module_basename(p1) == "p1"
    m1 = pkunit.import_module_from_data_dir("p1.m1")
    assert pkinspect.module_basename(m1) == "m1"
    assert pkinspect.module_basename(m1.C) == "m1"
    assert pkinspect.module_basename(m1.C()) == "m1"
    assert pkinspect.module_basename(m1) == "m1"
    assert pkinspect.module_basename(m1.C) == "m1"
    assert pkinspect.module_basename(m1.C()) == "m1"
    p2 = pkunit.import_module_from_data_dir("p1.p2")
    assert pkinspect.module_basename(p2) == "p2"
    m2 = pkunit.import_module_from_data_dir("p1.p2.m2")
    assert pkinspect.module_basename(m2) == "m2"


def test_caller():
    from pykern import pkinspect
    from pykern import pkunit
    import inspect
    import sys

    def _func_name(expect):
        pkunit.pkeq(expect, pkinspect.caller_func_name())

    m1 = pkunit.import_module_from_data_dir("p1.m1")
    c = m1.caller()
    expect = inspect.currentframe().f_lineno - 1
    pkunit.pkeq(expect, c.lineno)
    expect = "test_caller"
    pkunit.pkeq(expect, c.name)
    _func_name(expect)
    this_module = sys.modules[__name__]
    c = m1.caller(ignore_modules=[this_module])
    pkunit.pkne(expect, c.name)
    my_caller = pkinspect.caller()
    expect = my_caller._module
    pkunit.pkeq(expect, c._module)
    pkunit.pkeq(expect, c._module)


def test_caller_module():
    from pykern import pkunit

    m1 = pkunit.import_module_from_data_dir("p1.m1")
    assert (
        __name__ == m1.caller_module().__name__
    ), "caller_module should return this module"
    n = m1.caller_module(exclude_first=False).__name__
    expect = m1.__name__
    assert expect == n, "{}: should be {}".format(n, expect)


def test_is_caller_main():
    import sys
    import subprocess
    from pykern import pkio
    from pykern import pkunit

    m1 = pkunit.import_module_from_data_dir("p1.m1")
    assert not m1.is_caller_main(), "When not called from main, is_caller_main is False"
    with pkio.save_chdir(pkunit.data_dir()):
        subprocess.check_call(
            [sys.executable, "-c", "from p1 import m1; assert m1.is_caller_main()"]
        )


def test_is_valid_identifier():
    from pykern import pkinspect

    assert pkinspect.is_valid_identifier("_"), "a single underscore is valid"
    assert pkinspect.is_valid_identifier("A_3"), "any letters and numbers is valid"
    assert not pkinspect.is_valid_identifier("1abc"), "a leading number is invalid"
    assert not pkinspect.is_valid_identifier(""), "empty string is invalid"


def test_submodule_name():
    from pykern import pkinspect
    from pykern import pkunit

    m2 = pkunit.import_module_from_data_dir("p1.p2.m2")
    assert pkinspect.submodule_name(m2) == "p2.m2"


def test_root_pkg():
    from pykern import pkinspect
    from pykern import pkunit

    m2 = pkunit.import_module_from_data_dir("p1.p2.m2")
    assert pkinspect.root_package(m2) == "p1"
