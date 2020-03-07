# -*- coding: utf-8 -*-
u"""PyTest plugin to setup pkconfig and add pkunit fixtures

This plugin will only be "active" if the setup.py in the package
imports `pykern.pksetup`. It also calls `pykern.pkconfig.append_load_path`,
which modifies global state.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import os

import pytest
# Do not import anything from pykern here

#: Is py.test being run in a package with a setup.py that imports pksetup
_uses_pykern = False

#: Initialized below
_no_recurse = None

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
def pytest_runtest_protocol(item, *args, **kwargs):
    """Make sure work directory is empty for a module.

    If `item` is in a module not seen before, it removes
    the `pkunit.work_dir`.

    Args:
        item (Item): pytest test item (case)

    Returns:
        None: always so that the next hook runs the item.
    """
    if not _uses_pykern:
        return
    from pykern import pkunit
    # Seems to be the only way to get the module under test
    m = item._request.module
    is_new = m != pkunit.module_under_test
    pkunit.module_under_test = m
    if is_new:
        from pykern import pkio
        pkio.unchecked_remove(pkunit.work_dir())


def _setup_py_parser():
    """Look for setup.py and set `_uses_pykern`

    Returns:
        str: root dir containing setup.py or None
    """
    global _uses_pykern
    import py.path
    prev_p = None
    p = py.path.local()
    while True:
        prev_p = p
        s = p.join('setup.py')
        if s.check(file=True):
            break
        p = py.path.local(p.dirname)
        if prev_p == p or len(str(prev_p)) <= len(str(p)):
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
