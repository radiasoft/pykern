# -*- coding: utf-8 -*-
u"""pytest for `pykern.resource`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import glob
import os.path

import pytest

from pykern import pkio
from pykern import pkjinja
from pykern import pkunit


def test_render_resource():
    t1 = pkunit.import_module_from_data_dir('t1')
    with pkunit.save_chdir_work():
        out = 'out'
        expect = '\n!v1!\n'
        assert expect == t1.render(None), \
            'render_resource should return rendered template'
        assert not glob.glob('*'), \
            'render_resource should not create any files'
        assert expect == t1.render(out), \
            'render_resource should return string even when writing to file'
        assert expect == pkio.read_text(out), \
            'With out, render_resource should write file'
