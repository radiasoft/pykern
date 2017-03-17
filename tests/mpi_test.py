# -*- coding: utf-8 -*-
u"""

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

pytest.importorskip('mpi4py')


def test_checked_call():
    from pykern import pkunit
    from pykern.pkunit import pkeq
    import sys
    import subprocess

    with pkunit.save_chdir_work():
        cmd = [sys.executable, str(pkunit.data_dir().join('p1.py'))]
        for i, a in enumerate((
            ('normal', 0),
            ('exit-1', 1),
            ('divide-zero', 1),
            ('normal-rank-all', 0),
            ('divide-zero-rank-2', 86),
            ('exit-13-rank-0', 13),
        )):
            f = '{}.out'.format(i)
            with open(f, 'w') as o:
                c = cmd + [a[0]]
                print(a[0])
                if 'rank' in a[0]:
                    c = ['mpiexec', '-n', '4'] + c
                actual = subprocess.call(
                    c,
                    stdout=o,
                    stderr=subprocess.STDOUT,
                )
            pkeq(a[1], actual, '{}: exit({})\n{}', ' '.join(c), actual, open(f).read())
