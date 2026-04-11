# CLI Reference — loom Command-Line Tool

Loom ships with a full-featured CLI tool (`loom`) that mirrors the MCP tool surface and adds interactive REPL mode.

All `loom` subcommands communicate with the MCP server running on `http://127.0.0.1:8787/mcp` by default.

## Global Flags

These flags apply to all subcommands:

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--server <URL>` | string | `http://127.0.0.1:8787/mcp` | MCP server URL |
| `--timeout <SECS>` | int | 120 | Request timeout in seconds |
| `--json` | flag | false | Output raw JSON |
| `--pretty` | flag | true | Pretty-print output with colors |
| `--quiet` | flag | false | Suppress all output except errors |

Examples:

```bash
loom --server http://remote.example.com:8787/mcp fetch https://example.com
loom --timeout 60 spider urls.txt
loom --json fetch https://example.com | jq .
```

---

## loom serve

Start the MCP server on the specified host and port.

### Synopsis

```text
loom serve [OPTIONS]
```

### Description

Start the Loom MCP server. By default listens on `127.0.0.1:8787` with streamable-http transport. The server accepts MCP client connections and routes requests to the appropriate tools.

### Flags

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--host <ADDR>` | string | `127.0.0.1` | Bind address (use `0.0.0.0` to allow remote clients) |
| `--port <PORT>` | int | `8787` | Bind port |
| `--reload` | flag | false | Auto-reload on code changes (development mode) |
| `--log-level <LEVEL>` | string | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |

### Examples

Start the server with default settings:

```bash
loom serve
```

Start on a different port:

```bash
loom serve --port 8788
```

Allow remote clients (dangerous, requires authentication):

```bash
loom serve --host 0.0.0.0 --port 8787
```

Enable debug logging:

```bash
loom serve --log-level DEBUG
```

Development mode with auto-reload:

```bash
loom serve --reload
```

### Exit Codes

- `0` — Server started successfully
- `1` — Port already in use or binding failed

---

## loom fetch

Fetch a single URL and extract content.

### Synopsis

```text
loom fetch <URL> [OPTIONS]
```

### Description

Fetch a URL with adaptive anti-bot strategy. Automatically chooses between HTTP, JavaScript rendering (dynamic), and stealth browser modes. Returns structured content with metadata.

### Flags

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `<URL>` | string | *required* | URL to fetch |
| `--mode <MODE>` | string | `stealthy` | Fetch mode: `http` (plain HTTP), `dynamic` (JavaScript-enabled), `stealthy` (TLS spoofing) |
| `--header <KEY:VALUE>` | string (repeatable) | — | Add custom HTTP header |
| `--user-agent <STR>` | string | — | Override User-Agent header |
| `--proxy <URL>` | string | — | HTTP/HTTPS proxy URL (format: `http://user:pass@host:port`) |
| `--cookie <NAME=VALUE>` | string (repeatable) | — | Add cookie |
| `--accept-language <LANG>` | string | `en-US,en;q=0.9` | Accept-Language header |
| `--wait-for <SELECTOR>` | string | — | CSS selector to wait for (dynamic mode only) |
| `--return-format <FMT>` | string | `text` | Return format: `text`, `html`, `json`, `screenshot` |
| `--session <NAME>` | string | — | Use persistent browser session (preserves cookies/state) |
| `--save <FILE>` | string | — | Save JSON response to file |
| `--timeout <SECS>` | int | 120 | Request timeout in seconds |

### Examples

Simple HTTP fetch:

```bash
loom fetch https://httpbin.org/html
```

Fetch with custom headers and language:

```bash
loom fetch https://arxiv.org \
  --header "Accept: application/json" \
  --accept-language "ar,en;q=0.8"
```

Stealth fetch with TLS spoofing:

```bash
loom fetch https://cloudflare.com --mode stealthy
```

Wait for dynamic JavaScript content:

```bash
loom fetch https://example.com/spa \
  --mode dynamic \
  --wait-for ".content-loaded"
```

Use a persistent session:

```bash
loom fetch https://huggingface.co/datasets --session my-hf
```

Extract only a CSS subtree:

```bash
loom fetch https://example.com --wait-for "article" --return-format html
```

Take a screenshot:

```bash
loom fetch https://example.com --return-format screenshot --mode dynamic
```

