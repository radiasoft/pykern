# -*- coding: utf-8 -*-
"""db configuration

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import os.path
import sys

#: Relative to current directory only in dev mode
_DEFAULT_ROOT = "run"


def init_db_dir(package_object):
    r = (
        pkio.py_path(
            sys.modules[pkinspect.root_package(package_object)].__file__,
        )
        .dirpath()
        .dirpath()
    )
    pkdp("r={}", r)
    # Check to see if we are in our dev directory. This is a hack,
    # but should be reliable.
    if not r.join("setup.py").check():
        # Don't run from an install directory
        r = pkio.py_path(".")
    else:
        pkdp("HIT")
    pkdp("r={}", r)
    return pkio.mkdir_parent(r.join(_DEFAULT_ROOT))
