# Loom MCP Research Server — Help & Quick Start

Loom is a comprehensive research orchestration system with 23+ tools, intelligent provider cascading, and a 12-stage deep research pipeline. This guide covers installation, common workflows, and troubleshooting.

## Quick Start

### Installation

```bash
# Clone and install with dev dependencies
git clone https://github.com/yourusername/loom
cd loom
pip install -e ".[dev]"

# Or with optional browser tools
pip install -e ".[dev,browsers]"
```

### Configuration

Create `~/.loom/config.json` or set environment variables:

```json
{
  "DEFAULT_SEARCH_PROVIDER": "exa",
  "SPIDER_CONCURRENCY": 5,
  "EXTERNAL_TIMEOUT_SECS": 30,
  "CACHE_TTL_DAYS": 30,
  "LLM_CASCADE_ORDER": ["nvidia", "openai", "anthropic", "vllm"],
  "LLM_DAILY_COST_CAP_USD": 10.0,
  "RESEARCH_MAX_COST_USD": 0.50,
  "RESEARCH_EXPAND_QUERIES": true,
  "RESEARCH_EXTRACT": true,
  "RESEARCH_SYNTHESIZE": true,
  "RESEARCH_GITHUB_ENRICHMENT": true
}
```

**API Keys (via environment):**
```bash
export EXA_API_KEY="..."
export TAVILY_API_KEY="..."
export FIRECRAWL_API_KEY="..."
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

### Start the Server

```bash
# Development (auto-reload)
loom-server

# Or from source
python -m loom.server

# Verify on localhost:8787
curl http://127.0.0.1:8787/mcp/status
```

## Tool Categories & Examples

### Core Search & Fetch (Foundation Tools)

**research_search** — Multi-provider web search:
```python
# Single provider
research_search(
    query="latest transformer architectures 2026",
    provider="exa",
    n=10
)

# Auto-route by query type
research_search(
    query="PyTorch implementation paper",
    provider=None  # auto-detects code/academic
)
```

**research_fetch** — Single URL retrieval with mode selection:
```python
# HTTP mode (fast, open pages)
research_fetch(
    url="https://example.com",
    mode="http",
    max_chars=50000
)

# Stealthy mode (anti-bot, rotating proxies)
research_fetch(
    url="https://protected-site.com",
    mode="stealthy"
)

# Dynamic mode (real browser, JavaScript)
research_fetch(
    url="https://spa-app.com",
    mode="dynamic",
    screenshot=True
)
```

**research_spider** — Parallel bulk fetching:
```python
# Fetch 10 URLs concurrently, auto-escalate on failure
research_spider(
    urls=[
        "https://site1.com",
        "https://site2.com",
        "https://site3.com"
    ],
    mode="stealthy",
    concurrency=5,
    max_chars_each=10000
)
```

**research_markdown** — LLM-ready markdown extraction:
```python
# Extract clean markdown for LLM consumption
research_markdown(
    url="https://example.com",
    css_selector=".main-content",  # optional subtree
    remove_selectors=["nav", ".sidebar"],
    screenshot=False
)
```

### Deep Research (Full Pipeline)

**research_deep** — 12-stage orchestrated research:
```python
# Comprehensive research with all stages
result = research_deep(
    query="Machine Learning for healthcare 2026",
    depth=2,
    expand_queries=True,              # Stage 1: expand query variants
    extract=True,                     # Stage 5: LLM extract
    synthesize=True,                  # Stage 12: synthesize answer
    include_github=True,              # Stage 7: GitHub enrichment
    include_community=False,          # Stage 9: HN + Reddit sentiment
    include_red_team=False,           # Stage 10: challenge claims
    include_misinfo_check=False,      # Stage 11: fact check
    max_cost_usd=0.50,
    search_providers=["exa", "arxiv"]
)

# Returns: {
#     "answer": "...",
#     "sources": [...],
#     "citations": [...],
#     "metadata": {
#         "stages_completed": [1, 2, 3, 4, 5, 6, 7, 12],
#         "total_urls_fetched": 25,
#         "cost_usd": 0.32
#     }
# }
```

### GitHub & Code Search

**research_github** — Search GitHub repos and code:
```python
# Find repositories
research_github(
    query="pytorch attention implementation",
    type="repositories",
    language="python",
    sort="stars",
    n=10
)

