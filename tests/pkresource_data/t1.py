from __future__ import absolute_import, division, print_function, unicode_literals
from io import open
from pykern import pkresource

def somefile():
    with open(pkresource.filename('somefile')) as f:
        return f.read()
