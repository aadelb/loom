import os
import re

files = [
    "src/loom/tools/breach_check.py",
    "src/loom/tools/creative.py",
    "src/loom/tools/dark_forum.py",
    "src/loom/tools/exploit_db.py",
    "src/loom/tools/fetch.py",
    "src/loom/tools/gamification.py",
    "src/loom/tools/identity_resolve.py",
    "src/loom/tools/infowar_tools.py",
    "src/loom/tools/domain_intel.py",
    "src/loom/tools/circuit_breaker.py"
]

for fpath in files:
    if not os.path.exists(fpath):
        print(f"MISSING FILE: {fpath}")
        continue
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Missing awaits
    # Any call to research_fetch, research_search, _call_with_cascade without await
    # We will look for "research_fetch(" or "research_search(" or "_call_with_cascade(" not preceded by await
    # Also find if they are used in run_in_executor
    for func in ["research_fetch", "research_search", "_call_with_cascade"]:
        matches = re.finditer(r'[^a-zA-Z0-9_]' + func + r'\s*\(', content)
        for m in matches:
            start = max(0, m.start() - 30)
            end = min(len(content), m.end() + 30)
            context = content[start:end]
            if "await" not in context and "def " not in context:
                print(f"{fpath} - MISSING AWAIT: {context.strip()}")
            if "run_in_executor" in context or "lambda" in context:
                 print(f"{fpath} - ASYNC IN EXECUTOR: {context.strip()}")

    # 2. content[0].text
    if "content[0].text" in content:
        print(f"{fpath} - LLMResponse content[0].text found")

    # 3. .set(
    # Specifically cache.set or similar
    if ".set(" in content:
        print(f"{fpath} - .set( found")

    # 4. validate_url missing try-except
    matches = re.finditer(r'validate_url\(', content)
    for m in matches:
        start = max(0, m.start() - 100)
        context = content[start:m.end()]
        if "try:" not in context:
            print(f"{fpath} - validate_url without try-except nearby")

    # 5. from mcp.types import TextContent without try/except
    matches = re.finditer(r'from mcp\.types import TextContent', content)
    for m in matches:
        start = max(0, m.start() - 50)
        context = content[start:m.end()]
        if "try:" not in context:
            print(f"{fpath} - TextContent import without try-except nearby")

print("DONE")
