# -*- coding: utf-8 -*-
""":mod:`private` package

:copyright: Copyright (c) 2024 James Bond.  All Rights Reserved.
:license: PROPRIETARY AND CONFIDENTIAL. See LICENSE file for details.
"""
import pkg_resources

try:
    # We only have a version once the package is installed.
    __version__ = pkg_resources.get_distribution("private").version
except pkg_resources.DistributionNotFound:
    pass
