from __future__ import absolute_import, division, print_function
from pykern import pkresource

def somefile():
    with open(pkresource.filename('somefile')) as f:
        return f.read()
