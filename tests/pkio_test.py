"""PyTest for :mod:`pykern.pkio`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import glob
import os
import py
import pytest


def test_atomic_write():
    from pykern import pkunit
    from pykern import pkio

    with pkunit.save_chdir_work():
        pkio.atomic_write("x.ABC", "abc")
        pkunit.pkeq("abc", pkio.read_text("x.ABC"))


def test_compare_files():
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkunit import pkok

    with pkunit.save_chdir_work():
        text = "abc"
        b = pkio.py_path("base")
        b.write(text)
        c = pkio.py_path("copy")
        b.copy(c)
        c.setmtime(b.mtime())
        c = pkio.py_path("same-content")
        c.write(text)
        c.setmtime(b.mtime() + 10)
        c = pkio.py_path("same-stat")
        c.write(len(text) * "X")
        c.setmtime(b.mtime())
        c = pkio.py_path("diff-size")
        c.write(text + text)
        c.setmtime(b.mtime())
        pkok(pkio.compare_files("base", "copy"), "copy")
        pkok(pkio.compare_files("base", "same-content"), "same-content")
        pkok(pkio.compare_files("base", "same-stat"), "same-stat")
        pkok(not pkio.compare_files("base", "same-stat", force=True), "same-stat force")
        pkok(not pkio.compare_files("base", "diff-size"), "diff-size")
        pkok(not pkio.compare_files("base", "not-found"), "not-found")
        pkok(not pkio.compare_files("both-not-found", "not-found"), "both-not-found")


def test_has_file_extension():
    from pykern.pkunit import pkeq
    from pykern import pkio

    pkeq(True, pkio.has_file_extension("x.ABC", "abc"))
    pkeq(True, pkio.has_file_extension(py.path.local("x.abc"), ("abc", "def")))
    pkeq(False, pkio.has_file_extension("filename_with_no_extension", "json"))


def test_is_pure_text():
    from pykern import pkunit
    from pykern import pkio

    d = pkunit.data_dir()
    pkunit.pkeq(False, pkio.is_pure_text(d.join("binary.dat")))
    pkunit.pkeq(True, pkio.is_pure_text(d.join("text.dat")))


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
    expect_new = py.path.local("..").realpath()
    try:
        with pkio.save_chdir(expect_new) as new:
            assert (
                expect_new == new
            ), "save_chdir returns current directory before chdir"
            assert (
                expect_new == py.path.local().realpath()
            ), "When in save_chdir, expect current directory to be new directory"
            os.chdir("..")
            assert (
                expect_new != py.path.local().realpath()
            ), "When in save_chdir, expect chdir to still work"
            raise IndentationError()
    except IndentationError as benign_exception:
        pass
    assert (
        expect_prev == py.path.local().realpath()
    ), "When exception is raised, current directory should be reverted."
    expect_new = pkunit.empty_work_dir().join("new_folder").realpath()
    with pytest.raises(OSError):
        with pkio.save_chdir(expect_new) as new:
            assert (
                False
            ), "When save_chdir given non-existent dir, should throw exception"
    with pkio.save_chdir(expect_new, mkdir=True) as new:
        assert (
            expect_new == py.path.local().realpath()
        ), "When save_chdir given non-existent dir and mkdir=True, should pass"


def test_unchecked_remove():
    """Also tests mkdir_parent"""
    from pykern import pkunit
    from pykern import pkio

    with pkunit.save_chdir_work():
        fn = "f1"
        # Should not throw an exception
        pkio.unchecked_remove(fn)
        pkio.write_text(fn, "hello")
        pkio.unchecked_remove(fn)
        assert not os.path.exists(fn), "When file removed, should be gone"
        for f in ("d1", "d2/d3"):
            assert py.path.local(f) == pkio.mkdir_parent(
                f
            ), "When mkdir_parent is called, returns path passed in"
        assert os.path.exists("d1"), "When single directory, should exist"
        assert os.path.exists("d2/d3"), "When nested directory, should exist"
        with pytest.raises(AssertionError):
            pkio.unchecked_remove(".")
        with pytest.raises(AssertionError):
            pkio.unchecked_remove(os.getcwd())
        with pytest.raises(AssertionError):
            pkio.unchecked_remove("/")


def test_walk_tree_and_sorted_glob():
    """Looks in work_dir"""
    from pykern import pkunit
    from pykern import pkio
    import re

    with pkunit.save_chdir_work() as pwd:
        for f in ("d1/d7", "d2/d3", "d4/d5/d6"):
            pkio.mkdir_parent(f)
        expect = []
        for f in ["d1/d7/f1", "d4/d5/f2", "d2/d3/f3"]:
            pkio.write_text(f, "")
            expect.append(py.path.local(f))
        assert sorted(expect) == list(
            pkio.walk_tree(".")
        ), "When walking tree, should only return files"
        assert [expect[2]] == list(
            pkio.walk_tree(".", "f3")
        ), "When walking tree with file_re, should only return matching files"
        assert [expect[0]] == list(
            pkio.walk_tree(".", "^d1")
        ), "When walking tree with file_re, file to match does not include dir being searched"
        assert [expect[0]] == list(
            pkio.walk_tree(".", re.compile("^d1"))
        ), "When walking tree with file_re, file to match does not include dir being searched"
        assert pkio.sorted_glob("*/*/f*", key="basename") == expect


def test_write_binary():
    """Also tests read_binary"""
    from pykern import pkunit
    from pykern import pkio

    d = pkunit.empty_work_dir()
    expect_res = d.join("anything")
    expect_content = b"\xef broken utf8 \xbb\xbf"
    res = pkio.write_binary(expect_res, expect_content)
    pkunit.pkeq(expect_res, res)
    pkunit.pkeq(expect_content, pkio.read_binary(expect_res))


def test_write_text():
    """Also tests read_text"""
    from pykern import pkunit
    from pykern import pkio

    d = pkunit.empty_work_dir()
    expect_res = d.join("anything")
    expect_content = "something\u2167"
    write_content = bytes(expect_content, "utf-8")
    res = pkio.write_text(str(expect_res), write_content)
    assert expect_res == res, "Verify result is file path as py.path.Local"
    with open(str(expect_res), "rb") as f:
        assert (
            write_content == f.read()
        ), 'When write_text is called, it should write "something"'
    assert expect_content == pkio.read_text(
        str(expect_res)
    ), 'When read_text, it should read "something"'
    pkio.write_binary(expect_res, b"\xFF\xFF\0")
    with pkunit.pkexcept(str(expect_res)):
        pkio.read_text(expect_res)
    with pkunit.pkexcept(str(expect_res)):
        pkio.write_text(expect_res, b"\xFF\xFF\0")