Save response to file:

```bash
loom fetch https://example.com --save output.json --json
```

### Exit Codes

- `0` — Success
- `1` — Network error or tool error
- `2` — URL validation failed (SSRF detected, invalid URL)
- `3` — Server unreachable or timeout

---

## loom spider

Fetch multiple URLs concurrently.

### Synopsis

```text
loom spider <URLS_FILE> [OPTIONS]
```

### Description

Bulk fetch multiple URLs with concurrency control. URLs file should have one URL per line. Results are returned as an array of fetch responses.

### Flags

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `<URLS_FILE>` | path | *required* | File with URLs (one per line) |
| `--concurrency <N>` | int | `5` | Max parallel fetches (range: 1-20) |
| `--mode <MODE>` | string | `stealthy` | Fetch mode: `http`, `dynamic`, `stealthy` |
| `--fail-fast` | flag | false | Stop on first error |
| `--dedupe` | flag | true | Remove duplicate URLs before fetching |
| `--out <DIR>` | string | — | Save each result to a separate JSON file in directory |
| `--timeout <SECS>` | int | 120 | Per-request timeout |
| (all fetch options) | — | — | `--header`, `--proxy`, `--cookie`, `--session`, etc. |

### Examples

Fetch 5 URLs with default concurrency:

```bash
loom spider urls.txt
```

Fetch with 10 parallel workers:

```bash
loom spider urls.txt --concurrency 10
```

Stealthy spider with domain sorting:

```bash
loom spider urls.txt --mode stealthy --concurrency 8
```

Save results to directory:

```bash
loom spider urls.txt --out ./results/
```

Stop on first error:

```bash
loom spider urls.txt --fail-fast
```

Disable deduplication:

```bash
loom spider urls.txt --dedupe=false
```

Fetch with proxy and custom headers:

```bash
loom spider urls.txt \
  --proxy http://proxy.example.com:8080 \
  --header "Authorization: Bearer token"
```

### Exit Codes

- `0` — All URLs fetched successfully
- `1` — One or more URLs failed (unless `--fail-fast`)
- `2` — Validation error (file not found, invalid concurrency)
- `3` — Server unreachable

---

## loom markdown

Extract clean markdown from a URL using Crawl4AI.

### Synopsis

```text
loom markdown <URL> [OPTIONS]
```

### Description

Convert a web page to clean, well-formatted markdown with citations and metadata. Ideal for preparing content for LLM processing.

### Flags

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `<URL>` | string | *required* | URL to convert |
| `--css <SELECTOR>` | string | — | CSS selector to extract only a subtree |
| `--screenshot` | flag | false | Include a screenshot of the page |
| `--session <NAME>` | string | — | Use persistent browser session |
| `--timeout <SECS>` | int | 120 | Request timeout |
| (all fetch options) | — | — | `--header`, `--proxy`, `--cookie`, etc. |

### Examples

Extract clean markdown:

```bash
loom markdown https://example.com
```

Extract only article content:

```bash
loom markdown https://example.com --css "article"
```

Remove navigation before extracting:

```bash
loom markdown https://example.com --css "body" --timeout 30
```

Include screenshot:

```bash
loom markdown https://example.com --screenshot
```

Fetch from authenticated session:

```bash
loom markdown https://huggingface.co/docs --session my-session
```

### Exit Codes

- `0` — Success
- `1` — Extraction error
- `2` — URL validation failed
- `3` — Server unreachable

---

## loom search

Search the web using multiple providers.

### Synopsis

```text
loom search <QUERY> [OPTIONS]
```

### Description

Search across multiple providers (Exa, Tavily, Firecrawl, Brave). Each provider offers different strengths: Exa for neural search, Tavily for keyword search, Firecrawl for web scraping, Brave for privacy-focused search.

### Flags

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `<QUERY>` | string | *required* | Search query |
| `--provider <PROVIDER>` | string | `exa` | Search provider: `exa`, `tavily`, `firecrawl`, `brave` |
| `--n <COUNT>` | int | `10` | Number of results |
| `--include-domain <DOMAIN>` | string (repeatable) | — | Only search these domains |
| `--exclude-domain <DOMAIN>` | string (repeatable) | — | Exclude these domains |
| `--start-date <DATE>` | string | — | Earliest result date (ISO format: YYYY-MM-DD) |
| `--end-date <DATE>` | string | — | Latest result date (ISO format: YYYY-MM-DD) |
| `--language <LANG>` | string | — | Language hint (provider-specific: `en`, `ar`, `fr`, etc.) |