# Find code files
research_github(
    query="transformer attention mask",
    type="code",
    language="python"
)
```

**research_github_readme** — Extract README for context:
```python
research_github_readme(
    repo="torch/pytorch"
)

# Returns: {
#     "repo": "torch/pytorch",
#     "readme": "# PyTorch\n...",
#     "stars": 78000,
#     "language": "C++"
# }
```

### LLM & Enrichment Tools

**research_llm_summarize** — Summarize long text:
```python
research_llm_summarize(
    text="...(long document)...",
    style="bullet_points",
    max_length=500
)
```

**research_llm_extract** — Extract structured data:
```python
research_llm_extract(
    text="...",
    schema={
        "author": "str",
        "date": "str",
        "key_claims": ["str"]
    }
)
```

**research_llm_translate** — Translate text:
```python
research_llm_translate(
    text="Bonjour le monde",
    target_language="en"
)
```

**research_llm_embed** — Semantic embeddings:
```python
research_llm_embed(
    text="machine learning is cool",
    model="nvidia/nv-embed-v2"
)
# Returns: 768-dim vector
```

**research_find_experts** — Discover thought leaders:
```python
research_find_experts(
    topic="AI Safety",
    n=5
)
# Returns: [{name, affiliation, twitter, email, relevance_score}, ...]
```

### Advanced Analysis Tools

**research_red_team** — Adversarial claim testing:
```python
research_red_team(
    text="AI will achieve AGI by 2030",
    perspective="skeptical",
    depth="deep"
)
# Returns: {
#     "weaknesses": [...],
#     "counterarguments": [...],
#     "confidence": 0.85
# }
```

**research_misinfo_check** — Fact-checking:
```python
research_misinfo_check(
    claims=[
        "The Earth is flat",
        "COVID vaccines cause autism"
    ]
)
# Returns: [{claim, verdict, confidence, evidence}, ...]
```

**research_community_sentiment** — HN + Reddit analysis:
```python
research_community_sentiment(
    topic="OpenAI's latest model",
    include_comments=True
)
# Returns: {
#     "overall_sentiment": 0.72,
#     "posts": [...],
#     "trending_claims": [...]
# }
```

### Stealth & Browser Tools

**research_camoufox** — Real browser with anti-detection:
```python
research_camoufox(
    url="https://site-with-bot-detection.com",
    wait_for=".results",  # CSS selector to wait for
    js_before_scrape="window.scrollTo(0, document.body.scrollHeight)",
    screenshot=True
)
```

**research_botasaurus** — Specialized stealth scraper:
```python
research_botasaurus(
    url="https://protected-site.com",
    solve_cloudflare=True
)
```

### Session Management

**research_session_open** — Create persistent browser context:
```python
research_session_open(
    name="authenticated_session",
    browser="camoufox",
    login_url="https://example.com/login",
    login_script="document.getElementById('username').value='user'; ...",
    ttl_seconds=3600
)
```

**research_session_list** — List active sessions:
```python
sessions = research_session_list()
# Returns: {sessions: [...], count: 3}
```

**research_session_close** — Clean up:
```python
research_session_close(name="authenticated_session")
```

### Cache Management

**research_cache_stats** — Diagnostics:
```python
research_cache_stats()
# Returns: {
#     "file_count": 1245,
#     "total_bytes": 125000000,
#     "days_present": ["2026-04-20", "2026-04-21", ...]
# }
```

**research_cache_clear** — TTL cleanup:
```python
# Remove entries older than 30 days
research_cache_clear(days=30)
# Returns: {removed_count: 342}
```

## Common Research Workflows

### Workflow 1: Quick Fact Check
```
research_search(query, provider="tavily", n=5)
→ research_spider(top_5_urls, mode="http")
→ research_llm_extract(results, schema={key_facts})
→ Done in <10 seconds, <$0.05
```

### Workflow 2: In-Depth Research Report
```
research_deep(query, depth=2)
  ├─ Stage 1: Query expansion (3 variants)
  ├─ Stage 2: Auto-route (arxiv for academic papers)
  ├─ Stage 3: Search (exa + arxiv)
  ├─ Stage 4-6: Fetch & extract
  ├─ Stage 7: GitHub enrichment
  ├─ Stage 12: Synthesize with citations
