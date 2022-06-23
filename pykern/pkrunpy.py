# -*- coding: utf-8 -*-
"""Run python code

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
# Avoid pykern imports so avoid dependency issues
import importlib.machinery
import importlib.util
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
    mn = os.path.basename(fname).replace(".", "_")
    m = importlib.util.module_from_spec(importlib.machinery.ModuleSpec(mn, None))
    with open(fname, "rt") as f:
        code = compile(f.read(), fname, "exec")
    exec(code, m.__dict__)
    return m
