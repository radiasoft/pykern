import pytest
from pykern import pkunit
from pykern import pkio

def test_1():
    with pkunit.save_chdir_work():
        pkio.write_text('do_not_include_in_sdist.py', 'some text')
