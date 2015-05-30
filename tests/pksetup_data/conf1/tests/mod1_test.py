import pytest

def test_1():
    import conf1.mod1
    assert conf1.mod1.var1 == 123
