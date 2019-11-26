# -*- coding: utf-8 -*-
u"""pkcli.test test

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_simple(capsys):
    from pykern import pkunit
    import pykern.pkcli.test

    with pkunit.save_chdir_work() as d:
        t = d.join('tests')
        pkunit.data_dir().join('tests').copy(t)
        with pkunit.pkexcept('FAILED=1 passed=1'):
            pykern.pkcli.test.default_command()
        o, e = capsys.readouterr()
        pkunit.pkre('1_test.py pass', o)
        pkunit.pkre('2_test.py FAIL', o)
        t.join('2_test.py').rename(t.join('2_test.py-'))
        pkunit.pkre('passed=1', pykern.pkcli.test.default_command())
        o, e = capsys.readouterr()
        pkunit.pkre('1_test.py pass', o)
        pkunit.pkre('passed=1', pykern.pkcli.test.default_command('tests/1_test.py'))
        o, e = capsys.readouterr()
        pkunit.pkre('1_test.py pass', o)
        t.join('2_test.py-').rename(t.join('2_test.py'))
        t.join('1_test.py').rename(t.join('1_test.py-'))
        with pkunit.pkexcept('FAILED=1 passed=0'):
            pykern.pkcli.test.default_command()
        o, e = capsys.readouterr()
        pkunit.pkre('2_test.py FAIL', o)
        pkunit.pkre('x = 1 / 0', o)
