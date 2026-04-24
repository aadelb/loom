# Loom API Keys & Environment Variables

Complete reference for all environment variables, API keys, and configuration options used by Loom.

---

## Search Providers

### EXA_API_KEY

**Service:** Exa semantic search  
**Signup:** https://dashboard.exa.ai  
**Free Tier:** 10 queries/month  
**Paid Tiers:** $9-$999/month  
**What it unlocks:** Neural semantic search across the web; required for `research_search(provider="exa")`

```bash
export EXA_API_KEY="your-exa-api-key"
```

---

### TAVILY_API_KEY

**Service:** Tavily agent-native search  
**Signup:** https://tavily.com  
**Free Tier:** 100 queries/month  
**Paid Tiers:** $30-$3000/month  
**What it unlocks:** Structured web search with agent-friendly output; required for `research_search(provider="tavily")`

```bash
export TAVILY_API_KEY="your-tavily-api-key"
```

---

### FIRECRAWL_API_KEY

**Service:** Firecrawl web intelligence search  
**Signup:** https://app.firecrawl.dev  
**Free Tier:** 500 credits/month  
**Paid Tiers:** $99+/month  
**What it unlocks:** Web search + page extraction; required for `research_search(provider="firecrawl")`

```bash
export FIRECRAWL_API_KEY="your-firecrawl-api-key"
```

---

### BRAVE_API_KEY

**Service:** Brave Search REST API  
**Signup:** https://api.search.brave.com  
**Free Tier:** Unlimited for personal use (20 results/query max, no domain filters)  
**Paid Tiers:** $10-$100/month for premium features  
**What it unlocks:** Privacy-focused web search; required for `research_search(provider="brave")`

```bash
export BRAVE_API_KEY="your-brave-api-key"
```

---

## LLM Providers

All LLM tools use cascade routing. Set up at least one of the following:

### NVIDIA_NIM_API_KEY

**Service:** NVIDIA NIM (free tier)  
**Signup:** https://build.nvidia.com  
**Free Tier:** 25,000 requests/month (roughly $0.04/1K tokens)  
**Paid Tiers:** Custom enterprise pricing  
**Default Model:** `meta/llama-4-maverick-17b-128e-instruct`  
**What it unlocks:** Fastest cascade option; free tier is excellent for development  

```bash
export NVIDIA_NIM_API_KEY="nvapi-your-key"
export NVIDIA_NIM_ENDPOINT="https://integrate.api.nvidia.com/v1"  # optional, has default
```

---

### OPENAI_API_KEY

**Service:** OpenAI API  
**Signup:** https://platform.openai.com  
**Free Trial:** $5 credit (expires 3 months)  
**Paid Tiers:** Pay-per-token ($0.003-$0.03 per 1K tokens depending on model)  
**Default Model:** `gpt-4-mini`  
**What it unlocks:** Fallback when NVIDIA NIM is rate-limited; highest quality models  

```bash
export OPENAI_API_KEY="sk-your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional, has default
```

---

### ANTHROPIC_API_KEY

**Service:** Anthropic API (Claude)  
**Signup:** https://console.anthropic.com  
**Free Trial:** None (pay-per-token)  
**Paid Tiers:** $0.003-$0.03 per 1K tokens  
**Default Model:** `claude-opus-4-6`  
**What it unlocks:** Third cascade option; Claude models for specialized tasks  

```bash
export ANTHROPIC_API_KEY="sk-ant-your-key"
```

---

## GitHub Integration

### GITHUB_TOKEN

**Service:** GitHub API  
**Signup:** https://github.com/settings/tokens  
**Free Tier:** 60 requests/hour (unauthenticated)  
**Authenticated:** 5,000 requests/hour  
**What it unlocks:** Increased rate limits for `research_github`, `research_github_readme`, `research_github_releases`; required for private repo access  

```bash
export GITHUB_TOKEN="ghp_your-token"
```

---

## Core Configuration Variables

### LOOM_HOST

**Type:** string  
**Default:** `"127.0.0.1"`  
**Description:** Host for MCP server to bind to

```bash
export LOOM_HOST="0.0.0.0"  # to listen on all interfaces
```

---

### LOOM_PORT

**Type:** integer  
**Default:** `8787`  
**Description:** Port for MCP server

```bash
export LOOM_PORT="8787"
```

---

### LOOM_CONFIG_PATH

