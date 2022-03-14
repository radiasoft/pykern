# -*- coding: utf-8 -*-
u"""Various constant values

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import math
import scipy.constants

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


#: Copied from numconv, which copied from RFC1924
BASE62_CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
pi = math.pi
TWO_PI = 2 * pi
RT_TWO_PI = math.sqrt(TWO_PI)
RT_2_OVER_PI = math.sqrt(2 / pi)
RT_2 = math.sqrt(2.)
C = scipy.constants.c
C_SQ = C ** 2
C_INV  = 1. / C
mu_0 = scipy.constants.mu_0
epsilon_0 = scipy.constants.epsilon_0
m_p = scipy.constants.m_p
m_e = scipy.constants.m_e
e = scipy.constants.e
MKS_factor = 1. / (4. * pi * epsilon_0)
KG_to_EV = C_SQ / e
EV_to_ERG = 1.602e-12
C_to_STATC = C * 10.
E_CGS = e * C_to_STATC
C_CGS = C * 100
m_e_CGS = m_e * 1000.
m_p_CGS = m_p * 1000.
m_e_EV = m_e * KG_to_EV
m_p_EV = m_p * KG_to_EV
M_E_EV = m_e * C_SQ / (-e)
