"""test pytest skip

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


@pytest.mark.skip(reason="always skips")
def test_skip():
    from pykern import pkunit

    pkunit.pkfail("test_skip not skipped")


def test_pass():
    pass
