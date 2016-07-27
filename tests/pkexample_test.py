# -*- coding: utf-8 -*-
u"""Demonstrates RadiaSoft style testing.

Some Rules:
    We use  `pytest <http://pytest.org>`_ for unit testing.

    1. Terminology: a "test" is the file. Functions that
       begin with ``test_`` are cases.
    #. Test cases should be simple and test only one behavior
    #. Assertions messages should be informative, including
       values that are not in the assertion comparison itself.
    #. Use pytest fixtures for setup/teardown. See
       `yield fixtures <http://doc.pytest.org/en/latest/yieldfixture.html>`_
       for a way to setup/teardown each test.
    #. Use :func:`pykern.pkunit.save_chdir_work` to get automatic
       cleanup of files at start of test. The work dir stays
       around after the test runs, which helps debugging.
    #. Avoid global imports, even of the module under test.
       The pytest "collector" imports all tests files into a
       single process so you want this to go fast and not
       to initialize modules during collection.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_ema_compute():
    from pykern import pkexample
    ema = pkexample.EMA(4)
    ema.compute(20.)
    assert 16. == ema.compute(10.), \
        'Adding a value to the series changes the average'


def test_ema_init():
    from pykern import pkexample
    assert 5.0 == pkexample.EMA(1).compute(5.), \
        'First values sets initial average'


def test_ema_init_deviance():
    from pykern import pkexample
    with pytest.raises(AssertionError) as e:
        pkexample.EMA(0)
    assert 'must be greater' in str(e.value)
