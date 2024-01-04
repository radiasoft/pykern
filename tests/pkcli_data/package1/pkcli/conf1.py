from __future__ import absolute_import, division, print_function

last_cmd = None

from pykern.pkdebug import pkdp

def cmd1(arg1):
    """Subject line for cmd1

    Args:
        arg1
    """
    global last_cmd
    last_cmd = cmd1
    return

def cmd2():
    """Subject line for cmd2

    Args:
        -
    """
    global last_cmd
    last_cmd = cmd2
    return