→ 5-minute research, <$0.50 cost
```

### Workflow 3: Expert Discovery
```
research_find_experts(topic="AI Safety", n=10)
→ research_spider(expert_websites, mode="stealthy")
→ research_llm_embed(bios) for clustering
→ rank by relevance
```

### Workflow 4: Fact-Check with Red Team
```
research_deep(query, include_red_team=True, include_misinfo_check=True)
  ├─ Stage 10: research_red_team
  │   └─ Challenge each claim
  ├─ Stage 11: research_misinfo_check
  │   └─ Verify against fact databases
  └─ Stage 12: Synthesize with confidence scores
→ High-confidence fact-checked answer
```

### Workflow 5: Community Sentiment Analysis
```
research_community_sentiment(topic="New AI Model")
→ research_search(topic, provider="reddit")
→ research_search(topic, provider="hackernews")
→ Aggregate sentiment + trending claims
```

### Workflow 6: YouTube Research
```
research_deep(query, search_providers=["youtube"])
→ Auto-detects YouTube URLs in results
→ fetch_youtube_transcript(youtube_url)
→ research_llm_extract(transcript)
→ Synthesize from transcripts
```

### Workflow 7: Multi-Language Research
```
research_deep(query, language="ar")  # Arabic
→ research_spider(urls, accept_language="ar")
→ research_detect_language(text)
→ research_llm_translate(arabic_text, target_language="en")
→ Bilingual synthesis
```

## Configuration Guide

### Search Provider Selection

**For code/library research:**
```json
{
  "DEFAULT_SEARCH_PROVIDER": "exa",
  "RESEARCH_SEARCH_PROVIDERS": ["exa", "tavily"],
  "RESEARCH_GITHUB_ENRICHMENT": true
}
```

**For academic papers:**
```json
{
  "DEFAULT_SEARCH_PROVIDER": "arxiv",
  "RESEARCH_SEARCH_PROVIDERS": ["arxiv"],
  "RESEARCH_EXPAND_QUERIES": true
}
```

**For general knowledge:**
```json
{
  "DEFAULT_SEARCH_PROVIDER": "tavily",
  "RESEARCH_SEARCH_PROVIDERS": ["exa", "tavily", "wikipedia"]
}
```

### Performance Tuning

**For fast, shallow research:**
```json
{
  "SPIDER_CONCURRENCY": 10,
  "EXTERNAL_TIMEOUT_SECS": 15,
  "CACHE_TTL_DAYS": 7,
  "RESEARCH_EXPAND_QUERIES": false,
  "RESEARCH_EXTRACT": false
}
```

**For thorough, deep research:**
```json
{
  "SPIDER_CONCURRENCY": 5,
  "EXTERNAL_TIMEOUT_SECS": 60,
  "CACHE_TTL_DAYS": 30,
  "RESEARCH_EXPAND_QUERIES": true,
  "RESEARCH_COMMUNITY_SENTIMENT": true,
  "RESEARCH_RED_TEAM": true
}
```

### Cost Management

**Conservative (academic use):**
```json
{
  "LLM_DAILY_COST_CAP_USD": 5.0,
  "RESEARCH_MAX_COST_USD": 0.10,
  "LLM_CASCADE_ORDER": ["vllm", "nvidia"]
}
```

**Generous (production):**
```json
{
  "LLM_DAILY_COST_CAP_USD": 100.0,
  "RESEARCH_MAX_COST_USD": 5.0,
  "LLM_CASCADE_ORDER": ["openai", "anthropic", "nvidia"]
}
```

## Troubleshooting

### Issue: "SSRF Error: host resolves to blocked address"

**Cause:** Loom rejected a private/internal IP (127.0.0.1, 10.x.x.x, etc.)

**Solution:**
- Verify URL is public-facing
- Check DNS doesn't resolve to local IP
- Contact server admin if URL should be accessible

### Issue: "Cost cap exceeded"

**Cause:** LLM spending exceeded RESEARCH_MAX_COST_USD or daily limit

**Solution:**
```bash
# Reduce cost cap or disable expensive stages
research_config_set("RESEARCH_MAX_COST_USD", 1.0)
research_config_set("RESEARCH_RED_TEAM", False)
research_config_set("RESEARCH_MISINFO_CHECK", False)
```

### Issue: "Fetch timeout after 30s"

**Cause:** Page took >30s to load or fetch escalation failed

**Solution:**
```bash
# Increase timeout
research_config_set("EXTERNAL_TIMEOUT_SECS", 60)

