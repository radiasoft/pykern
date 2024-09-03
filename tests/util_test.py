"""PyTest for :mod:`pykern.util`

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_dev_run_dir():
    from pykern import util, pkunit

    pkunit.pkeq(pkunit.work_dir(), util.dev_run_dir(util))
    util._dev_run_dir = None
    p = pkunit.is_test_run
    try:
        pkunit.is_test_run = lambda: False
        pkunit.pkeq(
            pkunit.work_dir().dirpath().dirpath().join("run"),
            util.dev_run_dir(util),
        )
    finally:
        pkunit.is_test_run = p


def test_is_pure_text():
    from pykern import util
    from pykern import pkunit

    def _false(value, is_truncated=False):
        pkunit.pkeq(False, util.is_pure_text(value, is_truncated=is_truncated))

    def _true(value, is_truncated=False):
        pkunit.pkeq(True, util.is_pure_text(value, is_truncated=is_truncated))

    a = "a".encode("utf-8")
    _false(b"\0 one null causes failure in valid text")
    _false(a + b"\xc2")
    _false(bytes(range(1, 0x20)))
    _false(b"\xd4\x16\xc0\xd6\xec\xbf\x92\xe6\x84T\xc9 \xe9\xbf")
    # backwards probing on non-text case
    _false(a + b"\xc2\xc2\xc2\xc2", is_truncated=True)
    # boundary of control code ratio
    _false(b"\x01" * 33 + b"\x07" * 67)
    _true(b"\x01" * 32 + b"\x07" * 68)
    _true(b"")
    _true(b"This is example text")
    _true(b"\x07\x08\t\n\x0b\x0c\r\x0e\x0f")
    # backwards probing on text case
    _true(a + "¡".encode("utf-8"), is_truncated=True)
    _true(a + b"\xf0\x9f\x8c\xae", is_truncated=True)
