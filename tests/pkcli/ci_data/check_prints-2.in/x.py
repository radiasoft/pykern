def foo():
    from pykern.pkdebug import pkdp
    #print('this should not set off check_prints')
    #   print('this should not be found either')
    #pkdp('neither should this')
    mention = (pkdp, print)
