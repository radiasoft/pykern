# -*- coding: utf-8 -*-
"""conforming case_dirs

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_case_dirs_bytes():
    from pykern import pkunit

    for d in pkunit.case_dirs(group_prefix="bytes", is_bytes=True):
        # Copy does all the work, just a sanity check here
        pkunit.pkok(d.join("dot.gif").check(exists=True), "dot.gif doesn't exist")


def test_case_dirs_conformance():
    from pykern import pkunit

    for d in pkunit.case_dirs(group_prefix="conformance"):
        i = d.join("in.txt").read()
        pkunit.pkeq(d.basename + "\n", i)
        d.join("out.txt").write(i)


def test_case_dirs_deviance():
    from pykern import pkunit
    import re

    with pkunit.pkexcept("See stack above"):
        for d in pkunit.case_dirs(group_prefix="deviance"):
            with pkunit.ExceptToFile():
                d.join("in.txt").read()
    pkunit.pkre("not.*found.*deviance-1/in.txt", d.join(pkunit.PKSTACK_PATH).read())


def test_case_dirs_curly_brackets():
    from pykern import pkunit

    with pkunit.pkexcept("1c1\n< expected\n---\n> {unexpected}"):
        for d in pkunit.case_dirs(group_prefix="curly_brackets"):
            pass


def test_no_files():
    from pykern import pkunit

    with pkunit.pkexcept("no files found"):
        for d in pkunit.case_dirs(group_prefix="no_files"):
            continue
