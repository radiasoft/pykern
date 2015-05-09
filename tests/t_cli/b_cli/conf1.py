last_cmd = None

def cmd1(arg1):
    global last_cmd
    last_cmd = cmd1
    return

def cmd2():
    global last_cmd
    last_cmd = cmd2
    return
