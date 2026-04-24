import re
import glob

config_fields = [
    "SPIDER_CONCURRENCY",
    "EXTERNAL_TIMEOUT_SECS",
    "MAX_CHARS_HARD_CAP",
    "MAX_SPIDER_URLS",
    "CACHE_TTL_DAYS",
    "DEFAULT_SEARCH_PROVIDER",
    "DEFAULT_ACCEPT_LANGUAGE",
    "LOG_LEVEL",
    "LLM_DEFAULT_CHAT_MODEL",
    "LLM_DEFAULT_EMBED_MODEL",
    "LLM_DEFAULT_TRANSLATE_MODEL",
    "LLM_MAX_PARALLEL",
    "LLM_DAILY_COST_CAP_USD",
    "LLM_CASCADE_ORDER",
    "RESEARCH_SEARCH_PROVIDERS",
    "RESEARCH_EXPAND_QUERIES",
    "RESEARCH_EXTRACT",
    "RESEARCH_SYNTHESIZE",
    "RESEARCH_GITHUB_ENRICHMENT",
    "RESEARCH_MAX_COST_USD",
    "FETCH_AUTO_ESCALATE",
]

files = glob.glob("src/loom/**/*.py", recursive=True)
used = {f: False for f in config_fields}

for f in files:
    content = open(f).read()
    if f.endswith("config.py"): continue # Skip definition file
    
    for field in config_fields:
        if field in content:
            used[field] = True

for field, is_used in used.items():
    if not is_used:
        print(f"Config field {field} is NEVER read by any code outside config.py!")