**Type:** string (file path)  
**Default:** `./config.json`  
**Description:** Path to runtime config file (JSON). Merged over code defaults.

```bash
export LOOM_CONFIG_PATH="/etc/loom/config.json"
```

---

### LOG_LEVEL

**Type:** string  
**Default:** `"INFO"`  
**Valid values:** `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`  
**Description:** Logging verbosity

```bash
export LOG_LEVEL="DEBUG"
```

---

### LOOM_LOGS_DIR

**Type:** string (directory path)  
**Default:** `~/.cache/loom/logs`  
**Description:** Directory for LLM cost logs (atomic JSON per day)

```bash
export LOOM_LOGS_DIR="/var/log/loom"
```

---

## Search & Scraping Configuration

### SPIDER_CONCURRENCY

**Type:** integer  
**Default:** `5`  
**Valid range:** 1-20  
**Description:** Max concurrent fetches in `research_spider`

```bash
export SPIDER_CONCURRENCY="10"
```

---

### EXTERNAL_TIMEOUT_SECS

**Type:** integer  
**Default:** `30`  
**Valid range:** 5-120  
**Description:** Timeout for external HTTP requests (seconds)

```bash
export EXTERNAL_TIMEOUT_SECS="60"
```

---

### MAX_FETCH_CHARS

**Type:** integer  
**Default:** `200000` (200 KB)  
**Valid range:** 1,000-2,000,000  
**Description:** Hard cap on characters returned by `research_fetch`

```bash
export MAX_FETCH_CHARS="500000"
```

---

### MAX_SPIDER_URLS

**Type:** integer  
**Default:** `100`  
**Valid range:** 1-500  
**Description:** Max URLs per `research_spider` call

```bash
export MAX_SPIDER_URLS="500"
```

---

### DEFAULT_SEARCH_PROVIDER

**Type:** string  
**Default:** `"exa"`  
**Valid values:** `"exa"`, `"tavily"`, `"firecrawl"`, `"brave"`, `"ddgs"`, `"arxiv"`, `"wikipedia"`, `"hackernews"`, `"reddit"`  
**Description:** Default provider for `research_search` when not specified

```bash
export DEFAULT_SEARCH_PROVIDER="brave"  # fallback if EXA_API_KEY not set
```

---

### DEFAULT_ACCEPT_LANGUAGE

**Type:** string  
**Default:** `"en-US,en;q=0.9,ar;q=0.8"`  
**Description:** Accept-Language header for all fetches

```bash
export DEFAULT_ACCEPT_LANGUAGE="ar,en;q=0.9"  # Arabic preferred
```

---

### FETCH_AUTO_ESCALATE

**Type:** boolean  
**Default:** `true`  
**Description:** Auto-escalate http → stealthy → dynamic on Cloudflare blocks

```bash
export FETCH_AUTO_ESCALATE="false"
```

---

## Cache Configuration

### CACHE_TTL_DAYS

**Type:** integer  
**Default:** `30`  
**Valid range:** 1-365  
**Description:** Default cache retention in days; older entries purged by `research_cache_clear`

```bash
export CACHE_TTL_DAYS="7"  # keep cache 1 week
```

---

### LOOM_CACHE_DIR

**Type:** string (directory path)  
**Default:** `~/.cache/loom/cache` (on Unix), `%APPDATA%\Loom\cache` (Windows)  
**Description:** Directory for fetch result cache

```bash
export LOOM_CACHE_DIR="/mnt/cache/loom"
```

---

## LLM Configuration

### LLM_DEFAULT_CHAT_MODEL

**Type:** string  
**Default:** `"meta/llama-4-maverick-17b-128e-instruct"`  
**Description:** Default model for `research_llm_chat`, `research_llm_summarize`, etc. when `model="auto"`

```bash
export LLM_DEFAULT_CHAT_MODEL="gpt-4-mini"
```

---

### LLM_DEFAULT_EMBED_MODEL

**Type:** string  
**Default:** `"nvidia/nv-embed-v2"`  
**Description:** Default model for `research_llm_embed`

```bash
export LLM_DEFAULT_EMBED_MODEL="openai/text-embedding-3-large"
```

---

### LLM_DEFAULT_TRANSLATE_MODEL

**Type:** string  
**Default:** `"moonshotai/kimi-k2-instruct"`  
**Description:** Default model for `research_llm_translate`

```bash
export LLM_DEFAULT_TRANSLATE_MODEL="gpt-4-mini"
```

---

