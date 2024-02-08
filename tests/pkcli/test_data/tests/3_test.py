# -*- coding: utf-8 -*-
"""test pytest skip

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


#@pytest.mark.skip(reason="always skips")
def test_skip():
    from pykern import pkunit

    pkunit.pkfail("test_skip not skipped")


def test_skip_output(capsys):
    from pykern import pkcompat
    from pykern import pkunit
    import re
    
    o, e = capsys.readouterr()
    if not re.search("asdf", pkcompat.from_bytes(o), flags=re.IGNORECASE + re.DOTALL):
        pkunit.pkfail("o={}", o)
