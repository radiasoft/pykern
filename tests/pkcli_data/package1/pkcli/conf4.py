last_self = None
last_cmd = None
last_arg = None


def should_not_find():
    pass


class Commands:
    def __init__(self):
        global last_self

        last_self = self

    def default_command(self, arg1):
        global last_cmd, last_arg
        last_cmd = self.default_command.__name__
        last_arg = arg1

    def _should_not_find():
        pass
