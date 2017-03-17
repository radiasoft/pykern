# -*- coding: utf-8 -*-
u"""MPI support routines

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

def checked_call(op):
    try:
        op()
    except BaseException as e:
        if isinstance(e, SystemExit):
            if hasattr(e, 'code') and not e.code:
                raise
        try:
            from mpi4py import MPI
            if False and MPI.COMM_WORLD:
                MPI.COMM_WORLD.Abort(1)
        except BaseException as e2:
            pass
        raise
