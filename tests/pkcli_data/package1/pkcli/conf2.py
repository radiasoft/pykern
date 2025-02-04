last_cmd = None


def cmd1(arg1):
    global last_cmd
    last_cmd = cmd1.__name__
    return


def _not_cmd1():
    pass
