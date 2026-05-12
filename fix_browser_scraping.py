"""Wire Playwright browser scraping into source clients for gov sites that work."""
import os

# Update source_client.py to add a browser fetch method
SOURCE_CLIENT = "/data/opt/research-toolbox/loom-legal/src/loom_legal/source_client.py"
content = open(SOURCE_CLIENT).read()

if "playwright" not in content:
    # Add browser fetch method
    browser_method = '''

    async def _fetch_with_browser(self, url: str, wait_selector: str = "body", timeout: int = 15000) -> str:
        """Fetch page content using real Chromium browser (bypasses bot detection)."""
        import asyncio
        def _sync_fetch():
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    resp = page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                    if resp and resp.status == 200:
                        content = page.content()
                    else:
                        content = ""
                    browser.close()
                    return content
            except Exception:
                return ""
        return await asyncio.to_thread(_sync_fetch)
'''
    # Insert before the last method or at end of class
    class_end = content.rfind("\n\n")
    if class_end > 0:
        content = content[:class_end] + browser_method + content[class_end:]
        open(SOURCE_CLIENT, "w").write(content)
        print("Added _fetch_with_browser to source_client.py")
    else:
        print("Could not find insertion point in source_client.py")

# Update dubai_legal_portal.py to use Playwright
DUBAI_PORTAL = "/data/opt/research-toolbox/loom-legal/src/loom_legal/sources/dubai_legal_portal.py"
if os.path.exists(DUBAI_PORTAL):
    dp = open(DUBAI_PORTAL).read()
    if "playwright" not in dp and "_fetch_with_browser" not in dp:
        # Add browser fallback to the search method
        if "async def search" in dp:
            dp = dp.replace(
                "async def search(",
                "async def search_browser(self, query: str) -> list:\n"
                "        \"\"\"Search using real browser (bypasses 403).\"\"\"\n"
                "        from bs4 import BeautifulSoup\n"
                "        url = f'https://dlp.dubai.gov.ae/en/Pages/LegislationSearch.aspx?q={query}'\n"
                "        html = await self._fetch_with_browser(url)\n"
                "        if not html:\n"
                "            return []\n"
                "        soup = BeautifulSoup(html, 'html.parser')\n"
                "        results = []\n"
                "        for item in soup.select('.search-result-item, .law-item, tr')[:20]:\n"
                "            title = item.get_text(strip=True)[:200]\n"
                "            if title:\n"
                "                results.append({'title': title, 'source': 'dlp.dubai.gov.ae'})\n"
                "        return results\n\n"
                "    async def search(",
            )
            open(DUBAI_PORTAL, "w").write(dp)
            print("Added browser search to dubai_legal_portal.py")

# Update DIFC client to use Playwright
DIFC = "/data/opt/research-toolbox/loom-legal/src/loom_legal/sources/difc.py"
if os.path.exists(DIFC):
    dc = open(DIFC).read()
    if "playwright" not in dc and "_fetch_with_browser" not in dc:
        if "async def search" in dc:
            dc = dc.replace(
                "async def search(",
                "async def search_browser(self, query: str) -> list:\n"
                "        \"\"\"Search DIFC legal DB using real browser.\"\"\"\n"
                "        from bs4 import BeautifulSoup\n"
                "        url = f'https://www.difc.com/business/laws-and-regulations/legal-database?search={query}'\n"
                "        html = await self._fetch_with_browser(url)\n"
                "        if not html:\n"
                "            return []\n"
                "        soup = BeautifulSoup(html, 'html.parser')\n"
                "        results = []\n"
                "        for item in soup.select('.law-item, .regulation-item, .search-result, article')[:20]:\n"
                "            title = item.get_text(strip=True)[:200]\n"
                "            if title:\n"
                "                results.append({'title': title, 'source': 'difc.com'})\n"
                "        return results\n\n"
                "    async def search(",
            )
            open(DIFC, "w").write(dc)
            print("Added browser search to difc.py")

print("\nDone. Restart service to apply.")
