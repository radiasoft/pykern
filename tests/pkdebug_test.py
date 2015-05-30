# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkdebug`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import inspect
import os
import os.path
import pytest
from io import StringIO


from pykern import pkio
from pykern import pkunit

def test_cpr(capsys):
    """Verify basic output"""
    # 3 the cpr statement is three lines forward, hence +3
    this_file = os.path.relpath(__file__)
    control = this_file + ':' + str(inspect.currentframe().f_lineno + 3) + ':test_cpr t1'
    os.environ['PYKERN_DEBUG_CONTROL'] = control
    from pykern.pkdebug import cpr, init
    cpr('t1')
    out, err = capsys.readouterr()
    assert err == control + '\n', \
        'When control exactly matches file:line:func msg, output is same'
    cpr('t2')
    out, err = capsys.readouterr()
    assert err == '', \
        'When cpr msg does not match control, no output'
    init('t3')
    cpr('t3 {}', 'p3')
    out, err = capsys.readouterr()
    assert 'test_cpr t3' in err, \
        'When control is simple msg match, expect output'
    assert 't3 p3\n' in err, \
        'When positional format *args, expect positional param in output'
    output = StringIO()
    init('t4', output)
    cpr('t4 {k4}', k4='v4')
    out, err = capsys.readouterr()
    assert 'test_cpr t4 v4' in output.getvalue(), \
        'When params is **kwargs, value is formatted from params'
    assert err == '', \
        'When output is passed to init(), stderr is empty'


def test_cpr_dev(capsys):
    """Test max exceptions"""
    import pykern.pkdebug as d
    d.init('.')
    for i in range(d.MAX_EXCEPTION_COUNT):
        d.cpr('missing format value {}')
        out, err = capsys.readouterr()
        assert 'invalid format' in err, \
            'When fmt is incorrect, output indicates format error'
    d.cpr('any error{}')
    out, err = capsys.readouterr()
    assert err == '', \
        'When exception_count exceeds MAX_EXCEPTION_COUNT, no output'


def test_init(capsys):
    f = pkunit.empty_work_dir().join('f1')
    from pykern.pkdebug import dpr, init
    init(output=f)
    dpr('init1')
    out, err = capsys.readouterr()
    assert '' == err, \
        'When output is a file name, nothing goes to err'
    assert 'init1\n' in pkio.read_text(f), \
        'File output should contain msg'


def test_init_dev(capsys):
    """Test init exceptions"""
    import pykern.pkdebug as d
    output = StringIO()
    d.init(r'(regex is missing closing parent', output)
    out, err = capsys.readouterr()
    assert not d._have_control, \
        'When control re.compile fails, _printer is not set'
    assert 'compile error' in output.getvalue(), \
        'When an exception in init(), output indicates init failure'
    assert err == '', \
        'When an exception in init() and output, stderr is empty'
    d.init(r'[invalid regex', '/invalid/file/path')
    assert not d._have_control, \
        'When invalid control regex, _have_control should be false'
    out, err = capsys.readouterr()
    assert 'compile error' in err, \
        'When exception in init() and output invalid, init failure written to stderr'


def test_ipr(capsys):
    """Basic output and return with `ipr`"""
    from pykern.pkdebug import ipr, init
    init()
    assert 333 == ipr(333)
    out, err = capsys.readouterr()
    assert str(333) in err, \
        'When ipr called, arg chould be converted to str,'
