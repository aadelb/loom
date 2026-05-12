"""Add Playwright browser scraping as middle fallback layer.
Order: 1. Local DB (instant) → 2. Browser scrape (if site works) → 3. LLM fallback
"""
import os

tools_dir = "/data/opt/research-toolbox/loom-legal/src/loom_legal/tools"

# Map tools to their gov site URLs that work with Playwright
BROWSER_SITES = {
    "dubai_law.py": ("dlp.dubai.gov.ae", "https://dlp.dubai.gov.ae/en/Pages/LegislationSearch.aspx"),
    "difc.py": ("difc.com", "https://www.difc.com/business/laws-and-regulations/legal-database"),
    "dubai_decree.py": ("dlp.dubai.gov.ae", "https://dlp.dubai.gov.ae/en/Pages/LegislationSearch.aspx"),
    "municipality.py": ("dlp.dubai.gov.ae", "https://dlp.dubai.gov.ae/en/Pages/LegislationSearch.aspx"),
}

BROWSER_SCRAPE_CODE = '''
    # LAYER 2: Browser scraping (real Chromium — works for {site})
    try:
        import asyncio
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        def _browser_search():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    url = "{url}?q=" + str(query) if "?" not in "{url}" else "{url}&search=" + str(query)
                    resp = page.goto(url, timeout=12000, wait_until="domcontentloaded")
                    if resp and resp.status == 200:
                        html = page.content()
                        browser.close()
                        soup = BeautifulSoup(html, "html.parser")
                        items = []
                        for el in soup.select("tr, .law-item, .search-result, article, .result-item")[:10]:
                            text = el.get_text(strip=True)[:300]
                            if text and len(text) > 20:
                                items.append({{"title_en": text[:100], "content": text, "source": "{site}"}})
                        return items
                    browser.close()
            except Exception:
                pass
            return []
        browser_results = await asyncio.to_thread(_browser_search)
        if browser_results:
            return {{
                "query": query,
                "total_count": len(browser_results),
                "results": browser_results,
                "source": "{site} (browser)",
                "cached": False,
                "elapsed_ms": 0,
            }}
    except Exception:
        pass
    # Continue to LLM fallback below
'''

fixed = 0
for fname, (site, url) in BROWSER_SITES.items():
    fpath = os.path.join(tools_dir, fname)
    if not os.path.exists(fpath):
        continue

    content = open(fpath).read()

    if "playwright" in content or "browser_search" in content:
        print(f"  SKIP {fname} (already has browser)")
        continue

    # Find where DB-first code ends (after "# Fallback" or "# Continue" comment)
    # Insert browser layer between DB and LLM fallback
    markers = ["# Fallback to", "# If DB returned", "# Continue to", "# PRIMARY SOURCE"]
    insert_after = None

    # Find the end of DB-first block (the "pass" after except Exception)
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "# If DB returned nothing" in line or "# Fallback to" in line or ("pass" in line and i > 0 and "except" in lines[i-1] and "_search_uae_law_db" in "\n".join(lines[max(0,i-10):i])):
            insert_after = i + 1
            break

    if insert_after is None:
        # Try after the DB except block
        for i, line in enumerate(lines):
            if "except Exception:" in line and i > 5:
                next_line = lines[i+1].strip() if i+1 < len(lines) else ""
                if next_line == "pass":
                    insert_after = i + 2
                    break

    if insert_after is None:
        print(f"  SKIP {fname} (no insertion point found)")
        continue

    indent = "    "  # standard function indent
    browser_code = BROWSER_SCRAPE_CODE.format(site=site, url=url)

    # Insert browser scraping code
    browser_lines = browser_code.split("\n")
    for j, bl in enumerate(browser_lines):
        lines.insert(insert_after + j, bl)

    content = "\n".join(lines)
    open(fpath, "w").write(content)
    fixed += 1
    print(f"  FIXED {fname} — added Playwright browser layer for {site}")

print(f"\nTotal: {fixed} tools now have browser scraping layer")
