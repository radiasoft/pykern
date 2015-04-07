# -*- coding: utf-8 -*-
"""Handle system startup.

Installs a system process

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""

import os
import sys


#: Which user invoked the boot GUI.
_UID_ARG = 'original_uid:'

def gui(*args):
    """Called from the gui app. May install if not already installed.

    May be passed any number of arguments. We don't really know.
    """
    if pybivio.platform.is_darwin():
        return _gui_darwin(args)
    raise NotImplementedError('unsupported platform')


def _gui_darwin(args):
    """
    """
    uid = os.getuid()
    if uid != 0:
        return _darwin_escalate_privileges(uid)
    os.system("""osascript -e 'display alert "Installing..."'""")


def _darwin_escalate_privileges(uid):
    """Escalate privileges to administrator with Apple Script.

    Args:
        uid (int): original user's id
    """
    cmd = """osascript -e 'do shell script "{} {}{}" with administrator privileges'"""
    os.system(cmd.format(sys.argv[0], _UID_ARG, uid))
