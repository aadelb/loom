import re
import glob

deps = [
    "mcp", "fastapi", "uvicorn", "pydantic", "pydantic_settings",
    "httpx", "orjson", "typer", "rich", "scrapling", "crawl4ai",
    "firecrawl", "exa_py", "tavily", "openai", "dotenv", "ddgs",
    "trafilatura", "langdetect"
]

files = glob.glob("src/loom/**/*.py", recursive=True)

found = {d: False for d in deps}

for f in files:
    content = open(f).read()
    for d in deps:
        if re.search(r'\b' + d + r'\b', content):
            found[d] = True

for d, ok in found.items():
    if not ok:
        print(f"Dependency {d} NOT FOUND in any src/loom/*.py file")
