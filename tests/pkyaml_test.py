# -*- coding: utf-8 -*-
u"""PyTest for :mod:`pykern.pkyaml`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_dump_pretty():
    from pykern import pkyaml, pkunit, pkio
    from pykern.pkcollections import PKDict

    v = PKDict(x=PKDict(y=[PKDict(b=1), 2]))
    a = pkunit.work_dir().join('dump1.yml')
    pkyaml.dump_pretty(v, a)
    pkunit.file_eq(
        a.basename,
        actual_path=a,
    )


def test_load_file():
    """Test values are unicode"""
    from pykern import pkunit
    from pykern import pkyaml

    y = pkyaml.load_file(pkunit.data_dir().join('conf1.yml'))
    _assert_unicode(y)


def test_load_resource():
    """Test file can be read"""
    from pykern import pkunit
    from pykern import pkyaml

    p1 = pkunit.import_module_from_data_dir('p1')
    assert 'v2' == p1.y['f2'], \
        'Resource should be loaded relative to root package of caller'


def _assert_unicode(value):
    import six

    if six.PY3:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            # TODO(robnagler) breaks with PY3
            assert isinstance(k, unicode), \
                '{}: key is not unicode'.format(k)
            _assert_unicode(v)
    elif isinstance(value, list):
        for v in value:
            _assert_unicode(v)
    elif type(value) == str:
        assert isinstance(value, unicode), \
            '{}: value is not unicode'.format(value)
