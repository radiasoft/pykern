"""Force a coroutine never awaited warning

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_coroutine_never_awaited():
    from pykern import pkdebug
    import asyncio

    async def coroutine():
        asyncio.sleep(0)

    pkdebug.pkdlog("expect 'RuntimeWarning: coroutine 'sleep' was never awaited'")
    asyncio.run(coroutine())
