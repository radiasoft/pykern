# -*- coding: utf-8 -*-
"""PyTest for :mod:`pykern.util`

:copyright: Copyright (c) 2022 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_is_pure_text():
    from pykern import pkunit
    from pykern import util

    a = "a".encode("utf-8")
    for case in [
        not util.is_pure_text(b"\0"),
        not util.is_pure_text(a + b"\xc2", 2),
        not util.is_pure_text(b"\xd4\x16\xc0\xd6\xec\xbf\x92\xe6\x84T\xc9 \xe9\xbf"),
        util.is_pure_text(b"This is example text"),
        util.is_pure_text(a + "¡".encode("utf-8"), 2),
        util.is_pure_text(a + b"\xf0\x9f\x8c\xae", 2),
    ]:
        pkunit.pkok(case, "is_pure_text test case failed")