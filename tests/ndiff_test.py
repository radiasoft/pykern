from pykern import pkunit
from pykern import pkio

def test_basic():
    data_dir = pkunit.data_dir()
    e = data_dir.join("x_expect.ndiff")
    a = data_dir.join("x_actual.ndiff")
    print(a, e)
    pkunit.file_eq(expect_path=e, actual_path=a)
