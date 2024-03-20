"""pykern package

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("pykern")
except importlib.metadata.PackageNotFoundError:
    # We only have a version once the package is installed.
    pass
