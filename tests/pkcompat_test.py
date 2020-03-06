# -*- coding: utf-8 -*-
u"""pytest for :mod:`pykern.pkcompat`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import locale
import os

import pytest
import six


def setup_module():
    """Set locale so can test expected outputs.

    TODO(robnagler) should test multiple locales.
    """
    # Setting locale as a tuple doesn't work. Not clear this is cross-platform
    os.environ['LANG'] = 'en_US.UTF-8'
    locale.setlocale(locale.LC_ALL)


def test_from_bytes():
    from pykern import pkcompat
    from pykern.pkunit import pkeq
    b = pkcompat.to_bytes('你好')
    s = pkcompat.from_bytes(b)
    pkeq(s, '你好')
    pkeq(b, b'\xe4\xbd\xa0\xe5\xa5\xbd')
    if six.PY2:
        pkeq(b, s)
    else:
        pkeq(False, b == s)


def test_locale_str_1():
    """Verify proper conversions"""
    from pykern import pkcompat

    s = pkcompat.locale_str(b'\xc2\xb0')
    if six.PY2:
        assert isinstance(s, unicode), \
            'When locale_str is converted in PY2, it should return unicode'
    else:
        assert isinstance(s, str), \
            'When locale_str is converted in not PY2, it should return str'
    assert u'°' == s, \
        'Conversion should be same as literal unicode value'
    if six.PY2:
        before = unicode(b'\xc2\xb0', 'utf8')
        assert before == pkcompat.locale_str(before), \
            'When string is already unicode, conversion yields same string'
        before = str(123)
        assert unicode(before) == pkcompat.locale_str(before), \
            'When string is already unicode, conversion yields same string'
        before = str(None)
        assert unicode(before) == pkcompat.locale_str(before), \
            'When string is already unicode, conversion yields same string'
    else:
        before = str(123)
        assert before == pkcompat.locale_str(before), \
            'When string is already unicode, conversion yields same string'
        before = str(None)
        assert before == pkcompat.locale_str(before), \
            'When string is already unicode, conversion yields same string'


def test_locale_str_2():
    """Invalid utf8"""
    from pykern import pkcompat

    with pytest.raises(UnicodeDecodeError):
        #TODO(robngler) set the locale?
        pkcompat.locale_str(b'\x80')


def test_unicode_unescape():
    from pykern import pkcompat

    assert '\n' == pkcompat.unicode_unescape(r'\n')
