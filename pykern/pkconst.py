"""Various constant values

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import py.path
import re


#: DEPRECATED use `str`
STRING_TYPES = str

#: Class of `pkio.py_path` and `py.path.local`
PY_PATH_LOCAL_TYPE = type(py.path.local())

#: Copied from numconv, which copied from RFC1924
BASE62_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

#: IP address for local servers
LOCALHOST_IP = "127.0.0.1"

#: The subdirectory in the top-level Python where to put resources
PACKAGE_DATA = "package_data"

#: Use this (sparingly, pkdlog is prefered) when you want to use print directly.
builtin_print = print
