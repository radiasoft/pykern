# -*- coding: utf-8 -*-
u"""Where external resources are stored

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

# Root module: Import only builtin packages so avoid dependency issues
import errno
import inspect
import os.path
import pkg_resources
import re

from pykern import pkinspect
from pykern import pksetup


def filename(relative_filename, caller_context=None):
    """Return the filename to the resource

    Args:
        relative_filename (str): file name relative to package_data directory.
        caller_context (object): Any object from which to get the `root_package`

    Returns:
        str: absolute path of the resource file
    """
    pkg = pkinspect.root_package(
        caller_context if caller_context else pkinspect.caller_module())
    fn = os.path.join(pksetup.PACKAGE_DATA, relative_filename)
    res = pkg_resources.resource_filename(pkg, fn)
    if not os.path.exists(res):
        raise IOError((errno.ENOENT, 'resource does not exist', res))
    return res
