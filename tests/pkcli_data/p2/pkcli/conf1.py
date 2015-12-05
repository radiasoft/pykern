from __future__ import absolute_import, division, print_function

last_cmd = None

from pykern.pkdebug import pkdp

def cmd1(arg1):
    global last_cmd
    last_cmd = cmd1
    return

def cmd2():
    global last_cmd
    last_cmd = cmd2
    return
