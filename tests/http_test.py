"""test http server

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


@pytest.mark.asyncio
async def test_basic():
    from pykern import http_unit

    with http_unit.Setup(api_classes=(_class(),)) as c:
        from pykern.pkcollections import PKDict
        from pykern import pkunit

        e = PKDict(a=1)
        pkunit.pkeq(e, await c.call_api("echo", e))


def _class():
    from pykern import quest

    class _API(quest.API):

        async def api_echo(self, api_args):
            return api_args

    return _API
