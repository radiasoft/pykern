# -*- coding: utf-8 -*-
u"""Wrapper for distutils.core.setup to simplify creating of `setup.py` files.

Python `setup.py` files should be short for well-structured projects.
`b_setup.setup` assumes there are directories such as `tests`, `docs`,
`bin`, etc. PyKern Projects use `py.test` so the appropriate `PyTest`
class is provided by this module.

Example:

    A sample ``setup.py`` script::

        setup(
            name='pyexample',
            description='Some Example app',
            author='Example, Inc.',
            author_email='somebody@example.com',
            url='http://example.com',
        )

Assumptions:

    - the use of ``pytest`` for tests. GUI and console scripts are
      found automatically by special suffixes ``_gui.py`` and
      ``_console.py``. See ``setup`` documentation for an example.

    - Under git control. Even if you are building an app for the first
      time, you should create the repo first. Does not assume anything
      about the remote (i.e. need not be a GitHub repo).

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import datetime
import distutils.core
import glob
import inspect
import json
import os
import os.path
import pip.download
import pip.req
import re
import setuptools.command.test
import subprocess
import sys


import pykern.io
from pykern.compat import locale_check_output, locale_str
from pykern.resource import PACKAGE_DATA


#: File computed globals are stored
STATE_FILE='pykern_setup.json'


class PyTest(setuptools.command.test.test):
    """Proper intiialization of `py.test`"""

    def initialize_options(self):
        """Initialize pytest_args. Always run ``--boxed``.

        We require pytest plug ``xdist``.
        See https://bitbucket.org/pytest-dev/pytest-xdist#rst-header-boxed
        """
        self.pytest_args = ['--boxed']

    def finalize_options(self):
        """Initialize test_args and set test_suite to True"""
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        """Import `pytest` and calls `main`. Calls `sys.exit` with result"""
        import pytest
        exit = pytest.main(self.pytest_args)
        sys.exit(exit)


def setup(**kwargs):
    """Parses `README.md` and `requirements.txt`, sets some defaults, then
    calls `distutils.core.setup`.

    Scripts are found by looking for files in the top level package directory
    which end with ``_console.py`` or ``_gui.py``. These files must have a
    function called ``main``.

    Example:
        The file ``pykern_console.py`` might contain::

            def main():
                print('hello world')

        This would create a program called command line program ``pykern`` which
        would call ``main()`` when invoked.

    Args:
        kwargs: see `distutils.core.setup`
    """
    with _relative_open('README.md') as f:
        long_description = f.read()
        # setup complains about missing README.txt
        pykern.io.write_file('README.txt', long_description)
    reqs = pip.req.parse_requirements(
        'requirements.txt', session=pip.download.PipSession())
    install_requires = [str(i.req) for i in reqs]
    # If the incoming is unicode, this works in Python3
    # https://bugs.python.org/issue13943
    name = str(kwargs['name'])
    base = {
        'author': kwargs['author'],
        'classifiers': [],
        'cmdclass': {'test': PyTest},
        'entry_points': _entry_points(name),
        'install_requires': install_requires,
        'long_description': long_description,
        'name': name,
        'packages': _packages(name),
        'tests_require': ['pytest'],
    }
    base = _state(base)
    base.update(kwargs)
    distutils.core.setup(**base)


def _entry_points(pkg_name):
    """Find all *_{console,gui}.py files and define them

    Args:
        pkg_name (str): name of the package (directory)

    Returns:
        dict: Mapping of script names to module:methods
    """
    res = {}
    for s in ['console', 'gui']:
        tag = '_' + s
        for p in glob.glob(os.path.join(pkg_name, '*' + tag + '.py')):
            m = re.search(
                r'^([a-z]\w+)' + tag, os.path.basename(p), flags=re.IGNORECASE)
            if m:
                ep = res.setdefault(s + '_scripts', [])
                #TODO(robnagler): assert that 'def main()' exists in python module
                ep.append('{} = {}.{}:main'.format(m.group(1), pkg_name, m.group(0)))
    return res


def _git_ls_files(extra_args):
    """Find all the files under git control

    Will return nothing if package_data doesn't exist or no files in it.

    Args:
        extra_args (list): other args to append to command

    Returns:
        list: Files under git control.
    """
    cmd = ['git', 'ls-files']
    cmd.extend(extra_args)
    out = locale_check_output(cmd, stderr=subprocess.STDOUT)
    return out.splitlines()


def _packages(name):
    """Find all packages by looking for ``__init__.py`` files.

    Mostly borrowed from https://bitbucket.org/django/django/src/tip/setup.py

    Args:
        name (str): name of the package (directory)

    Returns:
        list: packages names
    """

    def _fullsplit(path, result=None):
        """
        Split a pathname into components (the opposite of os.path.join) in a
        platform-neutral way.

        """
        if result is None:
            result = []
        head, tail = os.path.split(path)
        if head == '':
            return [tail] + result
        if head == path:
            return result
        return _fullsplit(head, [tail] + result)

    res = []
    for dirpath, _, filenames, in os.walk(name):
        if '__init__.py' in filenames:
            res.append(str('.'.join(_fullsplit(dirpath))))
    return res


def _package_data(name):
    """Find all package data checked in with git and otherwise.

    Asserts git is installed and git repo.

    Args:
        name (str): name of the package (directory). Will be
            joined with PACKAGE_DATA

    Returns:
        list: Files to include in package
    """
    d = os.path.join(name, PACKAGE_DATA)
    res = _git_ls_files(['--others', '--exclude-standard', d])
    res.extend(_git_ls_files([d]))
    return sorted(res)


def _relative_open(filename, *args):
    """Open a file relative to ``__file__``.

    Args:
        filename (str): relative pathname
        *args (list): Other args to pass to open

    Returns:
        io.TextIOWrapper: file just opened
    """
    return open(filename, *args)


def _sphinx_apidoc(base):
    """Call `sphinx-apidoc` with appropriately configured ``conf.py``.

    Args:
        base (dict): values to be passed to ``conf.py.in`` template
    """
    # Deferred import so initial setup.py works
    import jinja2
    output = 'docs/conf.py'
    template = output + '.in'
    with _relative_open(template) as f:
        d = f.read()
    d = jinja2.Template(d).render(base)
    with _relative_open(output, 'w') as f:
        f.write(d)
    subprocess.check_call([
        'sphinx-apidoc',
        '-f',
        '-o',
        os.path.dirname(output),
        base['name'],
    ])


def _state(base):
    """Gets global values (package_data, version, etc.) or computes them.

    If in a git repository, computes the globals first from the git repo values.

    Otherwise, reads pykern_setup.json, which will be included in the ``MANIFEST.in``.

    Args:
        base (dict): incoming setup confi

    Returns:
        dict: new base state
    """
    if os.path.isdir('.git'):
         state = _state_compute(base)
    else:
        assert os.path.isfile(STATE_FILE), \
            '{}: not found, incorrectly built sdist or not git repo?'.format(STATE_FILE)
        with _relative_open(STATE_FILE) as f:
            state = json.load(f.read())
    base.update(state)
    if os.getenv('READTHEDOCS'):
        _sphinx_apidoc(base)
    return base


def _state_compute(base):
    """Create :attr:`STATE_FILE` setting version, package_data, etc.
    """
    state = {
        'version': _version(),
    }
    pd = _package_data(base['name'])
    if pd:
        state['package_data'] = pd
    with _relative_open(STATE_FILE, 'w') as f:
        # dump() does not work: "TypeError: must be unicode, not str"
        f.write(json.dumps(state, ensure_ascii=False))
    with _relative_open('MANIFEST.in', 'w') as f:
        s = '''include {}
include LICENSE
include README.txt
include requirements.txt
'''.format(STATE_FILE)
        f.write(s)
    return state


def _version():
    """Chronological version string for most recent commit or time of newer file.

    Finds the commit date of the most recent branch. Uses ``git
    ls-files`` to find files under git control which are modified or
    to be deleted, in which case we assume this is a developer, and we
    should just use the current time for the version. It will be newer
    than any committed version, which is all we care about for upgrades.

    Returns:
        str: Chronological version "yyyymmdd.hhmmss"

    """
    # Under development?
    if len(_git_ls_files(['--modified', '--deleted'])):
        vt = datetime.datetime.utcnow()
    else:
        branch = locale_check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD']).rstrip()
        vt = locale_check_output(
            ['git', 'log', '-1', '--format=%ct', branch]).rstrip()
        vt = datetime.datetime.fromtimestamp(float(vt))
    return vt.strftime('%Y%m%d.%H%M%S')
