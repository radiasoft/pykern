# -*- coding: utf-8 -*-
"""PyTest for :mod:`pykern.util`

:copyright: Copyright (c) 2022 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_is_pure_text():
    from pykern import pkunit
    from pykern import util

    pkunit.pkeq(True, util.is_pure_text(b"", 512))
    pkunit.pkeq(True, util.is_pure_text(b"This is example text", 512))
    pkunit.pkeq(
        False,
        util.is_pure_text(
            b"\xeb\xbf\xe4\xa0\xe9\xcf\xa5\n\xe7\xbf\xde\x83\xd4\x16\xc0\xd6\xec\xbf\x92\xe6\x84T\xc9 \xe9\xbf",
            512,
        ),
    )
    pkunit.pkeq(
        True, util.is_pure_text(("a" * 511).encode("utf-8") + "¡".encode("utf-8"), 512)
    )
    pkunit.pkeq(
        True, util.is_pure_text(("a" * 511).encode("utf-8") + b"\xf0\x9f\x8c\xae", 512)
    )
    pkunit.pkeq(False, util.is_pure_text(("a" * 511).encode("utf-8") + b"\xc2", 512))
