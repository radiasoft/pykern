# -*- coding: utf-8 -*-
"""test for :mod:`pykern.pkcompat`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import locale
import os


def setup_module():
    """Set locale so can test expected outputs.

    TODO(robnagler) should test multiple locales.
    """
    # Setting locale as a tuple doesn't work. Not clear this is cross-platform
    os.environ["LANG"] = "en_US.UTF-8"
    locale.setlocale(locale.LC_ALL)


def test_from_bytes():
    from pykern import pkcompat
    from pykern.pkunit import pkeq

    b = pkcompat.to_bytes("你好")
    s = pkcompat.from_bytes(b)
    pkeq(s, "你好")
    pkeq(b, b"\xe4\xbd\xa0\xe5\xa5\xbd")
    pkeq(False, b == s)


def test_locale_str_1():
    """Verify proper conversions"""
    from pykern import pkcompat

    s = pkcompat.locale_str(b"\xc2\xb0")
    assert isinstance(s, str), "When locale_str is converted, it should return str"
    assert "°" == s, "Conversion should be same as literal unicode value"
    before = str(123)
    assert before == pkcompat.locale_str(
        before
    ), "When string is already unicode, conversion yields same string"
    before = str(None)
    assert before == pkcompat.locale_str(
        before
    ), "When string is already unicode, conversion yields same string"


def test_locale_str_2():
    """Invalid utf8"""
    from pykern import pkcompat, pkunit

    with pkunit.pkexcept(UnicodeDecodeError):
        # TODO(robngler) set the locale?
        pkcompat.locale_str(b"\x80")


def test_unicode_unescape():
    from pykern import pkcompat

    assert "\n" == pkcompat.unicode_unescape(r"\n")


def test_zip_strict():
    from pykern import pkcompat, pkunit

    for e, c in (
        ((), ()),
        ((), (range(0), range(0))),
        (((0,),), (range(1),)),
        (((0, 0),), (range(1), range(1))),
        (((0, 0, 0),), (range(1), range(1), range(1))),
    ):
        pkunit.pkeq(e, tuple(pkcompat.zip_strict(*c)))

    for c in (
        (range(0), range(1)),
        (range(0), range(0), range(1)),
        (range(1), range(0)),
        (range(1), range(2)),
        (range(2), range(3)),
    ):
        with pkunit.pkexcept(ValueError):
            list(pkcompat.zip_strict(*c))
