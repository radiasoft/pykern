from __future__ import absolute_import, division, print_function

last_cmd = None

def cmd1(arg1):
    global last_cmd
    last_cmd = cmd1
    return


def _not_cmd1():
    pass
