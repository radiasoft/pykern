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
TWO_PI = 2 * math.pi
RT_TWO_PI = math.sqrt(2*math.pi)
RT_2_OVER_PI = math.sqrt(2/math.pi)
pi = math.pi
RT_2 = math.sqrt(2.)
TWO_PI = 2 * math.pi
RT_TWO_PI = math.sqrt(2*math.pi)
RT_2_OVER_PI = math.sqrt(2/math.pi)
c = scipy.constants.c                  # speed of light [m/s]
c_SQ = scipy.constants.c**2
c_INV  = 1./scipy.constants.c
mu_0 = scipy.constants.mu_0            # permeability of free space
epsilon_0 = scipy.constants.epsilon_0  # permittivity of free space
m_p = scipy.constants.m_p              # proton mass [kg]
m_e = scipy.constants.m_e              # electron mass [kg]
e = scipy.constants.e                  # fundamental electric charge [C] (positive)
MKS_factor = 1./(4.*math.pi*scipy.constants.epsilon_0)
KG_to_EV = c_SQ / e          # convert mass [kg] to effective energy [eV]
EV_to_ERG = 1.602e-12        # convert energy from eV to erg
C_to_STATC = scipy.constants.c * 10.   # convert charge from coulombs to statcoulombs
e_CGS = scipy.constants.e * C_to_STATC
c_CGS = scipy.constants.c * 100
m_e_CGS = scipy.constants.m_e * 1000.
m_p_CGS = scipy.constants.m_p * 1000.
m_e_EV = scipy.constants.m_e * KG_to_EV
m_p_EV = scipy.constants.m_p * KG_to_EV
C_SQ = scipy.constants.c**2
C_INV  = 1./scipy.constants.c
MKS_FACTOR = 1./(4.*math.pi*scipy.constants.epsilon_0)
M_E_EV = scipy.constants.m_e * C_SQ / (-scipy.constants.e)
