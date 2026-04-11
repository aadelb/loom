# Loom journey test — 2026-04-11T20:15:08+00:00
**Topic:** llama model family
**Server:** http://127.0.0.1:8787/mcp
**Duration:** 1s | **Steps:** 4 | **✅ OK:** 2 | **❌ Fail:** 3

## Step 0 — mcp.initialize ✅ 115ms
**Name:** initialize
**Params:** `{}`
**Result:** `{
  "server": "research-toolbox",
  "version": "1.27.0"
}...`

## Step 1 — mcp.tools/list ❌ 255ms
**Name:** list_tools
**Params:** `{}`
**Result:** `{
  "tool_count": 10,
  "tools": [
    "research_fetch",
    "research_spider",
    "research_markdown",
    "research_search",
    "research_deep",
    "research_github",
    "research_camoufox",
   ...`

## Step 4 — research_search ✅ 119ms
**Name:** discovery_search
**Params:** `{
  "query": "llama model family",
  "provider": "exa",
  "n": 10
}`
**Result:** `{
  "hit_count": 0
}...`

## Step 6 — research_cache_stats ✅ 118ms
**Name:** cache_stats
**Params:** `{}`
**Result:** `{
  "file_count": 28,
  "total_bytes": 196355,
  "days_present": [
    "2026-04-11"
  ]
}...`

## Cache Stats
- **file_count:** 28
- **total_bytes:** 196355
- **days_present:** ['2026-04-11']
