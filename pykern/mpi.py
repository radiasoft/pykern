# -*- coding: utf-8 -*-
u"""MPI support routines

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

def checked_call(op):
    """Abort MPI if op raises an exception.

    If ``op`` doesn't handle an exception, then MPI needs
    to abort. This will terminate the MPI process, not just the
    one task.

    If MPI is not running or mpi4py is not installed,
    then passes through the exception.

    Args:
        op (func): function to call
    """
    try:
        op()
    except BaseException as e:
        code = 86
        if isinstance(e, SystemExit) and hasattr(e, 'code'):
            if not e.code:
                raise
            code = e.code
        try:
            from mpi4py import MPI
            if MPI.COMM_WORLD and MPI.COMM_WORLD.Get_size() > 1:
                MPI.COMM_WORLD.Abort(code)
        except BaseException as e2:
            pass
        raise
