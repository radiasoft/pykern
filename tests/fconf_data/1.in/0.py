from pykern.pkcollections import PKDict

def four(self):
    return 4

def three(self, one):
    return PKDict(one=one, four=self.four())

def mymap(self, func, *args):
    res = []
    for a in args:
        res.extend(map(func, a))
    return res
