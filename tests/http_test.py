"""test http server

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


@pytest.mark.asyncio
async def test_basic():
    from pykern import http_unit

    async with http_unit.Setup(api_classes=(_class(),)) as c:
        from pykern.pkcollections import PKDict
        from pykern import pkunit

        e = PKDict(ping="pong")
        pkunit.pkeq(e.pkupdate(counter=1), await c.call_api("echo", e))
        pkunit.pkeq(e.pkupdate(counter=2), await c.call_api("echo", e))


@pytest.mark.asyncio
async def test_subscribe():
    from pykern import http_unit

    async with http_unit.Setup(api_classes=(_class(),)) as c:
        from pykern.pkcollections import PKDict
        from pykern import pkunit

        e = PKDict(count=33)
        s = await c.subscribe_api("sub1", e)
        pkunit.pkeq(e, await s.reply_get())


def _class():
    from pykern import quest
    from pykern.pkcollections import PKDict
    import asyncio

    class _API(quest.API):

        async def api_echo(self, api_args):
            self.session.pksetdefault(counter=0).counter += 1
            return api_args.pkupdate(counter=self.session.counter)

        @quest.subscription_api
        async def api_sub1(self, api_args):
            for i in range(api_args.count):
                asyncio.sleep(0.1)
                await self.subscription.reply(PKDict(count=i))
                if self.is_destroyed():
                    break

    return _API
