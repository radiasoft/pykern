def checking_prints_at_function_level():
    from pykern.pkdebug import pkdp

    pkdp("this pkdp should be found")
    print("this print should be found")
    "#" + print("should be found")
    int(pkdp(1))
