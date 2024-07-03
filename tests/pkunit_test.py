# -*- coding: utf-8 -*-
"""PyTest for :mod:`pykern.pkunit`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
import shutil


def test_assert_object_with_json():
    from pykern import pkunit

    pkunit.empty_work_dir()
    pkunit.assert_object_with_json("assert1", {"a": 1})
    with pytest.raises(AssertionError):
        pkunit.assert_object_with_json("assert1", {"b": 1})


def test_pkfail_output():
    from pykern.pkunit import pkexcept, pkne, pkeq
    import re

    k = "example KeyError message"
    with pkexcept(
        re.compile(k + r".*?" + "expecting ValueError but will get KeyError", re.DOTALL)
    ):
        with pkexcept(ValueError, "expecting ValueError but will get {}", "KeyError"):
            raise KeyError(k)

    with pkexcept("expect=x != actual=y"):
        pkeq("x", "y")
    with pkexcept("expect=x != actual=y args: arg1 arg2 kwarg=z"):
        pkeq("x", "y", "args: {} {} kwarg={kwarg}", "arg1", "arg2", kwarg="z")
    with pkexcept("expect=x == actual=x args: arg1 arg2 kwarg=z"):
        pkne("x", "x", "args: {} {} kwarg={kwarg}", "arg1", "arg2", kwarg="z")


def test_data_dir():
    from pykern import pkio
    from pykern import pkunit

    expect = _expect("pkunit_data")
    d = pkunit.data_dir()
    assert isinstance(
        d, type(pkio.py_path())
    ), "Verify type of data_dir is same as returned by py.path.local"
    assert d == expect, "Verify data_dir has correct return value"


def test_data_yaml():
    from pykern import pkunit

    y = pkunit.data_yaml("t1")
    assert "v1" == y["k1"], "YAML is read from file in data_dir"


def test_empty_work_dir():
    from pykern import pkunit
    from pykern import pkio
    import os

    expect = _expect("pkunit_work")
    if os.path.exists(str(expect)):
        expect.remove(rec=1)
    assert not os.path.exists(str(expect)), "Ensure directory was removed"
    d = pkunit.empty_work_dir()
    assert isinstance(
        d, type(pkio.py_path())
    ), "Verify type of empty_work_dir is same as returned by py.path.local"
    assert expect == d, "Verify empty_work_dir has correct return value"
    assert os.path.exists(str(d)), "Ensure directory was created"


def test_file_eq():
    from pykern import pkio
    from pykern import pkunit
    import array

    a = array.ArrayType("d", [1])
    pkunit.file_eq("file_eq1.json", actual=a)
    with pkunit.pkexcept(TypeError):
        pkunit.file_eq("file_eq2.txt", actual=dict())
    d = pkunit.empty_work_dir()
    pkio.write_text(d.join("file_eq3.txt"), "something")
    with pkunit.pkexcept("both exist"):
        pkunit.file_eq("file_eq3.txt", actual="something else")


@pytest.mark.skipif(shutil.which("ndiff") is None, reason="ndiff not available")
def test_file_eq_ndiff():
    from pykern import pkunit

    d = pkunit.data_dir()

    pkunit.file_eq(
        expect_path=d.join("expect_default_conformance.ndiff"),
        actual_path=d.join("actual_default_conformance.ndiff"),
    )
    with pkunit.pkexcept("diffs detected:"):
        pkunit.file_eq(
            expect_path=d.join("expect_default_conformance_1.ndiff"),
            actual_path=d.join("actual_default_conformance_1.ndiff"),
        )
    pkunit.file_eq(
        expect_path=d.join("expect_abs_ok.ndiff"),
        actual_path=d.join("actual_abs_ok.ndiff"),
        ndiff_epsilon_is_abs=True,
        ndiff_epsilon=1e-20,
    )
    with pkunit.pkexcept("diffs detected:"):
        pkunit.file_eq(
            expect_path=d.join("expect_abs_ok.ndiff"),
            actual_path=d.join("actual_abs_ok.ndiff"),
            ndiff_epsilon=1e-20,
        )
    with pkunit.pkexcept("diffs detected:"):
        pkunit.file_eq(
            expect_path=d.join("expect_rel_ok.ndiff"),
            actual_path=d.join("actual_rel_ok.ndiff"),
            ndiff_epsilon_is_abs=True,
        )
    pkunit.file_eq(
        expect_path=d.join("expect_rel_ok.ndiff"),
        actual_path=d.join("actual_rel_ok.ndiff"),
    )
    pkunit.file_eq(
        expect_path=d.join("expect_rel_ok_2.ndiff"),
        actual_path=d.join("actual_rel_ok_2.ndiff"),
        ndiff_epsilon=1e-20,
        ndiff_epsilon_is_abs=False,
    )


def test_file_eq_is_bytes():
    from pykern import pkio
    from pykern import pkunit

    with pkio.save_chdir(pkunit.data_dir()) as d:
        pkunit.file_eq("in.bin", actual_path=d.join("out.bin"), is_bytes=True)
        with pkunit.pkexcept("differ: byte 88"):
            pkunit.file_eq("in.bin", actual_path=d.join("different.bin"), is_bytes=True)
        with pkunit.pkexcept(UnicodeDecodeError):
            pkunit.file_eq("in.bin", actual_path=d.join("out.bin"))


def test_import_module_from_data_dir(monkeypatch):
    from pykern import pkunit

    real_data_dir = pkunit.data_dir()
    fake_data_dir = None

    def mock_data_dir():
        return fake_data_dir

    monkeypatch.setattr(pkunit, "data_dir", mock_data_dir)
    fake_data_dir = str(real_data_dir.join("import1"))
    assert (
        "imp1" == pkunit.import_module_from_data_dir("p1").v
    ), 'import1/p1 should be from "imp1"'
    fake_data_dir = str(real_data_dir.join("import2"))
    assert (
        "imp2" == pkunit.import_module_from_data_dir("p1").v
    ), 'import2/p1 should be from "imp2"'


def test_is_test_run():
    from pykern import pkunit

    pkunit.pkeq(True, pkunit.is_test_run())


def test_pkexcept():
    import re, inspect
    from pykern.pkunit import pkexcept, pkfail

    def _exc_args(pattern, exc):
        if not re.search(pattern, str(exc.args)):
            pkfail("'{}' not found in e.args={}", pattern, exc)

    with pkexcept(KeyError, "should see a KeyError"):
        {}["not found"]
    with pkexcept("KeyError.*xyzzy"):
        {}["xyzzy"]
    try:
        l = inspect.currentframe().f_lineno + 2
        with pkexcept(KeyError, "xyzzy"):
            pass
    except AssertionError as e:
        _exc_args("xyzzy", e)
        _exc_args(f"pkunit_test.py:(?:{l}|{l-1}):test_pkexcept", e)
    except Exception as e:
        pkfail("{}: got exception, but not AssertionError", e)
    else:
        pkfail("did not raise AssertionError")
    try:
        with pkexcept(KeyError):
            raise NameError("whatever")
    except AssertionError as e:
        _exc_args(r"exception was raised.*but expected.*KeyError", e)
    except Exception as e:
        pkfail("{}: got exception, but not AssertionError", e)
    else:
        pkfail("did not raise AssertionError")
    try:
        l = inspect.currentframe().f_lineno + 2
        with pkexcept("any pattern"):
            pass
    except AssertionError as e:
        _exc_args(f"pkunit_test.py:(?:{l}|{l-1}):test_pkexcept", e)
        _exc_args("was not raised", e)
    except Exception as e:
        pkfail("{}: got exception, but not AssertionError", e)
    else:
        pkfail("did not raise AssertionError")


def test_pkok():
    from pykern.pkunit import pkok
    import inspect

    assert 1 == pkok(
        1, "should not see this"
    ), "Result of a successful ok is the condition value"
    lineno = inspect.currentframe().f_lineno + 2
    try:
        pkok(0, "xyzzy {} {k1}", "333", k1="abc")
    except AssertionError as e:
        # May not match exactly, because depends on start directory
        assert "pkunit_test.py:{}:test_pkok xyzzy 333 abc".format(lineno) in str(e.args)


def test_pkre_convert():
    from pykern.pkunit import pkre

    r = r"A"
    for s in ("A", b"A", r"A", "A"):
        pkre(r, s)


def test_xlsx_to_csv_conversion():
    from pykern.pkunit import file_eq, data_dir, empty_work_dir

    file_eq(
        expect_path="example.csv",
        actual_path=data_dir()
        .join("example.xlsx")
        .copy(empty_work_dir().join("example.xlsx")),
    )


def test_ignore_lines():
    from pykern import pkunit

    d = pkunit.data_dir()
    pkunit.file_eq(
        expect_path=d.join("ignore_lines.in"),
        actual_path=d.join("ignore_lines.out"),
        ignore_lines=[r"[0-9]\+xyz"],
    )
    with pkunit.pkexcept("diff command failed"):
        pkunit.file_eq(
            expect_path=d.join("ignore_lines.in"),
            actual_path=d.join("ignore_lines.out"),
            ignore_lines=[r"[invalid regex"],
        )


def _expect(base):
    from pykern import pkio

    d = pkio.py_path(__file__).dirname
    return pkio.py_path(d).join(base).realpath()
