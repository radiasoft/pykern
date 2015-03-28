# -*- coding: utf-8 -*-
"""Handle system startup.

Installs a system process

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""

import sys

def gui(*args):
    """Called from the gui app.

    May be passed any number of arguments. We don't really know.
    """
    # Determine system type and escalate privileges base on type,
    # re-executing the program. Care in parsing arguments. Only want
    # arguments that make sense.
    if sys.platform.startswith('darwin'):
        return _gui_darwin(*args)
    else:
        raise unsupported platform
    pass
