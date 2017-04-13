#

def all_modules():
    from pykern import pkconfig
    from pykern import pkinspect

    return pkconfig.all_modules_in_load_path(pkinspect.this_module())