### Examples

Neural search with Exa:

```bash
loom search "prompt injection attacks" --provider exa --n 20
```

Keyword search with Tavily:

```bash
loom search "SSRF vulnerabilities" --provider tavily --n 15
```

Search within date range:

```bash
loom search "AI safety" \
  --start-date 2025-01-01 \
  --end-date 2026-04-11 \
  --n 10
```

Search only arxiv.org and huggingface.co:

```bash
loom search "abliteration" \
  --include-domain arxiv.org \
  --include-domain huggingface.co \
  --n 20
```

Exclude noisy domains:

```bash
loom search "LLM refusal" \
  --exclude-domain reddit.com \
  --exclude-domain twitter.com \
  --n 15
```

Multilingual search:

```bash
loom search "التعلم الآلي" --language ar
```

Brave privacy search:

```bash
loom search "privacy tools" --provider brave --n 10
```

### Exit Codes

- `0` — Search successful
- `1` — Provider error or network failure
- `3` — API rate limit or timeout

---

## loom deep

Multi-step research: search → fetch → analyze → answer.

### Synopsis

```text
loom deep <QUERY> [OPTIONS]
```

### Description

Orchestrate a complete research workflow in one command. Loom searches for relevant URLs, fetches the top results, extracts markdown, and synthesizes a final answer using an LLM.

### Flags

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `<QUERY>` | string | *required* | Research question |
| `--depth <N>` | int | `2` | Research iterations (1-3, higher = deeper but slower) |
| `--provider <PROVIDER>` | string | `exa` | Search provider: `exa`, `tavily`, `firecrawl`, `brave` |

### Examples

Deep research with 2 iterations:

```bash
loom deep "what is SSRF and how does it work" --depth 2
```

Deeper research (3 iterations):

```bash
loom deep "abliteration techniques in LLMs" --depth 3
```

Using Tavily search:

```bash
loom deep "prompt injection" --provider tavily --depth 2
```

### Exit Codes

- `0` — Research complete
- `1` — Search or fetch error
- `3` — Server unreachable or timeout

---

## loom github

Search GitHub repositories, code, or issues.

### Synopsis

```text
loom github <KIND> <QUERY> [OPTIONS]
```

### Description

Search GitHub using the GitHub CLI (`gh`) wrapper. Kind determines what to search: repositories, code files, or issues.

### Flags

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `<KIND>` | string | *required* | Search type: `repo`, `code`, `issues` |
| `<QUERY>` | string | *required* | Search query |
| `--sort <SORT>` | string | `stars` | Sort order: `best-match`, `stars`, `forks`, `updated` |
| `--order <ORDER>` | string | `desc` | Order: `asc`, `desc` |
| `--language <LANG>` | string | — | Programming language (for code search): `python`, `javascript`, `rust`, etc. |
| `--owner <USER>` | string | — | Filter by repository owner |
| `--repo <REPO>` | string | — | Filter by repository name (format: `owner/repo`) |
| `--limit <COUNT>` | int | `20` | Max results |

### Examples

Search repositories by stars:

```bash
loom github repo "mcp server" --sort stars --limit 20
```

Search code in Python:

```bash
loom github code "def research_fetch" --language python
```

Search within an owner's repos:

```bash
loom github repo "loom" --owner aadelb
```

Search code in a specific repo:

```bash
loom github code "ssrf" --repo aadelb/loom
```

Search issues:

```bash
loom github issues "bug" --owner anthropics --repo anthropic-sdk
```

Recently updated repositories:

```bash
loom github repo "web scraping" --sort updated --order desc
```

### Exit Codes

- `0` — Search successful
- `1` — GitHub CLI not installed or authentication failed
- `2` — Invalid query or arguments
- `3` — GitHub API rate limit

---

## loom camoufox

Fetch a URL using Camoufox stealth browser (TLS fingerprint spoofing).

### Synopsis

```text
loom camoufox <URL> [OPTIONS]
```

### Description

Scrape a URL using Camoufox, which spoofs TLS fingerprints and HTTP headers to bypass bot detection. Ideal for Cloudflare, Akamai, and other anti-bot services.

