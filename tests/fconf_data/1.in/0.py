from pykern.pkcollections import PKDict

def add_score(self, num):
    return self.fconf_var('score') + num

def four(self):
    return 4


def mymap(self, func, *args):
    res = []
    for a in args:
        res.extend(map(func, a))
    return res


def three(self, one):
    return PKDict(one=one, four=self.four())
