# -*- coding: utf-8 -*-
u"""pytest for `pykern.trace`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import inspect
import os
import os.path
import pytest
import re
from io import StringIO


def test_conformance1(capsys):
    """Verify basic output"""
    # 3 the trace statement is three lines forward, hence +3
    this_file = os.path.relpath(__file__)
    control = this_file + ':' + str(inspect.currentframe().f_lineno + 3) + ':test_conformance1 t1'
    os.environ['PYKERN_TRACE'] = control
    from pykern.trace import trace, init
    trace('t1')
    out, err = capsys.readouterr()
    assert err == control + '\n', \
        'When control exactly matches file:line:func msg, output is same'
    trace('t2')
    out, err = capsys.readouterr()
    assert err == '', \
        'When trace msg does not match control, no output'
    init('t3')
    trace('t3 {}', 'p3')
    out, err = capsys.readouterr()
    assert re.search(r'test_conformance1 t3', err), \
        'When control is simple msg match, expect output'
    assert re.search(r't3 p3\n', err), \
        'When positional format *args, expect positional param in output'
    output = StringIO()
    init('t4', output)
    trace('t4 {k4}', k4='v4')
    out, err = capsys.readouterr()
    assert re.search(r'test_conformance1 t4 v4', output.getvalue()), \
        'When params is **kwargs, value is formatted from params'
    assert err == '', \
        'When output is passed to init(), stderr is empty'


def test_deviance1(capsys):
    """Test init exceptions"""
    import pykern.trace as t
    output = StringIO()
    t.init(r'(regex is missing closing parent', output)
    out, err = capsys.readouterr()
    assert t._printer is None, \
        'When control re.compile fails, _printer is not set'
    assert re.search(r'init failed', output.getvalue()), \
        'When an exception in init(), output indicates init failure'
    assert err == '', \
        'When an exception in init() and output, stderr is empty'
    t.init(r'[invalid regex', 'invalid file')
    assert t._printer is None
    out, err = capsys.readouterr()
    assert re.search(r'init failed', err), \
        'When exception in init() and output invalid, init failure written to stderr'


def test_deviance2(capsys):
    """Test max exceptions"""
    import pykern.trace as t
    t.init('.')
    for i in range(t.MAX_EXCEPTION_COUNT):
        t.trace('missing format value {}')
        out, err = capsys.readouterr()
        assert re.search(r'invalid trace format', err), \
            'When fmt is incorrect, output indicates format error'
    t.trace('any error{}')
    out, err = capsys.readouterr()
    assert err == '', \
        'When exception_count exceeds MAX_EXCEPTION_COUNT, no output'