### LLM_MAX_PARALLEL

**Type:** integer  
**Default:** `12`  
**Valid range:** 1-64  
**Description:** Max concurrent LLM requests (NVIDIA NIM rate limit)

```bash
export LLM_MAX_PARALLEL="20"
```

---

### LLM_DAILY_COST_CAP_USD

**Type:** float  
**Default:** `10.0`  
**Valid range:** 0.0-1000.0  
**Description:** Daily spend cap across all LLM calls (raises `RuntimeError` if exceeded)

```bash
export LLM_DAILY_COST_CAP_USD="5.00"  # $5/day max
```

---

### LLM_CASCADE_ORDER

**Type:** string or list  
**Default:** `"nvidia,openai,anthropic,vllm"`  
**Description:** Provider cascade order for LLM tools. Comma-separated string or JSON list.

```bash
export LLM_CASCADE_ORDER="openai,nvidia,anthropic"
# or in config.json:
# "LLM_CASCADE_ORDER": ["openai", "nvidia"]
```

---

## Research Pipeline Configuration

### RESEARCH_SEARCH_PROVIDERS

**Type:** string or list  
**Default:** `"exa,brave"`  
**Description:** Providers used by `research_deep` for multi-provider search

```bash
export RESEARCH_SEARCH_PROVIDERS="exa,brave,ddgs"
```

---

### RESEARCH_EXPAND_QUERIES

**Type:** boolean  
**Default:** `true`  
**Description:** Enable LLM query expansion in `research_deep`

```bash
export RESEARCH_EXPAND_QUERIES="false"
```

---

### RESEARCH_EXTRACT

**Type:** boolean  
**Default:** `true`  
**Description:** Enable LLM content extraction in `research_deep`

```bash
export RESEARCH_EXTRACT="false"
```

---

### RESEARCH_SYNTHESIZE

**Type:** boolean  
**Default:** `true`  
**Description:** Enable LLM answer synthesis in `research_deep`

```bash
export RESEARCH_SYNTHESIZE="false"
```

---

### RESEARCH_GITHUB_ENRICHMENT

**Type:** boolean  
**Default:** `true`  
**Description:** Include GitHub repos and README in `research_deep` for code-related queries

```bash
export RESEARCH_GITHUB_ENRICHMENT="false"
```

---

### RESEARCH_MAX_COST_USD

**Type:** float  
**Default:** `0.50`  
**Valid range:** 0.0-10.0  
**Description:** LLM cost cap for a single `research_deep` call

```bash
export RESEARCH_MAX_COST_USD="2.00"
```

---

### RESEARCH_COMMUNITY_SENTIMENT

**Type:** boolean  
**Default:** `false`  
**Description:** Include HN + Reddit sentiment in `research_deep` (off by default, adds cost)

```bash
export RESEARCH_COMMUNITY_SENTIMENT="true"
```

---

### RESEARCH_RED_TEAM

**Type:** boolean  
**Default:** `false`  
**Description:** Include adversarial counter-argument search in `research_deep` (off by default, adds cost)

```bash
export RESEARCH_RED_TEAM="true"
```

---

### RESEARCH_MISINFO_CHECK

**Type:** boolean  
**Default:** `false`  
**Description:** Include misinformation stress-test in `research_deep` (off by default, adds cost)

```bash
export RESEARCH_MISINFO_CHECK="true"
```

---

## Session Configuration

### SESSION_DIR

**Type:** string (directory path)  
**Default:** `~/.loom/sessions`  
**Description:** Directory for browser session metadata and state

```bash
export SESSION_DIR="/tmp/loom-sessions"
```

---

## Browser-Specific Configuration

### CAMOUFOX_BINARY

**Type:** string (file path)  
**Default:** auto-detected  
**Description:** Path to Camoufox binary (optional, auto-found if in PATH)

```bash
export CAMOUFOX_BINARY="/opt/camoufox/firefox"
```

---

### STEALTH_TIMEOUT

**Type:** integer  
**Default:** `60`  
**Description:** Timeout for stealth browser operations (seconds)

```bash
export STEALTH_TIMEOUT="120"
```

---

## Minimum Viable Key Set

For a functional Loom installation with all features:

