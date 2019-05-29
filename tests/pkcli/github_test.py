# -*- coding: utf-8 -*-
u"""test github

:copyright: Copyright (c) 2019 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import os

@pytest.mark.skipif(bool(os.environ.get('TRAVIS')), reason='travis uses shared IPs so gets rate limited too easily')
def test_backup():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing({
        'PYKERN_PKCLI_GITHUB_TEST_MODE': '1',
        'PYKERN_PKCLI_GITHUB_API_PAUSE_SECONDS': '0',
    })
    from pykern.pkcli import github
    from pykern import pkunit
    from pykern import pkio

    with pkunit.save_chdir_work():
        github.backup()
        github.backup()
