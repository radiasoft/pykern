# -*- coding: utf-8 -*-
u"""pytest for `pykern.pksetup`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import contextlib
import glob
import os
import os.path
import py
import pytest
import re
from subprocess import check_call
import tarfile

from pykern.pkdebug import *

from pykern import pkio
from pykern import pksetup
from pykern import pkunit


def test_build():
    """Create a normal distribution"""
    import pykern.pkdebug
    with _project_dir('conf1') as d:
        check_call(['python', 'setup.py', 'sdist'])
        arc = glob.glob(os.path.join('dist', 'conf1*'))
        assert 1 == len(arc), \
            'Verify setup.py sdist creates an archive file'
        arc = arc[0]
        base = re.search(r'(.+)\.tar\.gz', os.path.basename(arc))
        if base:
            base = base.group(1)
            with tarfile.open(arc, 'r:gz') as t:
                dat = os.path.join(base, 'conf1', 'package_data', 'data1')
                assert t.getmember(str(dat)) is not None, \
                    'When sdist, package_data is included.'
        else:
            # TODO(robnagler) need to handle zip for Windows?
            pass
        check_call(['python', 'setup.py', 'build'])
        dat = os.path.join('build', 'lib', 'conf1', 'package_data', 'data1')
        assert os.path.exists(dat)
        # Fails if any test fails
        check_call(['python', 'setup.py', 'test'])


@contextlib.contextmanager
def _project_dir(project):
    """Copy "data_dir/project" to "work_dir/project"

    Initializes as a git repo.

    Args:
        project (str): subdirectory name

    Returns:
        py.path.local: working directory"""
    d = pkunit.empty_work_dir().join(project)
    pkunit.data_dir().join(d.basename).copy(d)
    with pkio.save_chdir(d):
        check_call(['git', 'init', '.'])
        check_call(['git', 'add', '.'])
        # Need a commit
        check_call(['git', 'commit', '-m', 'n/a'])
        yield d
