# -*- coding: utf-8 -*-
u"""PyTest plugin to setup pkconfig and add pkunit fixtures

This plugin will only be "active" if the setup.py in the package
imports `pykern.pksetup`. This module turns on ``pytest-xdist``'s
``--boxed`` option. It also calls `pykern.pkconfig.append_load_path`,
which modifies global state.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
# Do not import anything from pykern here

#: Is py.test being run in a package with a setup.py that imports pksetup
_uses_pykern = False

#: Initialized below
_no_recurse = None


@pytest.yield_fixture(scope='function')
def pk_chdir_work():
    """Yields ``pkunit.save_chdir_work``

    See `pykern.pkunit.save_chdir_work` for details.
    """
    from pykern import pkunit
    with pkunit.save_chdir_work() as d:
        yield d


@pytest.fixture(scope='module')
def pk_data_dir():
    """Returns ``pkunit.data_dir()``

    See `pykern.pkunit.data_dir` for details.
    """
    from pykern import pkunit
    return pkunit.data_dir()


@pytest.fixture(scope='module')
def pk_work_dir():
    """Returns ``pkunit.work_dir()``.


    See `pykern.pkunit.work_dir` for details.
    """
    from pykern import pkunit
    return pkunit.work_dir()


@pytest.hookimpl(tryfirst=True)
def pytest_ignore_collect(path, config):
    """Ignore _work and _data directories

    """
    if not _uses_pykern:
        return False
    global _no_recurse
    if not _no_recurse:
        import re
        _no_recurse = re.compile(r'(_work|_data)$')
    return bool(_no_recurse.search(str(path)))


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """See if package uses `pykern`, and set options accordingly

    Args:
        config (_pytest.config.Config): used for options
    """
    root_d = _setup_py_parser()
    if not root_d:
        return
    from pykern import pkconfig
    pkconfig.append_load_path(root_d.basename)
    import os
    if hasattr(os, 'fork'):
        config._parser.parse_setoption(['--boxed'], config.option, namespace=config.option)
    #norecursedirs = *_data *_work


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    if not _uses_pykern:
        return
    import pykern.pkunit
    # Seems to be the only way to get the module under test
    pykern.pkunit.module_under_test = item._request.module


def _setup_py_parser():
    """Look for setup.py and set `_uses_pykern`

    Returns:
        str: root dir containing setup.py or None
    """
    global _uses_pykern
    import py.path
    prev_p = None
    p = py.path.local()
    while prev_p != p:
        prev_p = p
        s = p.join('setup.py')
        if s.check(file=1):
            break
        p = py.path.local(p.dirname)
    else:
        return None
    _uses_pykern = _setup_py_contains_pykern(s)
    if _uses_pykern:
        return p
    return None


def _setup_py_contains_pykern(setup_py):
    """Parses setup.py to see if it imports pykern

    This is hacky, but good enough because pykern and
    pksetup are unique names. If someone comments out with
    a multiline string, it's not super dangerous.

    Args:
        setup_py (py.path): setup.py file name

    Returns:
        bool: True if setup.py imports pykern and pksetup
    """
    import re
    with open(str(setup_py)) as f:
        return bool(
            re.search(
                r'^\s*(from|import)\s+pykern\b.*\bpksetup\b',
                f.read(),
                flags=re.MULTILINE,
            ),
        )


@pytest.yield_fixture(scope='function')
def pk_chdir_work():
    """Yields result of ``pkunit.save_chdir_work``

    See `pykern.pkunit.save_chdir_work` for details.
    """
    from pykern import pkunit
    with pkunit.save_chdir_work() as d:
        yield d
