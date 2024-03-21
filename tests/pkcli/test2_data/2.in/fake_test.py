import pytest
import y
import sys
import asyncio
from pykern import pksubprocess
import warnings


def test_fake1():
    pksubprocess.check_call_with_signals(["python", "x.py"], output="o.txt")
    with open("o.txt", 'r') as file:
        sys.stderr.write(file.read())