### Flags

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `<URL>` | string | *required* | URL to scrape |
| `--session <NAME>` | string | — | Use persistent browser session |
| `--screenshot` | flag | false | Include a screenshot |
| `--timeout <SECS>` | int | 120 | Request timeout |
| `--wait-for <SELECTOR>` | string | — | CSS selector to wait for |
| (all fetch options) | — | — | `--header`, `--proxy`, `--cookie`, etc. |

### Examples

Bypass Cloudflare:

```bash
loom camoufox https://cloudflare-protected.com
```

With persistent session:

```bash
loom camoufox https://huggingface.co --session my-hf
```

Wait for dynamic content:

```bash
loom camoufox https://example.com/spa --wait-for ".content"
```

Take screenshot:

```bash
loom camoufox https://example.com --screenshot
```

With custom headers:

```bash
loom camoufox https://example.com \
  --header "User-Agent: Mozilla/5.0"
```

### Exit Codes

- `0` — Success
- `1` — Browser error or network failure
- `2` — URL validation failed
- `3` — Timeout

---

## loom botasaurus

Fetch a URL using Botasaurus anti-detection library.

### Synopsis

```text
loom botasaurus <URL> [OPTIONS]
```

### Description

Scrape a URL using Botasaurus, a Python anti-detection library that provides maximum stealth through browser automation, request randomization, and behavioral spoofing. Use when Camoufox isn't sufficient.

### Flags

Same as `loom camoufox`.

### Examples

Maximum stealth scraping:

```bash
loom botasaurus https://heavily-protected.com
```

With session:

```bash
loom botasaurus https://example.com --session my-session
```

### Exit Codes

- `0` — Success
- `1` — Browser error
- `3` — Timeout

---

## loom session

Manage persistent browser sessions for login-walled content.

### Synopsis

```text
loom session <ACTION> [ARGS] [OPTIONS]
```

### Description

Manage persistent browser sessions. Sessions preserve cookies, localStorage, and authentication state across multiple requests. Useful for authenticated APIs and gated content.

### Actions

#### session open

Open a new browser session.

```text
loom session open <NAME> [OPTIONS]
```

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `<NAME>` | string | *required* | Session name (used in subsequent `fetch` calls) |
| `--browser <BROWSER>` | string | `camoufox` | Browser: `camoufox`, `chromium`, `firefox` |
| `--login-url <URL>` | string | — | URL to navigate to for login flow |
| `--login-script <FILE>` | string | — | JavaScript file to run for auto-login |
| `--ttl <SECS>` | int | `3600` | Session timeout in seconds |

Examples:

```bash
# Open a basic session
loom session open huggingface

# Open with login flow (headful browser)
loom session open huggingface \
  --login-url https://huggingface.co/login

# With auto-login script
loom session open my-session \
  --login-url https://example.com/login \
  --login-script ./login.js

# 30-minute TTL
loom session open long-session --ttl 1800
```

#### session list

List all active sessions.

```text
loom session list
```

Shows session name, creation time, last-used time, and TTL.

#### session close

Close a session and delete its profile directory.

```text
loom session close <NAME>
```

Example:

```bash
loom session close huggingface
```

---

## loom config

View and modify runtime configuration.

### Synopsis

```text
loom config <ACTION> [ARGS]
```

### Description

Get, set, or list configuration values. Changes persist to disk and take effect immediately (no restart required).

### Actions

#### config get

Show all or a specific config value.

```text
loom config get [KEY]
```

Examples:

```bash
# Show all config
loom config get

# Show one key
loom config get SPIDER_CONCURRENCY
```

#### config set

Set a config key.

```text
loom config set <KEY> <VALUE>
```

Examples:

```bash
# Increase spider concurrency
loom config set SPIDER_CONCURRENCY 10

# Increase request timeout
loom config set EXTERNAL_TIMEOUT_SECS 60

# Set default search provider
loom config set DEFAULT_SEARCH_PROVIDER tavily
```

#### config list

Show all configurable keys with descriptions and allowed ranges.

```text
loom config list
```

---

## loom cache

Manage the response cache.

### Synopsis

```text
loom cache <ACTION> [OPTIONS]
```

### Description

View cache statistics and clear old or all entries.

### Actions

