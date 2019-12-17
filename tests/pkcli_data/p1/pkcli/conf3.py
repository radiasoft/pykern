from __future__ import absolute_import, division, print_function

last_cmd = None

last_arg = None

def default_command(arg1):
    global last_cmd, last_arg
    last_cmd = default_command
    last_arg = arg1
    return
