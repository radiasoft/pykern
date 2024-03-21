import asyncio


def y():
    async def coroutine():
        asyncio.sleep(0)
    coroutine()

try:
    asyncio.run(y())
except Exception as e:
    pass
