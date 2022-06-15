# -*- coding: utf-8 -*-
"""Functions for continuous integration

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp, pkdlog

def run():
    """fmt.diff on dir and then test

    Args:
        dir (object): string or py.path to file or directory
    """
    from pykern.pkcli import fmt, test
    from pykern import pkio

    fmt.diff(pkio.py_path())
    test.default_command()
