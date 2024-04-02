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
