# -*- coding: utf-8 -*-
u"""pytest for :mod:`pykern.compat`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import locale
import os

import pytest
import six

import pykern.compat as pc


def setup_module():
    """Set locale so can test expected outputs.

    TODO(robnagler) should test multiple locales.
    """
    # Setting locale as a tuple doesn't work. Not clear this is cross-platform
    os.environ['LANG'] = 'en_US.UTF-8'
    locale.setlocale(locale.LC_ALL)


def test_conformance1():
    """Verify proper conversions"""
    s = pc.locale_str(b'\xc2\xb0')
    if six.PY2:
        assert type(s) == unicode, \
            'When locale_str is converted in PY2, it should return unicode'
    else:
        assert type(s) == str, \
            'When locale_str is converted in not PY2, it should return str'
    assert u'°' == s, \
        'Conversion should be same as literal unicode value'
    if six.PY2:
        before = unicode(b'\xc2\xb0', 'utf8')
        after = pc.locale_str(before)
        assert after == before, \
            'When string is already unicode, conversion yields same string'


def test_conformance2():
    """Verify locale_check_output works"""
    out = pc.locale_check_output(
        'echo ' + b'he\xc5\x82\xc5\x82o'.decode('utf8'),
        shell=True,
    )
    assert out == u'hełło\n'


def test_deviance1():
    """Invalid utf8"""
    with pytest.raises(UnicodeDecodeError):
        #TODO(robngler) set the locale?
        pc.locale_str(b'\x80')
