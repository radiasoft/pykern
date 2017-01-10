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

# Do not import anything from pk be fresh

# Test without logging redirects, because need to test native and then
# test _logging_uninstall()
os.environ['PYKERN_PKDEBUG_REDIRECT_LOGGING'] = ''

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
    assert re.search(r'\w{3} .\d \d\d:\d\d:\d\d +\d+ +\d+ ', err), \
        'When output has time, matches regex'


def test_init_deviance(capsys):
    """Test init exceptions"""
    import pykern.pkdebug as d
    output = six.StringIO()
    d.init(control=r'(regex is missing closing parent', output=output)
    out, err = capsys.readouterr()
    assert not d._have_control, \
        'When control re.compile fails, _printer is not set'
    assert 'compile error' in output.getvalue(), \
        'When an exception in init(), output indicates init failure'
    assert err == '', \
        'When an exception in init() and output, stderr is empty'
    d.init(control=r'[invalid regex', output='/invalid/file/path')
    assert not d._have_control, \
        'When invalid control regex, _have_control should be false'
    out, err = capsys.readouterr()
    assert 'compile error' in err, \
        'When exception in init() and output invalid, init failure written to stderr'


def test_ipython():
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
        o = p.stdout.read()
        assert re.search("Out\\[1\\]: \n?'abcdef'", o), \
            'IPython pkdp() is evaluated and written to stdout {}'.format(o)

    except OSError as e:
        # If we don't have IPython, then ignore error
        import errno
        if e.errno != errno.ENOENT:
            reraise


def test_logging(capsys):
    """Verify basic output"""
    import logging
    from pykern import pkdebug
    logging.warn('warn_xyzzy')
    out, err = capsys.readouterr()
    assert '%(levelname)s:%(name)s:%(message)s' == logging.BASIC_FORMAT, \
        'logging.BASIC_FORMAT is not what is assumed in pkdebug and tests below'
    assert 'WARNING:root:warn_xyzzy\n' == err, \
        'When logging is first initialized, warn should output'
    logging.info('info_xyzzy')
    out, err = capsys.readouterr()
    assert '' == err, \
        'When logging is first initialized, info should not output'
    pkdebug.init(control=None, output=None, redirect_logging=True)
    logging.debug('debug_xyzzy')
    l = logging.getLogger('whatever')
    l.debug('whatever_debug_xyzzy')
    out, err = capsys.readouterr()
    assert '' == err , \
        'When no control, logging.debug should not output anything'
    logging.info('info_xyzzy')
    l.info('whatever_info_xyzzy')
    out, err = capsys.readouterr()
    r = re.compile(
        r'INFO:root:info_xyzzy.*?INFO:whatever:whatever_info_xyzzy',
        flags=re.DOTALL,
    )
    matches = r.findall(err)
    assert 1 == len(matches), \
        'When no control, logging.info should output once per log; err=' + err
    logging.warn('warn_xyzzy')
    l.warn('whatever_warn_xyzzy')
    out, err = capsys.readouterr()
    r = re.compile(
        r'WARNING:root:warn_xyzzy.*?WARNING:whatever:whatever_warn_xyzzy',
        flags=re.DOTALL,
    )
    matches = r.findall(err)
    assert 1 == len(matches), \
        'When no control, logging.warn should output once per log; err=' + err
    pkdebug.init(control='xyzzy', output=None, redirect_logging=True)
    logging.debug('debug_xyzzy')
    l.debug('whatever_debug_xyzzy')
    out, err = capsys.readouterr()
    assert 'DEBUG:root:debug_xyzzy' in err, \
        'When have control that matches, logging.debug should output'
    assert 'DEBUG:whatever:whatever_debug_xyzzy' in err, \
        'When have control that matches, logging.debug should output'
    pkdebug.init(control='xyzzy', output=None, redirect_logging=False)
    # Assumes default logging level is WARN
    logging.debug('debug_xyzzy')
    l.debug('whatever_debug_xyzzy')
    logging.info('info_xyzzy')
    l.info('whatever_info_xyzzy')
    logging.warn('warn_xyzzy')
    out, err = capsys.readouterr()
    assert 'WARNING:root:warn_xyzzy\n' == err, \
        'When logging is not redirected, info and debug should not output'


def test_pkdc(capsys):
    """Verify basic output"""
    # The pkdc statement is four lines forward, hence +4
    this_file = os.path.relpath(__file__)
    control = this_file + ':' + str(inspect.currentframe().f_lineno + 4) + ':test_pkdc t1'
    from pykern import pkdebug
    from pykern.pkdebug import pkdc, init, pkdp
    init(control=control)
    pkdc('t1')
    out, err = capsys.readouterr()
    assert control + '\n' == err , \
        'When control exactly matches file:line:func msg, output is same'
    pkdc('t2')
    out, err = capsys.readouterr()
    assert '' == err, \
        'When pkdc msg does not match control, no output'
    init(control='t3')
    pkdc('t3 {}', 'p3')
    out, err = capsys.readouterr()
    assert 'test_pkdc t3' in err, \
        'When control is simple msg match, expect output'
    assert 't3 p3\n' in err, \
        'When positional format *args, expect positional param in output'
    output = six.StringIO()
    init(control='t4', output=output)
    pkdc('t4 {k4}', k4='v4')
    out, err = capsys.readouterr()
    assert 'test_pkdc t4 v4' in output.getvalue(), \
        'When params is **kwargs, value is formatted from params'
    assert '' == err, \
        'When output is passed to init(), stderr is empty'


def test_pkdc_deviance(capsys):
    """Test max exceptions"""
    import pykern.pkdebug as d
    d.init(control='.')
    for i in range(d.MAX_EXCEPTION_COUNT):
        d.pkdc('missing format value {}')
        out, err = capsys.readouterr()
        assert 'invalid format' in err, \
            'When fmt is incorrect, output indicates format error'
    d.pkdc('any error{}')
    out, err = capsys.readouterr()
    assert '' == err, \
        'When exception_count exceeds MAX_EXCEPTION_COUNT, no output'


def test_pkdexc():
    """Basic output and return with `pkdp`"""
    from pykern.pkdebug import init, pkdexc
    init()

    def force_error():
        xyzzy

    def tag1234():
        try:
            force_error()
        except:
            return pkdexc()

    actual = tag1234()
    for expect in 'xyzzy', 'force_error', 'tag1234', 'test_pkdexc':
        assert expect in actual, \
            '{}: call not found: {}'.format(expect, actual)
    assert not re.search(r'tag1234.*tag1234.*tag1234', actual, flags=re.DOTALL), \
        'tag1234: found routine thrice in exception stack: {}'.format(actual)


def test_pkdp(capsys):
    """Basic output and return with `pkdp`"""
    from pykern.pkdebug import pkdp, init
    init()
    assert 333 == pkdp(333)
    out, err = capsys.readouterr()
    assert str(333) in err, \
        'When pkdp called, arg chould be converted to str,'


def test_pkdpretty():
    """Pretty printing arbitrary objects`"""
    from pykern.pkdebug import pkdpretty
    recursive = []
    any_obj = object()
    recursive.append(recursive)
    for obj, expect in (
        (u'{"a":1}', '{\n    "a": 1\n}\n'),
        ('{"a":1}', '{\n    "a": 1\n}\n'),
        ({'b': set([1])}, "{   'b': set([1])}\n"),
        (recursive, recursive),
        (any_obj, any_obj),
    ):
        assert expect == pkdpretty(obj)


def _z(msg):
    """Useful for debugging this module"""
    with open('/dev/tty', 'w') as f:
        f.write(str(msg) + '\n')
