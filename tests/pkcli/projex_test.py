# -*- coding: utf-8 -*-
u"""pytest for `pykern.pkcli.projex`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import py
import pytest
import re
import subprocess

def test_init_rs_tree():
    """Normal case"""
    from pykern import pkio
    from pykern.pkcli import projex
    from pykern import pkunit


    with pkunit.save_chdir_work():
        name = 'rs_proj1'
        pkio.mkdir_parent(name)
        with pkio.save_chdir(name):
            subprocess.check_call(['git', 'init', '.'])
            subprocess.check_call(['git', 'config', 'user.email', 'pip@pykern.org'])
            subprocess.check_call(['git', 'config', 'user.name', 'pykern'])
            projex.init_rs_tree(
                description='some radiasoftee project',
            )
            for expect_fn, expect_re in (
                ('LICENSE', 'Apache License'),
                ('setup.py', "author='RadiaSoft LLC'"),
            ):
                assert re.search(expect_re, pkio.read_text(expect_fn)), \
                    '{} should exist and match "{}"'.format(expect_fn, expect_re)


def test_init_tree():
    """Normal case"""
    from pykern import pkio
    from pykern.pkcli import projex
    from pykern import pkunit

    with pkunit.save_chdir_work():
        name = 'proj1'
        pkio.mkdir_parent(name)
        with pkio.save_chdir(name):
            subprocess.check_call(['git', 'init', '.'])
            subprocess.check_call(['git', 'config', 'user.email', 'pip@pykern.org'])
            subprocess.check_call(['git', 'config', 'user.name', 'pykern'])
            projex.init_tree(
                name=name,
                author='zauthor',
                author_email='author@example.com',
                description='some python project',
                license='MIT',
                url='http://example.com',
            )
            pkio.write_text('tests/test_1.py', 'def test_1(): pass')
            for expect_fn, expect_re in (
                ('.gitignore', 'MANIFEST.in'),
                ('LICENSE', 'The MIT License'),
                ('README.md', 'licenses/MIT'),
                ('docs/_static/.gitignore', ''),
                ('docs/_templates/.gitignore', ''),
                ('docs/index.rst', name),
                ('setup.py', "author='zauthor'"),
                ('setup.py', r':copyright:.*zauthor\.'),
                ('tests/.gitignore', '_work'),
                (name + '/__init__.py', ''),
                (name + '/package_data/.gitignore', ''),
                (
                    '{}/{}_console.py'.format(name, name),
                    r"main\('{}'\)".format(name),
                ),
            ):
                assert re.search(expect_re, pkio.read_text(expect_fn)), \
                    '{} should exist and match "{}"'.format(expect_fn, expect_re)
            subprocess.check_call(['git', 'commit', '-m', 'initial'])
            # Do not install from PyPI
            pykern_path = py.path.local(__file__).dirpath().dirpath().dirpath()
            # pykern must be installed for setup.py to be able to be called
            subprocess.check_call(['pip', 'install', '-e', str(pykern_path)])
            subprocess.check_call(['python', 'setup.py', 'test'])
#TODO(robnagler) get rid of tox
#            subprocess.check_call(['python', 'setup.py', 'tox'])
