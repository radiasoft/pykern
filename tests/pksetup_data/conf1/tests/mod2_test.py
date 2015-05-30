import pytest

def test_1():
    import conf1.pkg1.mod2
    assert conf1.pkg1.mod2.var2 == 222
