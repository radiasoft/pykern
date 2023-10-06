# -*- coding: utf-8 -*-
u"""fails due to RuntimeWarning

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

def test_coroutine_never_awaited():
    import asyncio

    async def my_coroutine():
        asyncio.sleep(0)

    def trigger_warning():
        asyncio.run(my_coroutine())

    trigger_warning()