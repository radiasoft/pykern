def foo():
    from pykern.pkdebug import pkdp
    #print('this should not set off check_prints')
    #pkdp('neither should this')
    mention = (pkdp, print)
