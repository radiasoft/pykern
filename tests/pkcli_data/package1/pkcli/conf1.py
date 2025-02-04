last_cmd = None


def cmd1(arg1):
    """Subject line for cmd1

    Args:
        arg1
    """
    global last_cmd
    last_cmd = cmd1.__name__
    return


def cmd2():
    """Subject line for cmd2

    Args:
        -
    """
    global last_cmd
    last_cmd = cmd2.__name__
    return