#### cache stats

Show cache size, entry count, oldest entry, and TTL.

```text
loom cache stats
```

#### cache clear

Clear cache entries.

```text
loom cache clear [OPTIONS]
```

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--older-than-days <N>` | int | — | Remove entries older than N days (clear all if omitted) |
| `--dry-run` | flag | false | Show what would be deleted without deleting |

Examples:

```bash
# Clear entire cache
loom cache clear

# Remove old entries (older than 30 days)
loom cache clear --older-than-days 30

# Preview what would be deleted
loom cache clear --dry-run
```

---

## loom llm

Call LLM tools directly from the CLI.

### Synopsis

```text
loom llm <ACTION> [TEXT] [OPTIONS]
```

### Description

Call LLM tools for text processing, extraction, and generation. Input can be provided as an argument, via `--file`, or via stdin.

### Actions

#### llm summarize

Summarize text.

```text
loom llm summarize <TEXT> [OPTIONS]
```

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--file <FILE>` | string | — | Read input from file instead of argument |
| `--max-tokens <N>` | int | `200` | Max summary length |
| `--model <MODEL>` | string | — | LLM model (default: auto-select) |

Examples:

```bash
loom llm summarize "Long document text here" --max-tokens 300
loom llm summarize --file document.txt
echo "Text to summarize" | loom llm summarize
```

#### llm extract

Extract structured data using schema.

```text
loom llm extract <TEXT> --schema <SCHEMA>
```

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--schema <SCHEMA>` | string | *required* | JSON schema describing fields to extract |
| `--file <FILE>` | string | — | Read input from file |

Example schema:

```json
{
  "name": "string",
  "age": "number",
  "email": "string"
}
```

Usage:

```bash
loom llm extract "John Doe, 30 years old, john@example.com" \
  --schema '{"name":"string","age":"number","email":"string"}'
```

#### llm classify

Classify text into categories.

```text
loom llm classify <TEXT> --labels <LABELS>
```

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--labels <LABELS>` | string | *required* | Comma-separated category labels |
| `--file <FILE>` | string | — | Read input from file |

Examples:

```bash
loom llm classify "This product is amazing!" --labels "positive,negative,neutral"
loom llm classify --file review.txt --labels "spam,ham"
```

#### llm translate

Translate text to a target language.

```text
loom llm translate <TEXT> --to <LANG>
```

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--to <LANG>` | string | `en` | Target language code |
| `--from <LANG>` | string | — | Source language (auto-detected if omitted) |
| `--file <FILE>` | string | — | Read input from file |

Examples:

```bash
loom llm translate "Hello world" --to es
loom llm translate --file document_ar.txt --from ar --to en
```

#### llm expand

Expand a query into multiple variations.

```text
loom llm expand <QUERY> [OPTIONS]
```

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--n <COUNT>` | int | `5` | Number of variations |
| `--file <FILE>` | string | — | Read input from file |

Examples:

```bash
loom llm expand "what is prompt injection"
loom llm expand "SSRF vulnerabilities" --n 10
```

#### llm answer

Answer a question using provided sources.

```text
loom llm answer <QUESTION> --sources <FILE>
```

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--sources <FILE>` | string | *required* | Text file with one URL or document per line |
| `--max-tokens <N>` | int | `800` | Max answer length |

Sources file format:

```
https://example.com/article1
https://example.com/article2
https://example.com/article3
```

Usage:

```bash
loom llm answer "What is SSRF?" --sources sources.txt
```

#### llm embed

Generate embeddings for text.

```text
loom llm embed <TEXT>
```

Returns embedding vectors for semantic search or similarity.

#### llm chat

Interactive LLM conversation.

```text
loom llm chat [OPTIONS]
```

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--model <MODEL>` | string | — | LLM model |
| `--temperature <TEMP>` | float | `0.2` | Creativity (0.0-2.0) |

Read prompt from stdin:

```bash
echo "What is AI safety?" | loom llm chat
```

---

## loom journey-test

Run a deterministic end-to-end journey test exercising all 23 tools.

### Synopsis

```text
loom journey-test [OPTIONS]
```

### Description

Execute a comprehensive journey through all Loom tools: fetch, spider, search, deep, markdown, GitHub search, stealth scrapers, sessions, config, cache, and LLM tools. Generates a detailed markdown report.

