# Loom API Keys & Environment Variables

Complete reference for all environment variables, API keys, and configuration options used by Loom.

---


## LLM Providers

All LLM tools use cascade routing. Set up at least one of the following. Default cascade order: Groq → NVIDIA NIM → DeepSeek → Gemini → Moonshot → OpenAI → Anthropic → vLLM.

### GROQ_API_KEY

**Service:** Groq API  
**Signup:** https://console.groq.com  
**Free Tier:** 30,000 requests/month (extremely fast inference)  
**Paid Tiers:** $0.0005-$0.05 per 1K tokens  
**Default Model:** `mixtral-8x7b-32768`  
**What it unlocks:** Fastest LLM option; excellent for production  

```bash
export GROQ_API_KEY="gsk-your-key"
```

---

### NVIDIA_NIM_API_KEY

**Service:** NVIDIA NIM (free tier)  
**Signup:** https://build.nvidia.com  
**Free Tier:** 25,000 requests/month (roughly $0.04/1K tokens)  
**Paid Tiers:** Custom enterprise pricing  
**Default Model:** `meta/llama-4-maverick-17b-128e-instruct`  
**What it unlocks:** Excellent free tier; good cascade fallback option  

```bash
export NVIDIA_NIM_API_KEY="nvapi-your-key"
export NVIDIA_NIM_ENDPOINT="https://integrate.api.nvidia.com/v1"  # optional, has default
```

---

### DEEPSEEK_API_KEY

**Service:** DeepSeek API  
**Signup:** https://platform.deepseek.com  
**Free Tier:** Variable (check pricing)  
**Paid Tiers:** Pay-per-token  
**Default Model:** `deepseek-chat`  
**What it unlocks:** Advanced reasoning capabilities  

```bash
export DEEPSEEK_API_KEY="sk-your-key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"  # optional, has default
```

---

### GOOGLE_AI_KEY

**Service:** Google Gemini API  
**Signup:** https://ai.google.dev  
**Free Tier:** Limited (check quotas)  
**Paid Tiers:** Pay-per-token  
**Default Model:** `gemini-pro`  
**What it unlocks:** Google's multimodal LLM capabilities  

```bash
export GOOGLE_AI_KEY="your-gemini-key"
```

---

### MOONSHOT_API_KEY

**Service:** Moonshot (Kimi) API  
**Signup:** https://kimi.moonshot.cn  
**Free Tier:** Limited credits  
**Paid Tiers:** Pay-per-token  
**Default Model:** `moonshot-v1-128k`  
**What it unlocks:** Long-context multilingual LLM  

```bash
export MOONSHOT_API_KEY="sk-your-key"
export MOONSHOT_BASE_URL="https://api.moonshot.cn/v1"  # optional, has default
```

---

### OPENAI_API_KEY

**Service:** OpenAI API  
**Signup:** https://platform.openai.com  
**Free Trial:** $5 credit (expires 3 months)  
**Paid Tiers:** Pay-per-token ($0.003-$0.03 per 1K tokens depending on model)  
**Default Model:** `gpt-4-mini`  
**What it unlocks:** Highest quality models; reliable cascade fallback  

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
**What it unlocks:** Claude models for specialized tasks; strong reasoning  

```bash
export ANTHROPIC_API_KEY="sk-ant-your-key"
```

---

### vLLM_LOCAL_ENDPOINT

