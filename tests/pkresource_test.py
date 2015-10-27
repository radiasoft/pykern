# -*- coding: utf-8 -*-
u"""pytest for `pykern.resource`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import importlib
import os.path

import pytest

from pykern import pkunit
from pykern import pkresource


def test_filename():
    d = pkunit.data_dir()
    t1 = importlib.import_module(d.basename + '.t1')
    assert t1.somefile().startswith('anything'), \
        'When somefile is called, it should return the "anything" file'
    n = pkresource.filename('test.yml', pkresource)
    sn = [n]
    def _tail():
        (sn[0], tail) = os.path.split(sn[0])
        return tail
    assert 'test.yml' == _tail(), \
        'nth of resource name is name passed to pkresource'
    assert 'package_data' == _tail(), \
        'n-1th resource is always "package_data"'
    assert 'pykern' == _tail(), \
        'n-2th resource is root package of passed in context'
    with pytest.raises(IOError):
        # Should not find somefile, because that's in a different context
        pkresource.filename('somefile', pkresource)
    assert pkresource.filename('somefile', t1.somefile), \
        'Given any object, should fine resource in root package of that object'
