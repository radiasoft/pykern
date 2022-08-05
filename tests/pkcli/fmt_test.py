# -*- coding: utf-8 -*-
"""test fmt

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import pytest


def test_check():
    from pykern.pkcli import fmt

    _cases_with_prefix_except("check", fmt.check)


def test_diff():
    from pykern.pkcli import fmt

    _cases_with_prefix_except("diff", fmt.diff)


def test_run():
    from pykern import pkunit
    from pykern.pkcli import fmt

    for d in pkunit.case_dirs("fmt_dir"):
        fmt.run(d)


def _cases_with_prefix_except(prefix, fn):
    from pykern import pkunit
    from pykern import pkio

    for d in pkunit.case_dirs(prefix):
        with pkunit.ExceptToFile():
            fn(d)
