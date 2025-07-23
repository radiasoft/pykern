""":mod:`private` package

:copyright: Copyright (c) 2024 James Bond.  All Rights Reserved.
:license: PROPRIETARY AND CONFIDENTIAL. See LICENSE file for details.
"""
import importlib.metadata

try:
    # We only have a version once the package is installed.
    __version__ = importlib.metadata.version("private")
except importlib.metadata.PackageNotFoundError:
    pass