```bash
# Required: At least ONE search provider
export EXA_API_KEY="your-exa-key"                    # Best: semantic search

# Required: At least ONE LLM provider
export NVIDIA_NIM_API_KEY="your-nim-key"             # Best: free tier

# Optional: GitHub support
export GITHUB_TOKEN="your-github-token"              # Increases rate limits

# Optional: Fallback search provider
export BRAVE_API_KEY="your-brave-key"                # Free tier available

# Optional: Fallback LLM provider
export OPENAI_API_KEY="your-openai-key"              # If NIM rate-limited

# Recommended: Performance tuning
export SPIDER_CONCURRENCY="10"
export LOG_LEVEL="INFO"
export LLM_DAILY_COST_CAP_USD="10.00"
```

---

## Configuration File (config.json)

Instead of environment variables, you can use a config file at `$LOOM_CONFIG_PATH` (default: `./config.json`):

```json
{
  "SPIDER_CONCURRENCY": 10,
  "EXTERNAL_TIMEOUT_SECS": 60,
  "MAX_FETCH_CHARS": 500000,
  "CACHE_TTL_DAYS": 7,
  "DEFAULT_SEARCH_PROVIDER": "exa",
  "LOG_LEVEL": "INFO",
  "LLM_DEFAULT_CHAT_MODEL": "gpt-4-mini",
  "LLM_MAX_PARALLEL": 20,
  "LLM_DAILY_COST_CAP_USD": 5.0,
  "LLM_CASCADE_ORDER": ["nvidia", "openai", "anthropic"],
  "RESEARCH_SEARCH_PROVIDERS": ["exa", "brave", "ddgs"],
  "RESEARCH_EXPAND_QUERIES": true,
  "RESEARCH_EXTRACT": true,
  "RESEARCH_SYNTHESIZE": true,
  "RESEARCH_GITHUB_ENRICHMENT": true,
  "RESEARCH_MAX_COST_USD": 1.0,
  "RESEARCH_COMMUNITY_SENTIMENT": false,
  "RESEARCH_RED_TEAM": false,
  "RESEARCH_MISINFO_CHECK": false,
  "FETCH_AUTO_ESCALATE": true
}
```

Environment variables **override** config file values.

---

## Environment Variable Priority

**Highest to Lowest:**
1. Command-line parameter (e.g., `research_search(provider="brave")`)
2. Environment variable (e.g., `export BRAVE_API_KEY="..."`)
3. Config file value (e.g., `config.json`)
4. Code default

---

## Troubleshooting

### "NVIDIA_NIM_API_KEY not set"

```bash
# Check if key is set
echo $NVIDIA_NIM_API_KEY

# Set it
export NVIDIA_NIM_API_KEY="nvapi-your-key"

# Verify connection
curl -H "Authorization: Bearer $NVIDIA_NIM_API_KEY" \
  https://integrate.api.nvidia.com/v1/models
```

### "EXA_API_KEY invalid"

- Check key format (should be alphanumeric)
- Verify at https://dashboard.exa.ai
- Check monthly quota usage

### "OPENAI_API_KEY expired"

- Generate new key at https://platform.openai.com/api-keys
- Check billing status
- Verify organization access

### "Daily LLM cost cap exceeded"

- Increase `LLM_DAILY_COST_CAP_USD` in config
- Check cost logs in `~/.cache/loom/logs/llm_cost_YYYY-MM-DD.json`
- Consider disabling expensive features (red-team, community-sentiment, misinfo-check)

---

## Cost Estimation

### Typical per-call costs (USD):

- `research_search`: $0.00 - $0.02 (depends on provider)
- `research_fetch`: $0.00 (free providers only)
- `research_markdown`: $0.00 (free, uses Crawl4AI)
- `research_llm_summarize`: $0.0002 - $0.001
- `research_llm_extract`: $0.0003 - $0.002
- `research_llm_answer`: $0.0005 - $0.005
- `research_deep` (no LLM): $0.00 - $0.10
- `research_deep` (with synthesis): $0.05 - $0.50
- `research_red_team`: $0.03 - $0.10

---

## Secure Credential Management

**Do NOT commit API keys to git:**

```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "config.json" >> .gitignore

# Use .env file (not tracked by git)
cat > .env << EOF
EXA_API_KEY=your-key
NVIDIA_NIM_API_KEY=your-key
GITHUB_TOKEN=your-token
EOF

# Load in shell
source .env
```

**For Docker/production:**

```bash
# Use secrets management
docker run -e NVIDIA_NIM_API_KEY="$(cat /run/secrets/nvidia_key)" loom-server

# Or environment file
docker run --env-file .env.prod loom-server
```

