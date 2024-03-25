import sys
from pykern import pksubprocess


def test_subprocess():
    pksubprocess.check_call_with_signals(["python", "x.py"], output="o.txt")
    with open("o.txt", 'r') as file:
        sys.stderr.write(file.read())
