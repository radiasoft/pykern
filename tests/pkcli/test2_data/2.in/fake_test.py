import pytest
import y
import sys
import asyncio
from pykern import pksubprocess
import warnings


def test_fake1():
    pksubprocess.check_call_with_signals(["python", "x.py"], output="o.txt")
    with open("o.txt", 'r') as file:
        file_contents = file.read()
        # file_contents = "\n\n========= warnings summary =========== \n\n\n" + file_contents
        # file_contents = "\n\n\n FILE CONTENTS \n\n\n" + file_contents + "\n\n\n FILE CONTENTS \n\n\n"
        sys.stderr.write(file_contents)
