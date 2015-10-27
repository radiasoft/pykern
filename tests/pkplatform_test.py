# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkplatform`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import platform
import pytest
import re
import sys

from pykern import pkplatform


def test_conformance1():
    """Verify the platforms based on other calls"""
    if platform.system() == 'Linux':
        assert pkplatform.is_linux()
        assert pkplatform.is_unix()
        assert not pkplatform.is_darwin()
        assert not pkplatform.is_windows()
    elif platform.system().startswith('CYGWIN'):
        assert not pkplatform.is_linux()
        assert pkplatform.is_unix()
        assert not pkplatform.is_darwin()
        assert pkplatform.is_windows()
    elif platform.system() == 'Windows':
        assert not pkplatform.is_linux()
        assert not pkplatform.is_unix()
        assert not pkplatform.is_darwin()
        assert pkplatform.is_windows()
    elif platform.system() == 'Darwin':
        assert not pkplatform.is_linux()
        assert pkplatform.is_unix()
        assert pkplatform.is_darwin()
        assert not pkplatform.is_windows()
    else:
        assert not pkplatform.is_windows()
        assert not pkplatform.is_darwin()
        assert not pkplatform.is_linux()
        # Not sure if it would be unix
