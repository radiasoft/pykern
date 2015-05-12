# -*- coding: utf-8 -*-
u"""Wrapper for distutils.core.setup to simplify creating of `setup.py` files.

Python `setup.py` files should be short for well-structured projects.
`b_setup.setup` assumes there are directories such as `tests`, `docs`,
`bin`, etc. PyKern Projects use `py.test` so the appropriate `PyTest`
class is provided by this module.

Example:

    A sample ``setup.py`` script::

        setup(
            name='pykern',
            description='Python application support from Bivio',
            author='Bivio Software, Inc.',
            author_email='pip@pybiv.io',
            url='http://pybiv.io',
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
import jinja2
import json
import os
import os.path
import pip.download
import pip.req
import re
import setuptools.command.test
import subprocess
import sys


from pykern.compat import locale_check_output, locale_str
from pykern.resource import PACKAGE_DATA


#: File computed globals are stored
STATE_FILE='pykern_setup.json'


class PyTest(setuptools.command.test.test):
    """Proper intiialization of `py.test`"""

    def initialize_options(self):
        """Initialize pytest_args"""
        self.pytest_args = []

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
        **kwargs: see `distutils.core.setup`
    """
    prev_dir = os.getcwd()
    try:
        f = inspect.currentframe().f_back
        d = os.path.dirname(f.f_code.co_filename)
        if len(d):
            os.chdir(d)
        print("PWD=" + os.getcwd())
        print(locale_check_output(['ls', '-lR']))
        _setup(kwargs)
    finally:
        del f
        if prev_dir:
            os.chdir(prev_dir)


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


def _package_data(pkg_name):
    """Find all package data checked in with git. If not in a git repository.

    Assumes git is installed and git repo. If not, blows up.

    Args:
        pkg_name (str): name of the package (directory)

    Returns:
        list: Files under git control to include in package
    """
    return _git_ls_files([
        '--others', '--exclude-standard', os.path.join(pkg_name, PACKAGE_DATA)])


def _relative_open(filename, *args):
    """Open a file relative to ``__file__``.

    Args:
        filename (str): relative pathname
        *args (list): Other args to pass to open

    Returns:
        io.TextIOWrapper: file just opened
    """
    return open(filename, *args)



def _setup(kwargs):
    """Does the work of :func:`setup`

    Args:
        kwargs (dict): passed in to :func:`setup`
    """
    with _relative_open('README.md') as f:
        long_description = f.read()
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
        'entry_points': _setup_entry_points(name),
        'install_requires': install_requires,
        'long_description': long_description,
        'name': name,
        'packages': [name],
        'tests_require': ['pytest'],
    }
    base = _state(base)
    base.update(kwargs)
    distutils.core.setup(**base)


def _setup_entry_points(pkg_name):
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


def _sphinx_apidoc(base):
    """Call `sphinx-apidoc` with appropriately configured ``conf.py``.

    Args:
        base (dict): values to be passed to ``conf.py.in`` template
    """
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
            '{}: not found, incorrectly built sdist'.format(STATE_FILE)
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
include README.md
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
