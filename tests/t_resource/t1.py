from __future__ import absolute_import, division, print_function, unicode_literals
from io import open
import pykern.resource

def somefile():
    with open(pykern.resource.filename('somefile')) as f:
        return f.read()
