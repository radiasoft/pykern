# -*- coding: utf-8 -*-
"""pytest for `pykern.pksetup`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern.pkdebug import pkdc, pkdp

import contextlib
import glob
import os
import os.path
import py
import pytest
import re
import sys
from subprocess import check_call
import tarfile

from pykern import pkio
from pykern import pksetup
from pykern import pkunit


def test_build_clean():
    """Create a normal distribution"""
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
                dat = os.path.join(base, 'scripts', 'script1')
                assert t.getmember(str(dat)) is not None, \
                    'When sdist, scripts is included.'
        else:
            # TODO(robnagler) need to handle zip for Windows?
            pass
        check_call(['python', 'setup.py', 'build'])
        dat = os.path.join('build', 'lib', 'conf1', 'package_data', 'data1')
        assert os.path.exists(dat), \
            'When package_data, installed in lib'
        bin_dir = 'scripts-{}.{}'.format(*(sys.version_info[0:2]))
        dat = os.path.join('build', bin_dir, 'script1')
        assert os.path.exists(dat), \
            'When scripts, installed in ' + bin_dir
        # Fails if any test fails
        check_call(['python', 'setup.py', 'test'])
        check_call(['python', 'setup.py', 'sdist'])
        check_call(['python', 'setup.py', 'pkclean'])
        assert not os.path.exists('build'), \
            'When pkclean runs, build directory should not exist'


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
