import pykern.resource

def somefile():
    with open(pykern.resource.filename('somefile')) as f:
        return f.read()
