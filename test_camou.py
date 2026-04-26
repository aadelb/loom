import asyncio

async def test():
    from camoufox.async_api import AsyncNewBrowser
    from playwright.async_api import async_playwright
    p = await async_playwright().start()
    browser = await AsyncNewBrowser(p)
    print(type(browser))

asyncio.run(test())
