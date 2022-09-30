import pytest
from pykern import pkunit

def test_no_files():

    for d in pkunit.case_dirs():
        print(f"dir: {d}")




