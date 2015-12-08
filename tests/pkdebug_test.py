# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkdebug`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import inspect
import os
import os.path
import pytest
import re
import six

# Do not import anything from pk so test_pkdc() can be fresh

def test_pkdc(capsys):
    """Verify basic output"""
    # The pkdc statement is four lines forward, hence +4
    this_file = os.path.relpath(__file__)
    control = this_file + ':' + str(inspect.currentframe().f_lineno + 4) + ':test_pkdc t1'
    from pykern import pkdebug
    from pykern.pkdebug import pkdc, init, pkdp
    pkdebug.init(control=control)
    pkdc('t1')
    out, err = capsys.readouterr()
    assert control + '\n' == err , \
        'When control exactly matches file:line:func msg, output is same'
    pkdc('t2')
    out, err = capsys.readouterr()
    assert '' == err, \
        'When pkdc msg does not match control, no output'
    init('t3')
    pkdc('t3 {}', 'p3')
    out, err = capsys.readouterr()
    assert 'test_pkdc t3' in err, \
        'When control is simple msg match, expect output'
    assert 't3 p3\n' in err, \
        'When positional format *args, expect positional param in output'
    output = six.StringIO()
    init('t4', output)
    pkdc('t4 {k4}', k4='v4')
    out, err = capsys.readouterr()
    assert 'test_pkdc t4 v4' in output.getvalue(), \
        'When params is **kwargs, value is formatted from params'
    assert '' == err, \
        'When output is passed to init(), stderr is empty'


def test_pkdc_deviance(capsys):
    """Test max exceptions"""
    import pykern.pkdebug as d
    d.init('.')
    for i in range(d.MAX_EXCEPTION_COUNT):
        d.pkdc('missing format value {}')
        out, err = capsys.readouterr()
        assert 'invalid format' in err, \
            'When fmt is incorrect, output indicates format error'
    d.pkdc('any error{}')
    out, err = capsys.readouterr()
    assert '' == err, \
        'When exception_count exceeds MAX_EXCEPTION_COUNT, no output'


def test_init(capsys):
    from pykern import pkunit
    f = pkunit.empty_work_dir().join('f1')
    from pykern.pkdebug import pkdp, init
    init(output=f)
    pkdp('init1')
    out, err = capsys.readouterr()
    assert '' == err, \
        'When output is a file name, nothing goes to err'
    from pykern import pkio
    assert 'init1\n' in pkio.read_text(f), \
        'File output should contain msg'
    init(output=None, want_pid_time=True)
    pkdp('init2')
    out, err = capsys.readouterr()
    assert re.search(r'\w{3} .\d \d\d:\d\d:\d\d *\d+ ', err), \
        'When output has time, matches regex'


def test_ipython(capsys):
    import pykern.pkdebug
    from pykern.pkdebug import pkdp
    pykern.pkdebug.init(output=None)
    # Overwrite the _ipython_write method. This doesn't test how ipython is
    # running. We'll do that separately
    save = []
    def _write(msg):
        save.append(msg)
    try:
        pykern.pkdebug._ipython_write = _write
        pkdp('abcdefgh')
        assert 'abcdefgh' in save[0], \
            'When _ipython_write is set, should be called if no output'
    finally:
        pykern.pkdebug._ipython_write = None
    import subprocess
    try:
        p = subprocess.Popen(
            ['ipython',  '--colors', 'NoColor', '-c','from pykern.pkdebug import pkdp; pkdp("abcdef")'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Not a brilliant test, but does demonstrate that write_err works
        assert '<module> abcdef' in p.stderr.read(), \
            'When in IPython, pkdp() should output to stdout'
        # We make this rigid, because we want to know when IPython interpreter changes
        assert "Out[1]: 'abcdef'" in p.stdout.read(), \
            'When in IPython, return of pkdp() is evaluated and written to stdout'
    except OSError as e:
        # If we don't have IPython, then ignore error
        import errno
        if e.errno != errno.ENOENT:
            reraise


def test_init_deviance(capsys):
    """Test init exceptions"""
    import pykern.pkdebug as d
    output = six.StringIO()
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


def test_pkdp(capsys):
    """Basic output and return with `pkdp`"""
    from pykern.pkdebug import pkdp, init
    init()
    assert 333 == pkdp(333)
    out, err = capsys.readouterr()
    assert str(333) in err, \
        'When pkdp called, arg chould be converted to str,'


def _z(msg):
    """Useful for debugging this module"""
    with open('/dev/tty', 'w') as f:
        f.write(str(msg) + '\n')
