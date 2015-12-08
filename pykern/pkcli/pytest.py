# -*- coding: utf-8 -*-
u"""Wrapper for py.test

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import copy
import os
import py.path

from pykern import pkconfig
from pykern import pkio


def default_command(*args, **kwargs):
    """Run py.test first setting up ``$PYKERN_PKCONFIG_LOAD_PATH``

    If ``$PYKERN_PKCONFIG`` is not set, search up the file tree
    until it finds a ``setup.py``. If it can't find it, doesn't
    set the env var.

    Exec's ``py.test`` with whatever arguments it is given.

    Arguments are pass through to ``py.test``
    """
    env = copy.deepcopy(os.environ)
    if not pkconfig.LOAD_PATH_ENV_NAME in env:
        prev_p = None
        p = py.path.local()
        while prev_p != p:
            prev_p = p
            if p.join('setup.py').check(file=1):
                env[pkconfig.LOAD_PATH_ENV_NAME] = p.basename
                break
            p = py.path.local(p.dirname)
    os.execvpe('py.test', ('py.test',) + args, env)