### Flags

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--topic <TOPIC>` | string | `llama model family` | Research topic to use in tests |
| `--live` | flag | false | Run against real network (default: mocked fixtures) |
| `--record` | flag | false | Record screenshots during journey |
| `--fixtures <DIR>` | string | `tests/fixtures/journey` | Fixtures directory for mocked mode |
| `--out <DIR>` | string | `./journey-out` | Output directory for report |

### Examples

Run with mocked fixtures (fast, ~30 seconds):

```bash
loom journey-test
```

Run with custom topic:

```bash
loom journey-test --topic "SSRF vulnerabilities"
```

Run against live network:

```bash
loom journey-test --live
```

Record screenshots:

```bash
loom journey-test --live --record
```

### Exit Codes

- `0` — All journey steps passed
- `1` — One or more steps failed

### Output

Generates `journey-out/report.md` with:
- Summary (passed/failed steps)
- Detailed results for each tool
- Timings
- Error messages (if any)

---

## loom repl

Interactive REPL shell for exploratory research.

### Synopsis

```text
loom repl [OPTIONS]
```

### Description

Start an interactive shell with command history and tab completion. All commands are available without the `loom` prefix.

### Flags

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--server <URL>` | string | `http://127.0.0.1:8787/mcp` | MCP server URL |

### Examples

Start the REPL:

```bash
loom repl
```

Example session:

```
loom> fetch https://httpbin.org/html
[fetched 1024 bytes]

loom> search "prompt injection" --provider exa
[10 results returned]

loom> config get SPIDER_CONCURRENCY
5

loom> help
[shows available commands]

loom> exit
```

### Available Commands in REPL

- `fetch <url>` — Fetch a single URL
- `spider <file>` — Bulk fetch from file
- `markdown <url>` — Extract markdown
- `search <query>` — Search the web
- `deep <query>` — Deep research
- `github [repo|code|issues] <query>` — Search GitHub
- `camoufox <url>` — Stealth scraping
- `botasaurus <url>` — Bot scraping
- `session [open|list|close]` — Manage sessions
- `config [get|set|list]` — View/set config
- `cache [stats|clear]` — Cache management
- `llm [action]` — LLM tools
- `journey-test` — Run journey
- `help` — Show this help
- `exit` or `quit` — Exit REPL

---

## Common Workflows

### Fetch and Summarize

Fetch a page and generate a summary:

```bash
content=$(loom fetch https://arxiv.org/abs/2401.12345 --return-format text)
loom llm summarize --max-tokens 300 <<< "$content"
```

### Search, Fetch, and Answer

Search for URLs, fetch them, and synthesize an answer:

```bash
# One-shot workflow
loom deep "what is prompt injection" --depth 2

# Or step by step
urls=$(loom search "prompt injection" --n 5 --json | jq -r '.results[].url')
echo "$urls" > tmp_urls.txt
loom spider tmp_urls.txt --concurrency 3
loom llm answer "Summarize prompt injection" --sources tmp_urls.txt
```

### Bulk Scraping with Sessions

Open an authenticated session and fetch multiple pages:

```bash
# Open login session
loom session open huggingface --login-url https://huggingface.co/login

# Fetch multiple pages
while read url; do
  echo "Fetching $url..."
  loom fetch "$url" --session huggingface --return-format text
done < model_urls.txt

# Close when done
loom session close huggingface
```

### Monitor and Tune Configuration

Check current config and adjust as needed:

```bash
loom config get
loom config set SPIDER_CONCURRENCY 10
loom spider urls.txt --concurrency 10
loom config set SPIDER_CONCURRENCY 5  # reset
```

### Cache Management

Monitor and maintain the cache:

```bash
loom cache stats
loom cache clear --older-than-days 30 --dry-run
loom cache clear --older-than-days 30
```

---

## Exit Codes

All `loom` commands use these exit codes:

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Tool error (network, parsing, etc.) |
| `2` | Validation error (invalid arguments, file not found, SSRF) |
| `3` | Server unreachable or timeout |

---

## Environment Variables

Configure behavior with environment variables:

```bash
export LOOM_SERVER=http://remote.example.com:8787/mcp
export LOOM_TIMEOUT=60
loom fetch https://example.com
```

See [docs/installation.md](installation.md) for complete environment variable reference.