**Service:** Local vLLM server  
**Signup:** Self-hosted (https://github.com/vllm-project/vllm)  
**Cost:** Free (hardware costs only)  
**Default Model:** Configurable (e.g., `meta-llama/Llama-2-70b-hf`)  
**What it unlocks:** Offline LLM inference; full control over models  

```bash
export VLLM_BASE_URL="http://localhost:8000/v1"  # vLLM API endpoint
export VLLM_MODEL="meta-llama/Llama-2-70b-hf"  # Model to use
```

---

## Search Providers (21 total)

### Standard Web Search (4 providers)

#### EXA_API_KEY

**Service:** Exa semantic search  
**Signup:** https://dashboard.exa.ai  
**Free Tier:** 10 queries/month  
**Paid Tiers:** $9-$999/month  
**What it unlocks:** Neural semantic search; required for `research_search(provider="exa")`  

```bash
export EXA_API_KEY="your-exa-api-key"
```

#### TAVILY_API_KEY

**Service:** Tavily agent-native search  
**Signup:** https://tavily.com  
**Free Tier:** 100 queries/month  
**Paid Tiers:** $30-$3000/month  
**What it unlocks:** Structured web search; required for `research_search(provider="tavily")`  

```bash
export TAVILY_API_KEY="your-tavily-api-key"
```

#### FIRECRAWL_API_KEY

**Service:** Firecrawl web intelligence  
**Signup:** https://app.firecrawl.dev  
**Free Tier:** 500 credits/month  
**Paid Tiers:** $99+/month  
**What it unlocks:** Web search + page extraction; required for `research_search(provider="firecrawl")`  

```bash
export FIRECRAWL_API_KEY="your-firecrawl-api-key"
```

#### BRAVE_API_KEY

**Service:** Brave Search REST API  
**Signup:** https://api.search.brave.com  
**Free Tier:** Unlimited for personal use (20 results/query max, no domain filters)  
**Paid Tiers:** $10-$100/month  
**What it unlocks:** Privacy-focused search; required for `research_search(provider="brave")`  

```bash
export BRAVE_API_KEY="your-brave-api-key"
```

### Academic & Community (3 providers)

#### Arxiv (No API key)
Search academic papers. Used by `research_search(provider="arxiv")`. Free and unlimited.

#### Wikipedia (No API key)
Knowledge base search. Used by `research_search(provider="wikipedia")`. Free and unlimited.

#### Hacker News & Reddit (No API key)
Community sentiment and discussions. Free and unlimited.

### Data & Finance (4 providers)

#### NEWS_API_KEY

**Service:** NewsAPI  
**Signup:** https://newsapi.org  
**Free Tier:** 100 requests/day  
**Paid Tiers:** $39+/month  
**What it unlocks:** News article search; required for `research_search(provider="newsapi")`  

```bash
export NEWS_API_KEY="your-newsapi-key"
```

#### COINDESK_API_KEY

**Service:** CoinDesk API  
**Signup:** https://www.coindesk.com/api  
**Free Tier:** Limited  
**Paid Tiers:** Contact sales  
**What it unlocks:** Cryptocurrency news; required for `research_search(provider="coindesk")`  

```bash
export COINDESK_API_KEY="your-coindesk-key"
```

#### COINMARKETCAP_API_KEY

**Service:** CoinMarketCap API  
**Signup:** https://coinmarketcap.com/api  
**Free Tier:** 333 calls/day  
**Paid Tiers:** $99-$999/month  
**What it unlocks:** Crypto market data; used for `research_search(provider="coinmarketcap")`  

```bash
export COINMARKETCAP_API_KEY="your-cmc-key"
```

#### Binance Data (No API key)
Live crypto price data and trading info. Free and unlimited via public API.

### Darkweb & Specialized (7 providers)

#### Ahmia (No API key)
Tor hidden services search. Free and unlimited.

#### Darksearch (No API key)
Alternative darkweb search. Free and unlimited.

#### OnionSearch (No API key)
Tor onion crawler. Uses SOCKS5 proxy. Free and unlimited.

#### TorCrawl (No API key)
Tor crawling pattern. Uses SOCKS5 proxy. Free and unlimited.

#### deepdarkCTI (No API key)
Dark web threat intelligence sources. Free and unlimited.

#### robin OSINT (No API key)
AI-powered dark web OSINT tool. Free and unlimited.

#### UMMRO_RAG_URL

**Service:** UMMRO RAG endpoint  
**What it unlocks:** Custom knowledge base search  

```bash
export UMMRO_RAG_URL="https://your-ummro-endpoint/api/query"
```

### GitHub Integration

#### GITHUB_TOKEN

**Service:** GitHub API  
**Signup:** https://github.com/settings/tokens  
**Free Tier:** 60 requests/hour (unauthenticated)  
**Authenticated:** 5,000 requests/hour  
**What it unlocks:** Increased rate limits for `research_github`, `research_github_readme`, `research_github_releases`; required for private repo access  

```bash
export GITHUB_TOKEN="ghp_your-token"
```

---

## Security & Intelligence Tools

### HIBP_API_KEY (Optional)

**Service:** Have I Been Pwned (HIBP)  
**Signup:** https://haveibeenpwned.com/API/v3  
**Free Tier:** k-anonymity password check (no key needed)  
**Paid Tier:** $3.50/month for full API access  
**What it unlocks:** Breach detection via `research_breach_check` (works without key, limited)  

```bash
export HIBP_API_KEY="your-hibp-api-key"
```

---

### ABUSEIPDB_API_KEY (Optional)

**Service:** AbuseIPDB IP reputation  
**Signup:** https://www.abuseipdb.com/register  
**Free Tier:** 1,500 requests/day (IP reputation basic)  
**Paid Tiers:** $9.99+/month (advanced features)  
**What it unlocks:** IP reputation lookup via `research_ip_reputation` (ip-api.com works without key)  

```bash
export ABUSEIPDB_API_KEY="your-abuseipdb-api-key"
```

---

### NVD_API (No Key Required)

**Service:** National Vulnerability Database  
**Signup:** Free, no registration needed  
**Rate Limit:** 5 requests per 30 seconds  
**What it unlocks:** CVE vulnerability lookup via `research_cve_lookup` and `research_cve_detail`  

Free and unlimited (rate-limited).

---

### URLhaus API (No Key Required)

**Service:** URLhaus (abuse.ch)  
**Signup:** Free, no registration needed  
**Rate Limit:** Reasonable limits for automated queries  
**What it unlocks:** Malicious URL detection via `research_urlhaus_check` and `research_urlhaus_search`  

Free and unlimited.

---

## System Tools (No API Keys)

The following tools require CLI tools or local data files:

### research_nmap_scan
**Requires:** `nmap` CLI installed (`brew install nmap` or `apt install nmap`)  
**What it does:** Network scanning and port enumeration  
**No API key needed**

---

### research_text_analyze
**Requires:** NLTK (installed via pip)  
**Setup:** Runs `nltk.download('punkt', 'averaged_perceptron_tagger')` automatically on first use  
**What it does:** Natural language processing and text analysis  
**No API key needed**

---

### research_screenshot
**Requires:** Playwright browsers installed (`playwright install chromium`)  
**What it does:** Capture webpage screenshots and render visual content  
**No API key needed**

---

### research_geoip_local
**Requires:** GeoLite2-City.mmdb (MaxMind GeoIP database)  
**Setup:** Download from https://www.maxmind.com/en/geolite2-freegeoip (free registration)  
**Location:** `~/.maxmind/GeoLite2-City.mmdb`  
**What it does:** Local IP geolocation (no internet requests, fully offline)  
**No API key needed**

```bash
# After downloading from MaxMind:
mkdir -p ~/.maxmind
mv GeoLite2-City.mmdb ~/.maxmind/
```

---

### research_ocr_extract
**Requires:** Tesseract OCR CLI (`brew install tesseract` or `apt install tesseract-ocr`)  
**What it does:** Extract text from images using optical character recognition  
**No API key needed**

---

### research_exif_extract
**Requires:** Pillow (installed via pip, already included)  
**What it does:** Extract metadata (EXIF) from images  
**No API key needed**

---

## Infrastructure & Services

### VASTAI_API_KEY

**Service:** VastAI GPU compute marketplace  
**Signup:** https://www.vast.ai  
**What it unlocks:** Search GPU instances and check compute market prices via `research_vastai_search` and `research_vastai_status`  

```bash
export VASTAI_API_KEY="your-vastai-key"
```

---

### STRIPE_LIVE_KEY

**Service:** Stripe payment API  
**Signup:** https://stripe.com  
**What it unlocks:** Check billing and payment data via `research_stripe_balance`  

```bash
export STRIPE_LIVE_KEY="sk_live_your-key"
```

---

### Email Service (SMTP)

#### SMTP_USER

**Type:** Email address (e.g., your Gmail address)  
**What it unlocks:** Email sending via `research_email_report`  

```bash
export SMTP_USER="your-email@gmail.com"
```

---

#### SMTP_APP_PASSWORD

**Type:** Application password (not your main password)  
**Gmail:** Generate at https://myaccount.google.com/apppasswords  
**What it unlocks:** SMTP authentication for `research_email_report`  

```bash
export SMTP_APP_PASSWORD="your-16-char-app-password"
```

---

### JOPLIN_TOKEN

**Service:** Joplin note-taking API  
**Signup:** https://joplinapp.org (self-hosted or cloud)  
**What it unlocks:** Save and list notes via `research_save_note` and `research_list_notebooks`  

```bash
export JOPLIN_TOKEN="your-joplin-api-token"
export JOPLIN_BASE_URL="http://localhost:41184"  # optional, has default
```

---

## Communication & Notifications

### SLACK_BOT_TOKEN

**Service:** Slack Bot API  
**Signup:** https://api.slack.com/apps  
**What it unlocks:** Send notifications via `research_slack_notify`  

```bash
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
```

---

### GOOGLE_CLOUD_API_KEY

**Service:** Google Cloud (Vision, TTS)  
**Signup:** https://console.cloud.google.com  
**What it unlocks:** Image analysis and text-to-speech via `research_gcp_vision`, `research_gcp_tts`  

```bash
export GOOGLE_CLOUD_API_KEY="your-gcloud-api-key"
```

---

## Tor & Darkweb

### TOR_CONTROL_PASSWORD

**Service:** Tor control port authentication  
**Setup:** Configure in Tor config file  
**What it unlocks:** Check Tor status and request new identity via `research_tor_status` and `research_tor_new_identity`  

```bash
export TOR_CONTROL_PASSWORD="your-tor-password"
export TOR_CONTROL_HOST="127.0.0.1"  # optional, default localhost
export TOR_CONTROL_PORT="9051"  # optional, default 9051
```

---

## Media Processing

No API keys required for:

- `research_transcribe` — Audio to text (uses local speech recognition)
- `research_convert_document` — Document format conversion (uses local libraries)

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

For a functional Loom installation with all tools:

```bash
# REQUIRED: At least ONE LLM provider (try in this order)
export GROQ_API_KEY="gsk-your-key"                   # Best: fastest + free
# OR
export NVIDIA_NIM_API_KEY="nvapi-your-key"           # Free tier option
# OR
export OPENAI_API_KEY="sk-your-key"                  # High quality

# REQUIRED: At least ONE search provider
export EXA_API_KEY="your-exa-key"                    # Best: semantic
# OR
export BRAVE_API_KEY="your-brave-key"                # Free: privacy-focused

# OPTIONAL: GitHub (for code search)
export GITHUB_TOKEN="ghp_your-token"

# OPTIONAL: Specialized services (one-by-one)
export VASTAI_API_KEY="your-vastai-key"              # GPU pricing
export STRIPE_LIVE_KEY="sk_live_your-key"            # Billing
export JOPLIN_TOKEN="your-joplin-token"              # Notes
export TOR_CONTROL_PASSWORD="your-tor-password"      # Darkweb
export SMTP_USER="your-email@gmail.com"              # Email
export SMTP_APP_PASSWORD="your-16-char-password"     # Email auth

# RECOMMENDED: Performance tuning
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
