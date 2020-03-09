# -*- coding: utf-8 -*-
u"""Run python code

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

# Avoid pykern imports so avoid dependency issues
import imp
import os.path
import sys


def run_path_as_module(fname):
    """Runs ``fname`` in a module

    Args:
        fname (str or py.path.local): file to be exec'd

    Returns:
        module: imported file as a module
    """
    fname = str(fname)
    mn = os.path.basename(fname).replace('.', '_')
    m = imp.new_module(mn)
    with open(fname, 'rU') as f:
        code = compile(f.read(), fname, 'exec')
    if sys.version_info[0] >= 3:
        exec(code, m.__dict__)
    else:
        exec('exec code in m.__dict__')
    return m
