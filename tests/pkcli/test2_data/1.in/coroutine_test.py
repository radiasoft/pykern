# -*- coding: utf-8 -*-
"""Force a coroutine never awaited warning

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_coroutine_never_awaited():
    import asyncio

    async def coroutine():
        asyncio.sleep(0)

    asyncio.run(coroutine())


def test_subprocess():
    import sys
    from pykern import pksubprocess

    pksubprocess.check_call_with_signals(["python", "module_with_coroutine.py"], output="o.txt")
    with open("o.txt", 'r') as file:
        sys.stderr.write(file.read())
