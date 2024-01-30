# -*- coding: utf-8 -*-
"""PyTest for :mod:`pykern.util`

:copyright: Copyright (c) 2022 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
from pykern.pkcollections import PKDict


def test_is_pure_text():
    from pykern import util
    from pykern import pkunit

    a = "a".encode("utf-8")
    for case in [
        PKDict(
            value=b"\0"
            + "Valid text to see that zero byte causes failure".encode("utf-8"),
            is_truncated=False,
            expected_result=False,
        ),
        PKDict(value=a + b"\xc2", is_truncated=False, expected_result=False),
        PKDict(
            value=b"\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f",
            is_truncated=False,
            expected_result=False,
        ),
        PKDict(
            value=b"\xd4\x16\xc0\xd6\xec\xbf\x92\xe6\x84T\xc9 \xe9\xbf",
            is_truncated=False,
            expected_result=False,
        ),
        PKDict(value=b"", is_truncated=False, expected_result=True),
        PKDict(value=b"This is example text", is_truncated=False, expected_result=True),
        PKDict(
            value=b"\x07\x08\t\n\x0b\x0c\r\x0e\x0f",
            is_truncated=False,
            expected_result=True,
        ),
        PKDict(value=a + "¡".encode("utf-8"), is_truncated=True, expected_result=True),
        PKDict(value=a + b"\xf0\x9f\x8c\xae", is_truncated=True, expected_result=True),
    ]:
        pkunit.pkok(
            util.is_pure_text(case.value, is_truncated=case.is_truncated)
            == case.expected_result,
            f"is_pure_text failed on value={case.value}",
        )
