import pytest

def test_1():
    import pksetupunit1.mod1
    assert pksetupunit1.mod1.var1 == 123
