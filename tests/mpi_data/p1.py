# -*- coding: utf-8 -*-
u"""test pykern.mpi

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pykern.mpi


def op():
    from mpi4py import MPI
    import time
    import sys

    x = sys.argv[1]
    print(x)
    if 'normal' in x:
        return
    if 'exit-1' == x:
        raise SystemExit(1)
    if 'divide-zero' == x:
        i = 1 / 0
    if 'exit-13-rank-0' == x:
        if MPI.COMM_WORLD and MPI.COMM_WORLD.Get_rank() == 0:
            raise SystemExit(13)
        time.sleep(1)
        return
    if 'divide-zero-rank-2' == x:
        if MPI.COMM_WORLD and MPI.COMM_WORLD.Get_rank() == 2:
            time.sleep(.2)
            i = 1 / 0
        time.sleep(1)
    else:
        raise ValueError('{}: invalid argv'.format(sys.argv))


pykern.mpi.checked_call(op)
