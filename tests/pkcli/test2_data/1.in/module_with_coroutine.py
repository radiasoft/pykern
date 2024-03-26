import asyncio


def method_with_coroutine():
    async def coroutine():
        asyncio.sleep(0)
    coroutine()

try:
    asyncio.run(method_with_coroutine())
except Exception as e:
    pass
