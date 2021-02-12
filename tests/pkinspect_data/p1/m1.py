class C():
    pass

v = 1
c = C()

from pykern import pkinspect


def caller(ignore_modules=None):
    return pkinspect.caller(ignore_modules=ignore_modules)


def caller_module(exclude_first=True):
    return pkinspect.caller_module(exclude_first=exclude_first)


def is_caller_main():
    return pkinspect.is_caller_main()
