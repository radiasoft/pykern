# -*- coding: utf-8 -*-
u"""pytest for `pykern.setup`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import contextlib
import glob
import os
import py
import pytest
from subprocess import check_call

import pykern.io
import pykern.setup
import pykern.unittest


def test_build():
    """Create a normal distribution"""
    with _project_dir('conf1') as d:
        check_call(['python', 'setup.py', 'sdist'])
        assert 1 == len(glob.glob('dist/conf1*.tar.gz')), \
            'Verify setup.py sdist creates tar.gz file'


@contextlib.contextmanager
def _project_dir(project):
    """Copy "data_dir/project" to "work_dir/project"

    Initializes as a git repo.

    Args:
        project (str): subdirectory name

    Returns:
        py.path.local: working directory"""
    d = pykern.unittest.empty_work_dir().join(project)
    pykern.unittest.data_dir().join(d.basename).copy(d)
    with pykern.io.save_chdir(d):
        check_call(['git', 'init', '.'])
        pykern.io.write_file('.gitignore', '*')
        check_call(['git', 'add', '-f', '.gitignore'])
        # Need a commit
        check_call(['git', 'commit', '-m', 'n/a'])
        yield d
