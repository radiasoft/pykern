# -*- coding: utf-8 -*-
u"""wrapper for running simulations

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

def default_command(cmd, *args, **kwargs):
    import sys
    return getattr(sys.modules[__name__], '_'+ cmd)(*args, **kwargs)


def _run(*args):
    """Run a command with the proper local python and path environment

    Args:
        args (tuple): what to run (flags and all)
    """
    import subprocess
    import py.path
    import os

    venv = py.path.local('venv')
    env = os.environ.copy()
    env['PATH'] = str(venv.join('bin')) + ':' + env['PATH']
    env['PYTHONUSERBASE'] = str(venv)
    subprocess.check_call(args, env=env)
