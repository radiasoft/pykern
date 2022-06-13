from pykern.pkcollections import PKDict
x=PKDict(foo='foo', bar='bar', a='a', b='b', c='c', d='d', e='e', f='f', param1='foo', param2='bar', foobar='foobar', barfoo='barfoo')
y='''
asdfasdfasdfasdf
'''
class foo:
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c=f'{c}'
    def get_c(self):
        return self.c




g=foo(x, y, 3)
