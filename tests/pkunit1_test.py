# -*- coding: utf-8 -*-
"""conforming case_dirs

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_case_dirs():
    from pykern import pkunit

    for d in pkunit.case_dirs():
        with pkunit.ExceptToFile():
            i = d.join("in.txt").read()
            pkunit.pkeq(d.basename + "\n", i)
            d.join("out.txt").write(i)
