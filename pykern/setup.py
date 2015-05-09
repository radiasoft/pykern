# -*- coding: utf-8 -*-
"""Wrapper for distutils.core.setup to simplify creating of `setup.py` files.

Python `setup.py` files should be short for well-structured projects.
`b_setup.setup` assumes there are directories such as `tests`, `docs`,
`bin`, etc. PyKern Projects use `py.test` so the appropriate `PyTest`
is provided.

Example:

    A sample ``setup.py`` script:

        setup(
            name='pykern',
            description='Python application support from Bivio',
            author='Bivio Software, Inc.',
            author_email='pip@pybiv.io',
            url='http://pybiv.io',
        )

Assumes the use of ``pytest`` for tests. GUI and console scripts are found
automatically by special suffixes ``_gui.py`` and ``_console.py``. See ``setup``
documentation for an example.

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""

import datetime
import distutils.core
import glob
import os.path
import pip.download
import pip.req
import re
import setuptools.command.test
import subprocess
import sys

from pykern.resource import PACKAGE_DATA


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
    with open('README.md') as f:
        long_description = f.read()
    reqs = pip.req.parse_requirements(
        'requirements.txt', session=pip.download.PipSession())
    install_requires = [str(i.req) for i in reqs]
    # Using a commit date is not correct, because some files may not be committed.
    # Therefore, this version has to be newer. Since we use a promotion model,
    # there is only one version for all release channels (develop, alpha,
    # beta, stable).
    version = datetime.datetime.utcnow().strftime('%Y%m%d.%H%M%S')
    base = {
        'author': 'Bivio Software, Inc.',
        'classifiers': [],
        'cmdclass': {'test': PyTest},
        'install_requires': install_requires,
        'long_description': long_description,
        'packages': [kwargs['name']],
        'tests_require': ['pytest'],
        'version': version,
    }
    base['entry_points'] = _setup_entry_points(kwargs['name'])
    # pykern.resource assumes this is a top-level name. This is
    # implicit with Python's pkg_resources, too.
    data = _package_data(kwargs['name'])
    if data:
        base['package_data'] = {kwargs['name']: data}
    base.update(kwargs)
    distutils.core.setup(**base)


def _package_data(pkg_name):
    """Find all package data checked in with git. If not in a git repository.

    Assumes git is installed

    Args:
        pkg_name: name of the package (directory)

    Returns:
        list: Files under git control to include in package
    """
    try:
        # Will return nothing if package_data doesn't exist or no files in it
        # so only error is if not a git repo
        out = subprocess.check_output(
            ['git', 'ls-files', os.path.join(pkg_name, PACKAGE_DATA)],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        if re.search(r'\bnot\b.*\brepo.*', e.output, flags=re.IGNORECASE):
            return []
        raise
    return out.splitlines()


def _setup_entry_points(pkg_name):
    """Find all *_{console,gui}.py files and define them

    Args:
        pkg_name: name of the package (directory)

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