# Or use manual fetch with stealthy mode
research_fetch(url, mode="stealthy", timeout=120)
```

### Issue: "Missing API key for provider X"

**Cause:** Provider API key not set in environment

**Solution:**
```bash
# Set key
export EXA_API_KEY="sk-..."

# Verify
echo $EXA_API_KEY

# Or use fallback provider
research_config_set("DEFAULT_SEARCH_PROVIDER", "tavily")
```

### Issue: "Cache growing too large"

**Cause:** Cache directory >1GB

**Solution:**
```bash
# Clear old entries
research_cache_clear(days=7)

# Reduce TTL
research_config_set("CACHE_TTL_DAYS", 7)

# View current usage
research_cache_stats()
```

### Issue: "research_deep returns empty answer"

**Cause:** No search results or extraction failed

**Solution:**
1. Check query is specific enough
2. Verify search provider has API key
3. Try manual search + fetch:
   ```python
   results = research_search(query, provider="exa")
   for r in results:
       text = research_fetch(r['url'], mode="stealthy")
   ```
4. Enable DEBUG logging:
   ```bash
   research_config_set("LOG_LEVEL", "DEBUG")
   ```

### Issue: "Session expired" on research_spider

**Cause:** Browser session TTL exceeded

**Solution:**
```bash
# Increase session TTL
research_session_open(name="my_session", ttl_seconds=7200)

# Or keep session alive with periodic access
research_session_list()  # Refreshes last_used timestamp
```

### Issue: "Stealth mode detected as bot"

**Cause:** Even Camoufox rejected; site uses advanced bot detection

**Solution:**
1. Add custom headers:
   ```python
   research_fetch(url, mode="dynamic", headers={"Referer": "..."})
   ```
2. Use session with login:
   ```python
   research_session_open(..., login_url="...")
   ```
3. Report to [Camoufox/Scrapling](https://github.com/astromild/camoufox) with details

## Environment Variables Reference

```bash
# Server
LOOM_HOST=127.0.0.1
LOOM_PORT=8787
LOOM_CONFIG_PATH=~/.loom/config.json
LOOM_CACHE_DIR=~/.cache/loom
LOOM_SESSIONS_DIR=~/.loom/sessions

# API Keys
EXA_API_KEY=...
TAVILY_API_KEY=...
FIRECRAWL_API_KEY=...
BRAVE_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...

# LLM
NVIDIA_NIM_API_KEY=...  (if using NIM)

# Advanced
LOG_LEVEL=INFO
```

## Performance Tips

1. **Use caching:** Same query = cache hit (0ms)
2. **Set provider explicitly:** Avoid auto-detection overhead for known types
3. **Parallel spider:** Increase concurrency if network permits (1-20)
4. **Skip expensive stages:** Disable red_team + misinfo_check for speed
5. **Use vLLM for local:** Fastest (free) LLM tier in cascade

## API Reference

For complete API details, see [architecture.md](./architecture.md) and inline docstrings:

```bash
python -c "from loom.tools.deep import research_deep; help(research_deep)"
python -c "from loom.tools.search import research_search; help(research_search)"
```

---

**Need help?** Check logs:
```bash
tail -f ~/.loom/loom.log
```

See [architecture.md](./architecture.md) for system design details.
