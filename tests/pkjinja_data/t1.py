from __future__ import absolute_import, division, print_function
from pykern import pkresource

from pykern import pkjinja

def render(out):
    v = {'k1': 'v1'}
    return pkjinja.render_resource('t1', v, out)
