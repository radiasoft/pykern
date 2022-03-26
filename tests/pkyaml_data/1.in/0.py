from pykern.pkcollections import PKDict

def four(self):
    return 4

def three(self, one):
    return PKDict(one=one, four=self.four())
