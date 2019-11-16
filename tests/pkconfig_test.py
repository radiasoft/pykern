# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkconfig`

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import dateutil.parser
import py.path
import pytest
import sys

_CHANNEL = 'dev'

_NOT_CHANNEL = 'alpha'


def test_channel_in(monkeypatch):
    """Validate channel_in()"""
    _setup(monkeypatch)
    assert pkconfig.channel_in(_CHANNEL), \
        'Should match configured channel'
    assert not pkconfig.channel_in(_NOT_CHANNEL), \
        'Should not match configured channel'
    assert pkconfig.channel_in(_NOT_CHANNEL, _CHANNEL), \
        'Should match configured channel'
    with pytest.raises(AssertionError):
        pkconfig.channel_in('bad channel')


def test_flatten_values():
    from pykern.pkconfig import flatten_values
    from pykern import pkcollections

    base = pkcollections.Dict()
    flatten_values(base, {'aa': 1, 'bb': {'cc': 3}})
    assert base['bb_cc'] == 3
    flatten_values(base, {'bb': {'dd': 4}})
    assert base['bb_cc'] == 3
    assert base['bb_dd'] == 4


def test_init(monkeypatch):
    """Validate initializing a module"""
    _setup(
        monkeypatch,
        dict(
            P1_M1_BOOL3='',
            P1_M1_BOOL4='y',
            P1_M1_P6='2012-12-12T12:12:12Z',
        ))
    from p1.m1 import cfg
    assert 'default2' == cfg['dict1']['d2'], \
        'Nothing should change dict1[d2]'
    assert dateutil.parser.parse('2012-12-12T12:12:12Z') == cfg['p6'], \
        'pkconfig_base.py sets time value and m1._custom_p6'
    assert 999 == cfg.dynamic_default10, \
        'When value is None, calls parser'
    assert False == cfg.bool1, \
        'When bool1 is none, is False'
    assert True == cfg.bool2, \
        'When bool2 is none, is True'
    pkconfig.reset_state_for_testing()
    assert False == cfg.bool3, \
        'bool3 should be overriden to be False'
    assert True == cfg.bool4, \
        'bool4 should be overriden to be True'


def test_init3(monkeypatch):
    """Validate parse_tuple"""
    _setup(monkeypatch, dict(P1_M1_TUPLE3='', P1_M1_TUPLE4='a:b'))
    from p1.m1 import cfg
    assert () == cfg.tuple1, \
        'When tuple1 is none, is empty'
    assert (1,) == cfg.tuple2, \
        'When tuple2 is none, is (1,)'
    pkconfig.reset_state_for_testing()
    assert () == cfg.tuple3, \
        'tuple3 should be overriden to be empty'
    assert ("a", "b") == cfg.tuple4, \
        'tuple4 should be overriden to be ("a", "b")'


def test_init4(monkeypatch):
    """Validate parse_set"""
    _setup(monkeypatch, dict(P1_M1_SET3='', P1_M1_SET4='a:b'))
    from p1.m1 import cfg
    assert set() == cfg.set1, \
        'When set1 is none, is empty'
    assert set([1]) == cfg.set2, \
        'When set2 is none, is (1,)'
    pkconfig.reset_state_for_testing()
    assert set() == cfg.set3, \
        'set3 should be overriden to be empty'
    assert set(('a', 'b')) == cfg.set4, \
        'set4 should be overriden to be ("a", "b")'


def test_to_environ(monkeypatch):
    from pykern import pkconfig
    from pykern.pkcollections import PKDict

    _setup(monkeypatch, dict(OTHER_THING='', P1_M1_SET4='a:b'))
    assert PKDict(P1_M1_REQ8='99', P1_M1_SET4='a:b') == pkconfig.to_environ(['p1.*'])
    assert PKDict(P1_M1_REQ8='99', P1_M1_SET4='a:b', OTHER_THING='') \
        == pkconfig.to_environ(['p1.*', 'other.thing'])
    assert PKDict() == pkconfig.to_environ(['nomatch.*'])


def _setup(monkeypatch, env=None):
    # Can't import anything yet
    global pkconfig
    data_dir = py.path.local(__file__).dirpath('pkconfig_data')
    monkeypatch.setenv('PYKERN_PKCONFIG_CHANNEL', _CHANNEL)
    monkeypatch.setenv('P1_M1_REQ8', '99')
    if data_dir not in sys.path:
        sys.path.insert(0, str(data_dir))
    from pykern import pkconfig
    pkconfig.reset_state_for_testing(add_to_environ=env)
