""":mod:`xyzzy1` package

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import importlib.metadata

try:
    # We only have a version once the package is installed.
    __version__ = importlib.metadata.version("xyzzy1")
except importlib.metadata.PackageNotFoundError:
    pass
