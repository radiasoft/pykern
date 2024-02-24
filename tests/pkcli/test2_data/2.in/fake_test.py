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
        sys.stderr.write(file_contents)
    # for w in recwarn:
    #     print("\n\n\n w=", w)

# def test_fake2():
#     async def coroutine():
#         asyncio.sleep(0)
#     coroutine()
    # for w in recwarn:
    #     print("\n\n\n w=", w)