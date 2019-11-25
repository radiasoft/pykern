# -*- coding: utf-8 -*-
u"""Various constant values

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

# pykern uses pksetup in setup.py so requirements.txt is not yet evaluated so can't use six
# or any other external dependencies. The "types" modules in Python 2 had a StringTypes, which
# would have been great if it hadn't been removed and changed completely in Python 3.

#: Python version independent value of string instance check
STRING_TYPES = None
try:
    STRING_TYPES = basestring
except NameError:
    STRING_TYPES = str


try:
    # May not be here, but that's ok, only for modules that
    # aren't in the critical import path (see comment above)
    import py.path

    #: Class of `pkio.py_path` and `py.path.local`
    PY_PATH_LOCAL_TYPE = type(py.path.local())
except Exception:
    pass
