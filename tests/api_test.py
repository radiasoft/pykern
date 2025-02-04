"""test http server

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


@pytest.mark.asyncio
async def test_basic():
    from pykern.api import unit_util

    async with unit_util.Setup(api_classes=(_class(),)) as c:
        from pykern.pkcollections import PKDict
        from pykern import pkunit, pkdebug

        e = PKDict(ping="pong")
        pkunit.pkeq(e.pkupdate(counter=1), await c.call_api("echo", e))
        pkunit.pkeq(e.pkupdate(counter=2), await c.call_api("echo", e))


@pytest.mark.asyncio
async def test_subscribe():
    from pykern.api import unit_util

    async def _client_unsub(iter_count, sub):
        sub.unsubscribe()
        with pkunit.pkexcept(util.APIDisconnected):
            pkunit.pkeq(None, await sub.result_get())
        sub.unsubscribe()

    async def _no_values(iter_count, sub):
        pkunit.pkeq(None, await sub.result_get())
        sub.unsubscribe()

    async def _server_unsub(iter_count, sub):
        for i in range(iter_count):
            pkunit.pkeq(PKDict(count=i), await sub.result_get())
        pkunit.pkeq(None, await sub.result_get())
        with pkunit.pkexcept(util.APIDisconnected):
            pkunit.pkeq(None, await sub.result_get())

    async with unit_util.Setup(api_classes=(_class(),)) as c:
        from pykern.pkcollections import PKDict
        from pykern import pkunit
        from pykern.api import util
        import asyncio

        for n, o in (
            (3, _server_unsub),
            (1, _client_unsub),
            (0, _no_values),
        ):
            with await c.subscribe_api("sub1", PKDict(iter_count=n)) as s:
                await o(n, s)


def _class():
    from pykern.api import util
    from pykern.pkcollections import PKDict
    from pykern import quest
    import asyncio

    class _API(quest.API):

        async def api_echo(self, api_args):
            self.session.pksetdefault(counter=0).counter += 1
            return api_args.pkupdate(counter=self.session.counter)

        @util.subscription
        async def api_sub1(self, api_args):
            await asyncio.sleep(0.1)
            for i in range(api_args.iter_count):
                await asyncio.sleep(0.2)
                if self.is_quest_end():
                    break
                self.subscription.result_put(PKDict(count=i))
            return None

    return _API
