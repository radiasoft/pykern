# -*- coding: utf-8 -*-
u"""Where external resources are stored

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import errno
import inspect
import os.path
import pkg_resources
import re

#: The subdirectory in the top-level Python where to put resources
PACKAGE_DATA = 'package_data'

def filename(relative_filename):
    """Return the filename to the resource

    Args:
        relative_filename (str): file name relative to package_data directory.

    Returns:
        str: absolute path of the resource file
    """
    pkg = _root_package()
    fn = os.path.join(PACKAGE_DATA, relative_filename)
    res = pkg_resources.resource_filename(pkg, fn)
    if not os.path.exists(res):
        raise IOError((errno.ENOENT, 'resource does not exist', res))
    return res


def _root_package():
    """Return the package from two callers back"""
    frame = None
    try:
        frame = inspect.currentframe().f_back.f_back
        module = inspect.getmodule(frame)
    finally:
        if frame:
            del frame
    return re.match(r'^\w+', module.__name__).group(0)
