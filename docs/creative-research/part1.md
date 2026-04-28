# Loom Tools Reference

Complete documentation for all 94 registered MCP tools.

---

## fetch_youtube_transcript

Extract auto-generated subtitles from a YouTube video (free).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | - | YouTube video URL |
| language | str | `en` | ISO 639-1 language code (e.g., 'en', 'ar', 'es') |

**Returns:** `{"transcript": "...", "language": "en", "url": "...", "error": "..." (optional)}`
**Cost:** FREE
**Rate Limit:** None (limited by YouTube rate limits)

---

## find_similar_exa

Find pages semantically similar to a given URL using Exa semantic search.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | - | Target URL to find similar pages for |
| n | int | `10` | Number of similar results to return (1-50) |

**Returns:** `{"url": "...", "results": [{"url": "...", "title": "...", "score": 0.85}], "provider": "exa"}`
**Cost:** PAID (EXA_API_KEY)
**Rate Limit:** Exa standard rate limit

---

## research_ai_detect

Detect whether text is likely AI-generated using multiple heuristics.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| text | str | - | Text to analyze |
| max_cost_usd | float | `0.02` | Max cost for LLM analysis |

**Returns:** `{"text_sample": "...", "ai_probability": 0.85, "confidence": 0.92, "indicators": [...]}`
**Cost:** PAID (varies by LLM provider, $0.02 default budget)
**Rate Limit:** LLM provider limits

---

## research_botasaurus

Fetch a URL using Botasaurus stealth browser (second stealth escalation).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | - | URL to fetch |
| session | str \| None | `None` | Persistent session name (for API compatibility) |
| screenshot | bool | `False` | Capture base64-encoded screenshot |
| timeout | int \| None | `None` | Operation timeout in seconds |

**Returns:** `{"url": "...", "title": "...", "html": "...", "text": "...", "screenshot": "..." (optional), "error": "..." (optional)}`
**Cost:** FREE
**Rate Limit:** None (limited by local browser resources)

---

## research_breach_check

Check if an email appears in known data breaches using HaveIBeenPwned API.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| email | str | - | Email address to check |

**Returns:** `{"email": "...", "breaches_found": 0, "breaches": [{"name": "...", "date": "2020-01-01", "data_classes": [...]}], "api_available": true}`
**Cost:** FREE (requires HIBP_API_KEY for API access)
**Rate Limit:** HaveIBeenPwned rate limits

---

## research_cache_clear

Remove cache entries older than N days.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| older_than_days | int \| None | `None` | Delete entries older than this many days (uses CACHE_TTL_DAYS from config if None) |

**Returns:** `{"deleted_count": 42, "freed_mb": 15.3, "older_than_days": 30}`
**Cost:** FREE
**Rate Limit:** None (local operation)

---

## research_cache_stats

Return cache statistics (size, entry count, age range).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| (none) | - | - | No parameters |

**Returns:** `{"size_mb": 125.4, "entry_count": 342, "oldest": "2025-01-01T10:30:00Z", "newest": "2025-04-27T15:45:00Z", "cache_dir": "/home/user/.cache/loom"}`
**Cost:** FREE
**Rate Limit:** None (local operation)

---

## research_camoufox

Fetch a URL using Camoufox stealth browser (anti-detection Firefox).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | - | URL to fetch |
| session | str \| None | `None` | NOT USED (for API compatibility) |
| screenshot | bool | `False` | Include base64-encoded screenshot |
| timeout | int \| None | `None` | Operation timeout in seconds |

**Returns:** `{"url": "...", "title": "...", "html": "...", "text": "...", "screenshot": "..." (optional), "error": "..." (optional)}`
**Cost:** FREE
**Rate Limit:** None (limited by local browser resources)

---

## research_cert_analyze

Extract SSL/TLS certificate information from a remote server.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| hostname | str | - | Hostname or IP address |
| port | int | `443` | Port number (typically 443 for HTTPS) |

**Returns:** `{"hostname": "...", "port": 443, "subject": {...}, "issuer": {...}, "valid_from": "2024-01-01", "valid_to": "2025-01-01", "cn": "example.com"}`
**Cost:** FREE
**Rate Limit:** None (network lookup only)

---

## research_cipher_mirror

Monitor paste sites for leaked credentials and model weights.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Search query for paste sites |
| n | int | `10` | Max number of results |
| entropy_threshold | float | `0.6` | Entropy threshold for credential detection (0.0-1.0) |
| max_cost_usd | float | `0.1` | Max cost for content analysis |

**Returns:** `{"query": "...", "pastes_found": 5, "pastes": [{"url": "...", "title": "...", "entropy": 0.92}], "credentials_detected": true}`
**Cost:** PAID (varies, $0.1 default budget)
**Rate Limit:** Depends on paste site providers

---

## research_citation_graph

Build a citation graph from a seed paper query (academic research).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| paper_query | str | - | Paper title or arxiv ID |
| depth | int | `1` | Graph depth (1-3, how many citation hops) |
| max_papers | int | `10` | Max papers to include in graph |

**Returns:** `{"seed_paper": {...}, "citing_papers": [...], "cited_by_papers": [...], "graph_size": 15}`
**Cost:** FREE (uses arxiv)
**Rate Limit:** None (arxiv public API)

---

## research_community_sentiment

Get practitioner sentiment from HackerNews and Reddit on a topic.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Topic to analyze |
| n | int | `5` | Number of top posts to analyze |

**Returns:** `{"query": "...", "hackernews_sentiment": "positive", "reddit_sentiment": "mixed", "posts": [{"source": "hn", "title": "...", "score": 150}]}`
**Cost:** FREE
**Rate Limit:** None (public APIs)

---

## research_config_get

Return current runtime config. If key is given, return only that entry.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| key | str \| None | `None` | Specific config key to return (e.g., 'DEFAULT_SEARCH_PROVIDER') |

**Returns:** `{"key": "value", ...}` or `{"key": "value"}` if specific key requested
**Cost:** FREE
**Rate Limit:** None (local operation)

---

## research_config_set

Validated runtime config update. Returns error dict on failure.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| key | str | - | Config key to set (must exist in schema) |
| value | Any | - | New value (validated against schema) |

**Returns:** `{"key": "...", "value": "...", "previous_value": "..."}` or `{"error": "Invalid key or value"}`
**Cost:** FREE
**Rate Limit:** None (local operation)

---

## research_consensus

Run query across all search engines, score results by consensus.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Search query |
| providers | list[str] \| None | `None` | List of providers (exa, tavily, brave, ddgs, etc.); uses all if None |
| n | int | `10` | Results per provider |

**Returns:** `{"query": "...", "results": [{"url": "...", "title": "...", "consensus_score": 0.85}], "provider_count": 4}`
**Cost:** PAID (varies by providers used)
**Rate Limit:** Depends on providers

---

## research_convert_document

Convert documents (PDF, DOCX, HTML, etc.) to markdown or text.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | - | Document URL or file path |
| output_format | str | `markdown` | Output format: 'markdown' or 'text' |

**Returns:** `{"url": "...", "format": "markdown", "content": "...", "pages": 5, "error": "..." (optional)}`
**Cost:** FREE
**Rate Limit:** None (local conversion, network fetch for URL)

---

## research_curriculum

Generate a multi-level learning path from ELI5 to PhD.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| topic | str | - | Learning topic |
| max_cost_usd | float | `0.1` | Max cost for LLM generation |

**Returns:** `{"topic": "...", "levels": [{"level": "eli5", "content": "..."}, {"level": "phd", "content": "..."}], "cost_usd": 0.05}`
**Cost:** PAID (varies, $0.1 default budget)
**Rate Limit:** LLM provider limits

---

## research_cve_detail

Get detailed information for a specific CVE ID.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| cve_id | str | - | CVE ID (e.g., 'CVE-2024-1234') |

**Returns:** `{"cve_id": "CVE-2024-1234", "description": "...", "cvss_score": 8.5, "affected_software": [...]}`
**Cost:** FREE
**Rate Limit:** None (NVD API, rate limited)

---

## research_cve_lookup

Search CVE database using NVD API (free, rate limited).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | CVE search query (keyword or ID) |
| limit | int | `10` | Max results (1-50) |

**Returns:** `{"query": "...", "results": [{"cve_id": "CVE-2024-1234", "score": 8.5}], "total": 150}`
**Cost:** FREE
**Rate Limit:** NVD API rate limits

---

## research_dead_drop_scanner

Probe ephemeral .onion sites and capture content with reuse detection.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| urls | list[str] | - | List of .onion URLs to monitor |
| interval_minutes | int | `5` | Check interval in minutes |

**Returns:** `{"urls_scanned": 5, "new_content": [{"url": "...", "content_hash": "...", "first_seen": "2025-04-27T..."}], "reused_hashes": 2}`
**Cost:** FREE
**Rate Limit:** None (local operation, Tor network limits)

---

## research_deception_detect

Detect deceptive or fraudulent content using linguistic cues.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| text | str | - | Text to analyze for deception indicators |

**Returns:** `{"text_sample": "...", "deception_score": 0.75, "indicators": ["urgency", "emotional_appeal"], "confidence": 0.82}`
**Cost:** FREE
**Rate Limit:** None (local NLP analysis)

---

## research_deep

Full-pipeline deep research using all available tools.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Research query |
| depth | int | `2` | Recursion depth for search expansion (1-3) |
| include_domains | list[str] \| None | `None` | Whitelist domains (e.g., ['github.com']) |
| exclude_domains | list[str] \| None | `None` | Blacklist domains (e.g., ['twitter.com']) |
| start_date | str \| None | `None` | ISO date filter (yyyy-mm-dd) |
| end_date | str \| None | `None` | ISO date filter (yyyy-mm-dd) |
| language | str \| None | `None` | Language hint (ISO 639-1) |
| provider_config | dict \| None | `None` | Provider-specific config (e.g., `{"exa": {...}}`) |
| search_providers | list[str] \| None | `None` | Providers to use (auto-detects if None) |
| expand_queries | bool | `True` | Generate related queries via LLM |
| extract | bool | `True` | Extract structured data from results |
| synthesize | bool | `True` | Generate synthesis answer |
| include_github | bool | `True` | Include GitHub search results |
| include_community | bool | `False` | Include HN + Reddit sentiment |
| include_red_team | bool | `False` | Generate counter-arguments |
| include_misinfo_check | bool | `False` | Stress-test claims against sources |
| max_cost_usd | float \| None | `None` | Cost cap for LLM operations |

**Returns:** `{"query": "...", "synthesis": "...", "sources": [...], "github_repos": [...], "cost_usd": 0.25, "execution_time_secs": 45.2}`
**Cost:** PAID (varies, depends on sub-tools used)
**Rate Limit:** Aggregate of all sub-tools

---

## research_detect_language

Detect the language of text content (free, no API key required).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| text | str | - | Text to analyze |

**Returns:** `{"text_sample": "...", "language": "en", "language_name": "English", "confidence": 0.98}`
**Cost:** FREE
**Rate Limit:** None (local library)

---

## research_dns_lookup

DNS lookup for domain records (A, AAAA, MX, NS, TXT, CNAME, etc.).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| domain | str | - | Domain name (e.g., 'example.com') |
| record_types | list[str] \| None | `None` | Record types to fetch (A, AAAA, MX, NS, TXT, CNAME); fetches all if None |

**Returns:** `{"domain": "example.com", "A": ["192.0.2.1"], "MX": [{"priority": 10, "host": "mail.example.com"}], "error": "..." (optional)}`
**Cost:** FREE
**Rate Limit:** None (system DNS resolver)

---

## research_email_report

Send research results via Gmail SMTP.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| to | str | - | Recipient email address |
| subject | str | - | Email subject |
| body | str | - | Email body text |
| html | bool | `False` | Treat body as HTML |

**Returns:** `{"to": "...", "subject": "...", "sent": true, "message_id": "..."}`
**Cost:** FREE (requires SMTP_USER and SMTP_APP_PASSWORD env vars)
**Rate Limit:** Gmail rate limits

---

## research_exif_extract

Extract EXIF metadata from image URLs or file paths.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url_or_path | str | - | Image URL or local file path |

**Returns:** `{"url": "...", "exif": {"Make": "Canon", "Model": "EOS R5", "DateTime": "2024-01-15T10:30:00"}, "gps": {"latitude": 51.5074, "longitude": -0.1278}}`
**Cost:** FREE
**Rate Limit:** None (local file or network fetch)

---

## research_fetch

Fetch a URL with configurable strategy (HTTP, stealth, or dynamic).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | - | URL to fetch |
| mode | str | `stealthy` | Fetch mode: 'http' (basic), 'stealthy' (custom headers), 'dynamic' (Playwright) |
| max_chars | int | `200000` | Max characters to return (hard cap) |
| solve_cloudflare | bool | `True` | Auto-escalate if Cloudflare challenge detected |
| headers | dict \| None | `None` | Custom HTTP headers |
| user_agent | str \| None | `None` | Override User-Agent header |
| proxy | str \| None | `None` | Proxy URL (http://, https://, socks5://, socks5h://) |
| cookies | dict \| None | `None` | Cookies dict |
| accept_language | str | `en-US,en;q=0.9,ar;q=0.8` | Accept-Language header |
| wait_for | str \| None | `None` | CSS selector to wait for before returning |
| return_format | str | `text` | Return format: 'text', 'html', 'json', 'screenshot' |
| timeout | int \| None | `None` | Operation timeout (1-120 seconds) |
| bypass_cache | bool | `False` | Force refetch, skip cache |
| auto_escalate | bool \| None | `None` | Auto-escalate on failure (if None, uses config) |

**Returns:** `{"url": "...", "status_code": 200, "text": "...", "html": "...", "title": "...", "error": "..." (optional), "elapsed_ms": 1250}`
**Cost:** FREE
**Rate Limit:** None (depends on target website)

---

## research_find_experts

Find top experts on a topic by cross-referencing multiple sources.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Topic to find experts for |
| n | int | `5` | Number of experts to return |

**Returns:** `{"query": "...", "experts": [{"name": "...", "field": "...", "affiliations": [...], "citations": 2345}]}`
**Cost:** PAID (varies by search/LLM providers)
**Rate Limit:** Depends on providers used

---

## research_forum_cortex

Analyze dark web forum discourse on a topic.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| topic | str | - | Topic to analyze in forums |
| n | int | `5` | Number of posts to analyze |
| max_cost_usd | float | `0.1` | Max cost for LLM analysis |

**Returns:** `{"topic": "...", "posts": [{"forum": "...", "author": "...", "content": "...", "sentiment": "neutral"}], "themes": ["..."]}`
**Cost:** PAID (varies, $0.1 default budget)
**Rate Limit:** Forum crawler limits, LLM provider limits

---

## research_geoip_local

Look up geographic information for an IP address using local MaxMind database.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ip | str | - | IP address (IPv4 or IPv6) |

**Returns:** `{"ip": "203.0.113.45", "country": "US", "city": "New York", "latitude": 40.7128, "longitude": -74.0060, "isp": "Example ISP"}`
**Cost:** FREE
**Rate Limit:** None (local database lookup)

---

## research_ghost_weave

Build temporal hyperlink graph of .onion hidden services.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| seed_url | str | - | Starting .onion URL |
| depth | int | `1` | Graph depth (1-3 hops) |
| max_pages | int | `20` | Max pages to crawl |

**Returns:** `{"seed": "...", "pages": [{"url": "...", "title": "...", "links": [...]}], "graph_size": 15}`
**Cost:** FREE
**Rate Limit:** None (Tor network limits)

---

## research_github

Search GitHub via public REST API (repos, code, issues).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| kind | str | - | Search type: 'repo' \| 'code' \| 'issues' |
| query | str | - | Search query (GitHub syntax) |
| sort | str | `stars` | Sort field: 'stars', 'forks', 'updated' |
| order | str | `desc` | Sort order: 'asc' \| 'desc' |
| limit | int | `20` | Max results (1-100) |
| language | str \| None | `None` | Programming language filter |
| owner | str \| None | `None` | Repository owner (user/org) |
| repo | str \| None | `None` | Repository name filter |

**Returns:** `{"query": "...", "results": [{"url": "...", "title": "...", "stars": 1250}], "total": 5432}`
**Cost:** FREE (uses public GitHub API; optional GITHUB_TOKEN for higher rate limits)
**Rate Limit:** GitHub API rate limits (60 req/hr unauthenticated, 5000 req/hr authenticated)

---

## research_github_readme

Fetch a repository's README content.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| owner | str | - | Repository owner (username or org) |
| repo | str | - | Repository name |

**Returns:** `{"owner": "...", "repo": "...", "readme": "# Project\n...", "format": "markdown", "error": "..." (optional)}`
**Cost:** FREE
**Rate Limit:** GitHub API rate limits

---

## research_github_releases

Fetch recent releases for a repository.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| owner | str | - | Repository owner (username or org) |
| repo | str | - | Repository name |
| limit | int | `5` | Max releases to return (1-100) |

**Returns:** `{"owner": "...", "repo": "...", "releases": [{"tag": "v1.0.0", "date": "2024-01-15", "url": "..."}]}`
**Cost:** FREE
**Rate Limit:** GitHub API rate limits

---

## research_health_check

Return server health status for monitoring.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| (none) | - | - | No parameters |

**Returns:** `{"status": "healthy", "timestamp": "2025-04-27T...", "uptime_seconds": 12345, "tools_registered": 94}`
**Cost:** FREE
**Rate Limit:** None (local operation)

---

## research_image_analyze

Analyze images using Google Cloud Vision API.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| image_url | str | - | Image URL to analyze |
| features | list[str] \| None | `None` | Vision features (label_detection, text_detection, face_detection, etc.); analyzes all if None |
| max_results | int | `10` | Max results per feature |

**Returns:** `{"url": "...", "labels": [{"description": "cat", "confidence": 0.95}], "text": "...", "faces": [...]}`
**Cost:** PAID (requires GOOGLE_CLOUD_VISION_API_KEY)
**Rate Limit:** Google Cloud Vision API rate limits

---

## research_ip_geolocation

Get geolocation for an IP address (lightweight, free).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ip | str | - | IP address (IPv4 or IPv6) |

**Returns:** `{"ip": "8.8.8.8", "country": "US", "country_code": "US", "city": "Mountain View", "latitude": 37.386, "longitude": -122.084}`
**Cost:** FREE
**Rate Limit:** None (free geolocation service)

---

## research_ip_reputation

Check IP reputation using free APIs (no API key needed).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ip | str | - | IP address to check |

**Returns:** `{"ip": "...", "reputation_score": 0.85, "is_malicious": false, "threat_types": ["..."], "sources": [...]}`
**Cost:** FREE
**Rate Limit:** None (aggregated free services)

---

## research_list_notebooks

List all Joplin notebooks.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| (none) | - | - | No parameters |

**Returns:** `{"notebooks": [{"id": "...", "title": "Research", "note_count": 42}]}`
**Cost:** FREE (requires JOPLIN_TOKEN env var)
**Rate Limit:** Joplin API rate limits

---

## research_llm_answer

Synthesize an answer from multiple sources with citations.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| question | str | - | Question to answer |
| sources | list[dict] | - | List of sources (each with 'url', 'title', 'content') |
| max_tokens | int | `800` | Max tokens in response |
| style | str | `cited` | Response style: 'cited' (with citations), 'summary' (no citations) |
| model | str | `auto` | LLM model: 'auto' (cascade), 'openai', 'anthropic', 'nvidia', 'groq', 'vllm' |
| provider_override | str \| None | `None` | Force specific provider |

**Returns:** `{"question": "...", "answer": "...", "sources": [{"url": "...", "citation_count": 2}], "cost_usd": 0.005}`
**Cost:** PAID (varies by LLM provider, ~$0.01 per answer)
**Rate Limit:** LLM provider cascade limits

---

## research_llm_chat

Raw pass-through to LLM chat endpoint.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| messages | list[dict] | - | Chat messages (each with 'role' and 'content') |
| model | str | `auto` | Model: 'auto' (cascade), 'openai', 'anthropic', 'nvidia', 'groq', 'vllm' |
| max_tokens | int | `1500` | Max output tokens |
| temperature | float | `0.2` | Sampling temperature (0.0-1.0) |
| response_format | dict \| None | `None` | Response format schema (JSON mode) |
| provider_override | str \| None | `None` | Force specific provider |

**Returns:** `{"message": {"role": "assistant", "content": "..."}, "model": "gpt-4o", "tokens": {"input": 50, "output": 120}, "cost_usd": 0.012}`
**Cost:** PAID (varies by provider and tokens)
**Rate Limit:** LLM provider limits

---

## research_llm_classify

Classify text into one or more categories from an allow-list.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| text | str | - | Text to classify |
| labels | list[str] | - | Allowed category labels |
| multi_label | bool | `False` | Allow multiple labels per text |
| model | str | `auto` | LLM model (auto, openai, anthropic, nvidia, groq, vllm) |
| provider_override | str \| None | `None` | Force specific provider |

**Returns:** `{"text_sample": "...", "labels": ["positive", "urgent"], "confidence": 0.92, "cost_usd": 0.003}`
**Cost:** PAID (varies, ~$0.003 per classification)
**Rate Limit:** LLM provider limits

---

## research_llm_embed

Generate embeddings for semantic similarity / deduping.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| texts | list[str] | - | List of texts to embed |
| model | str | `auto` | Embedding model (auto, openai, anthropic, nvidia, groq, vllm) |
| provider_override | str \| None | `None` | Force specific provider |

**Returns:** `{"embeddings": [[0.123, -0.456, ...], [...]], "model": "text-embedding-3-small", "dimension": 1536, "cost_usd": 0.0002}`
**Cost:** PAID (varies, ~$0.02 per 1M tokens)
**Rate Limit:** LLM provider embedding limits

---

## research_llm_extract

Extract structured data from text using schema.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| text | str | - | Text to extract from |
| schema | dict | - | JSON schema defining output structure |
| model | str | `auto` | LLM model (auto, openai, anthropic, nvidia, groq, vllm) |
| provider_override | str \| None | `None` | Force specific provider |

**Returns:** `{"text_sample": "...", "extracted": {...}, "cost_usd": 0.005}`
**Cost:** PAID (varies, ~$0.01 per extraction)
**Rate Limit:** LLM provider limits

---

## research_llm_query_expand

Expand a query into n related queries for broader search.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Original search query |
| n | int | `5` | Number of expanded queries to generate |
| model | str | `auto` | LLM model (auto, openai, anthropic, nvidia, groq, vllm) |
| provider_override | str \| None | `None` | Force specific provider |

**Returns:** `{"original": "machine learning", "expanded": ["deep learning", "neural networks", "AI algorithms", "statistical learning", "pattern recognition"], "cost_usd": 0.004}`
**Cost:** PAID (varies, ~$0.004 per expansion)
**Rate Limit:** LLM provider limits

---

## research_llm_summarize

Summarize text using an LLM.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| text | str | - | Text to summarize |
| max_tokens | int | `400` | Max output tokens |
| model | str | `auto` | LLM model (auto, openai, anthropic, nvidia, groq, vllm) |
| language | str | `en` | Language hint (ISO 639-1) |
| provider_override | str \| None | `None` | Force specific provider |

**Returns:** `{"text_sample": "...", "summary": "...", "compression_ratio": 0.25, "cost_usd": 0.008}`
**Cost:** PAID (varies, ~$0.01 per summary)
**Rate Limit:** LLM provider limits

---

## research_llm_translate

Translate text between languages (Arabic ↔ English first-class).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| text | str | - | Text to translate |
| target_lang | str | `en` | Target language (ISO 639-1) |
| source_lang | str \| None | `None` | Source language (auto-detected if None) |
| model | str | `auto` | LLM model (auto, openai, anthropic, nvidia, groq, vllm) |
| provider_override | str \| None | `None` | Force specific provider |

**Returns:** `{"original": "...", "translated": "...", "source_lang": "ar", "target_lang": "en", "cost_usd": 0.006}`
**Cost:** PAID (varies, ~$0.01 per translation)
**Rate Limit:** LLM provider limits

---

## research_markdown

Extract clean LLM-ready markdown via Crawl4AI (with optional CSS subtree).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| url | str | - | Target URL |
| bypass_cache | bool | `False` | Force refetch |
| css_selector | str \| None | `None` | Extract only this CSS subtree before markdown |
| js_before_scrape | str \| None | `None` | Small JS to execute before scraping (max 2KB) |
| screenshot | bool | `False` | Capture screenshot (writes to cache/screenshots/) |
| remove_selectors | list[str] \| None | `None` | CSS selectors to remove before extraction |
| headers | dict \| None | `None` | Custom HTTP headers |
| user_agent | str \| None | `None` | Override User-Agent |
| proxy | str \| None | `None` | Proxy URL |
| cookies | dict \| None | `None` | Cookies dict |
| accept_language | str | `en-US,en;q=0.9,ar;q=0.8` | Accept-Language header |
| timeout | int \| None | `None` | Operation timeout (capped) |
| extract_selector | str \| None | `None` | Alias for css_selector |
| wait_for | str \| None | `None` | CSS selector to wait for before scraping |

**Returns:** `{"url": "...", "title": "...", "markdown": "# Title\n...", "tool": "crawl4ai", "fetched_at": "2025-04-27T..."}`
**Cost:** FREE
**Rate Limit:** None (depends on target website)

---

<!-- Part 2 continues below -->
## Enrichment & Advanced Tools (Research Tools 47-93)

---

### research_markdown

Extract clean LLM-ready markdown from any URL using Crawl4AI with optional CSS selector and JavaScript execution.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | Target URL to extract markdown from |
| `bypass_cache` | bool | false | Skip cache read/write for this request |
| `css_selector` | str\|null | null | CSS selector to extract only specific subtree |
| `js_before_scrape` | str\|null | null | JavaScript code to execute before scraping (max 2KB) |
| `screenshot` | bool | false | Capture webpage screenshot |
| `remove_selectors` | list[str]\|null | null | CSS selectors to remove before extraction |
| `headers` | dict[str, str]\|null | null | Custom HTTP headers |
| `user_agent` | str\|null | null | Override User-Agent header |
| `proxy` | str\|null | null | HTTP or SOCKS5 proxy URL |
| `cookies` | dict[str, str]\|null | null | Request cookies |
| `accept_language` | str | en-US,en;q=0.9,ar;q=0.8 | Accept-Language header |
| `timeout` | int\|null | null | Request timeout in seconds (max 120) |
| `extract_selector` | str\|null | null | Alias for css_selector |
| `wait_for` | str\|null | null | CSS selector to wait for before scraping |

**Returns:** `{"url": "...", "title": "...", "markdown": "...", "tool": "crawl4ai", "fetched_at": "2026-04-28T..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_metrics

Return Prometheus-compatible metrics for Grafana dashboard integration. Tracks tool usage, errors, latency, and provider statistics.

**Returns:** `{"metrics": [...], "timestamp": "...", "version": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_misinfo_check

Stress test a claim by generating false variants and searching for sources to verify or refute it.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `claim` | str | - | Claim or statement to fact-check |
| `n_sources` | int | 5 | Number of sources to search for each variant |
| `max_cost_usd` | float | 0.05 | Maximum LLM cost budget for this request |

**Returns:** `{"claim": "...", "variants": [...], "findings": [...], "confidence": 0.85}`
**Cost:** PAID (varies with n_sources and LLM cascade)
**Rate Limit:** None

---

### research_multilingual

Search in multiple languages to discover cross-lingual information arbitrage and multilingual perspectives.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | - | Search query in any language |
| `languages` | list[str]\|null | null | Languages to search in (auto-detected if null, defaults to [en, es, fr, de, zh, ar]) |
| `n_per_lang` | int | 3 | Number of results per language |
| `max_cost_usd` | float | 0.1 | Maximum cost budget for search and translation |

**Returns:** `{"query": "...", "results": {"en": [...], "es": [...], ...}, "translations": [...]}`
**Cost:** PAID (multi-provider + translation)
**Rate Limit:** None

---

### research_network_persona

Analyze social network structure within forum data to identify influential nodes and community dynamics.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `posts` | list[dict[str, Any]] | - | Forum posts with author, content, and interaction metadata |
| `min_interactions` | int | 2 | Minimum interaction count to include a user in analysis |

**Returns:** `{"nodes": [...], "edges": [...], "communities": [...], "influence_scores": {...}}`
**Cost:** FREE
**Rate Limit:** None

---

### research_nmap_scan

Port scan a target using nmap to identify open ports and services.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target` | str | - | IP address or domain to scan |
| `ports` | str | 80,443,8080,8443 | Comma-separated port numbers or port ranges |
| `scan_type` | str | basic | Scan type: basic, aggressive, or stealth |

**Returns:** `{"target": "...", "ports": [...], "services": [...], "scan_duration_ms": 5432}`
**Cost:** FREE
**Rate Limit:** None

---

### research_ocr_extract

Extract text from images using Tesseract OCR engine.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url_or_path` | str | - | URL to image or local file path |
| `language` | str | eng | Language code for OCR (eng, fra, deu, spa, ara, etc.) |

**Returns:** `{"text": "...", "confidence": 0.92, "language": "eng", "processing_time_ms": 1234}`
**Cost:** FREE
**Rate Limit:** None

---

### research_onion_spectra

Classify .onion site content by language and safety category.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL of .onion site to classify |
| `fetch_content` | bool | true | Fetch and analyze site content |
| `max_chars` | int | 5000 | Maximum characters to analyze from fetched content |

**Returns:** `{"url": "...", "language": "en", "category": "marketplace\|forum\|news\|...", "confidence": 0.88, "warnings": [...]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_password_check

Check if a password appears in known password breaches using k-anonymity protocol.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `password` | str | - | Password to check |

**Returns:** `{"password": "***", "in_breaches": true, "breach_count": 12, "safe": false}`
**Cost:** FREE
**Rate Limit:** 4 req/min (k-anonymity compliant)

---

### research_pdf_extract

Extract text from a PDF URL with optional page range specification.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to PDF file |
| `pages` | str\|null | null | Page range (e.g., '1-5' or '1,3,5') |

**Returns:** `{"url": "...", "text": "...", "page_count": 42, "title": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_pdf_search

Search for text within a PDF file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to PDF file |
| `query` | str | - | Text to search for in PDF |

**Returns:** `{"url": "...", "query": "...", "matches": [...], "page_numbers": [3, 7, 12]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_persona_profile

Cross-platform persona reconstruction from text samples for deanonymization analysis.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `texts` | list[str] | - | Text samples from suspected same author |
| `metadata` | dict[str, Any]\|null | null | Optional metadata (timestamps, platforms, locations) |

**Returns:** `{"author_profile": {...}, "writing_style": {...}, "confidence": 0.76, "risk_factors": [...]}`
**Cost:** PAID (LLM analysis)
**Rate Limit:** None

---

### research_radicalization_detect

Monitor text for radicalization indicators using NLP classifiers.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Text to analyze |
| `context` | str\|null | null | Context or platform info (forum, dark web, etc.) |

**Returns:** `{"text": "...", "radicalization_score": 0.65, "indicators": [...], "severity": "medium"}`
**Cost:** PAID (LLM analysis)
**Rate Limit:** None

---

### research_red_team

Generate and search for counter-arguments to a claim for adversarial validation.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `claim` | str | - | Claim to challenge |
| `n_counter` | int | 3 | Number of counter-arguments to generate |
| `max_cost_usd` | float | 0.1 | Maximum LLM cost budget |

**Returns:** `{"claim": "...", "counter_arguments": [...], "supporting_urls": [...], "persuasiveness_score": 0.72}`
**Cost:** PAID (LLM + search)
**Rate Limit:** None

---

### research_rss_fetch

Fetch and parse an RSS or Atom feed.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to RSS/Atom feed |
| `max_items` | int | 20 | Maximum items to return |

**Returns:** `{"feed": {...}, "items": [...], "item_count": 18, "updated_at": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_rss_search

Search across multiple RSS feeds for items matching a query.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `urls` | list[str] | - | URLs of RSS/Atom feeds to search |
| `query` | str | - | Search query |
| `max_results` | int | 20 | Maximum results to return |

**Returns:** `{"query": "...", "results": [...], "feeds_searched": 5, "total_matches": 18}`
**Cost:** FREE
**Rate Limit:** None

---

### research_save_note

Create a note in Joplin via REST API for persistent research note-taking.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | str | - | Note title |
| `body` | str | - | Note content (supports Markdown) |
| `notebook` | str\|null | null | Target notebook name (defaults to Inbox) |

**Returns:** `{"id": "...", "title": "...", "created_at": "...", "notebook": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_screenshot

Take a screenshot of a webpage using Playwright headless browser.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to screenshot |
| `full_page` | bool | false | Capture full page or viewport only |
| `selector` | str\|null | null | CSS selector of element to screenshot |

**Returns:** `{"url": "...", "image_path": "cache/screenshots/abc123.png", "width": 1920, "height": 1080}`
**Cost:** FREE
**Rate Limit:** None

---

### research_search

Search the web using configured provider with domain filtering and temporal bounds.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | - | Search query |
| `provider` | str\|null | null | Provider: exa, tavily, firecrawl, brave, ddgs, arxiv, wikipedia, etc. |
| `n` | int | 10 | Number of results |
| `include_domains` | list[str]\|null | null | Filter to specific domains |
| `exclude_domains` | list[str]\|null | null | Exclude specific domains |
| `start_date` | str\|null | null | Results from this date (YYYY-MM-DD) |
| `end_date` | str\|null | null | Results until this date (YYYY-MM-DD) |
| `language` | str\|null | null | Language code (en, es, fr, etc.) |
| `provider_config` | dict[str, Any]\|null | null | Provider-specific configuration |

**Returns:** `{"query": "...", "results": [...], "provider": "exa", "total_results": 1234}`
**Cost:** PAID (varies by provider)
**Rate Limit:** Varies by provider

---

### research_security_headers

Analyze HTTP security headers of a URL to identify missing or misconfigured protections.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to analyze |

**Returns:** `{"url": "...", "headers": {...}, "issues": [...], "security_score": 85}`
**Cost:** FREE
**Rate Limit:** None

---

### research_semantic_sitemap

Crawl a domain's sitemap and cluster pages by semantic similarity for content mapping.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `domain` | str | - | Domain to crawl (with or without scheme) |
| `max_pages` | int | 50 | Maximum pages to crawl |
| `cluster_threshold` | float | 0.85 | Semantic similarity threshold for clustering (0-1) |

**Returns:** `{"domain": "...", "pages": [...], "clusters": [...], "topic_map": {...}}`
**Cost:** PAID (LLM embeddings)
**Rate Limit:** None

---

### research_sentiment_deep

Deep sentiment and emotion analysis with manipulation detection for nuanced understanding.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Text to analyze |
| `language` | str | en | Language code (auto-detect if empty) |

**Returns:** `{"text": "...", "sentiment": "positive", "confidence": 0.88, "emotions": {...}, "manipulation_score": 0.2}`
**Cost:** PAID (LLM analysis)
**Rate Limit:** None

---

### research_session_close

Close a persistent browser session by name.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | - | Session name to close |

**Returns:** `{"session": "...", "closed": true, "duration_seconds": 3600}`
**Cost:** FREE
**Rate Limit:** None

---

### research_session_list

List all active persistent browser sessions with details.

**Returns:** `{"sessions": [{"name": "...", "browser": "camoufox", "created_at": "...", "ttl_seconds": 3600}]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_session_open

Open (or reuse) a persistent browser session with optional login automation.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | - | Session name (alphanumeric, hyphens, underscores) |
| `browser` | str | camoufox | Browser: camoufox, chromium, or firefox |
| `ttl_seconds` | int | 3600 | Session time-to-live in seconds |
| `login_url` | str\|null | null | URL to navigate to for login |
| `login_script` | str\|null | null | JavaScript to execute for automated login |

**Returns:** `{"session": "...", "browser": "camoufox", "created": true, "expires_at": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_slack_notify

Send research results to a Slack channel or thread.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `channel` | str | - | Slack channel ID or name |
| `text` | str | - | Message text |
| `thread_ts` | str\|null | null | Thread timestamp for replies |
| `blocks` | list[dict[str, Any]]\|null | null | Slack Block Kit JSON |

**Returns:** `{"channel": "...", "ts": "...", "sent": true}`
**Cost:** FREE
**Rate Limit:** None

---

### research_social_profile

Extract public profile metadata from a social media URL.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | Social media profile URL |

**Returns:** `{"url": "...", "username": "...", "name": "...", "bio": "...", "followers": 5000, "profile_image": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_social_search

Check if a username exists across multiple social media platforms.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `username` | str | - | Username to search |
| `platforms` | list[str]\|null | null | Platforms to check (defaults to: twitter, github, linkedin, instagram, reddit, etc.) |

**Returns:** `{"username": "...", "found_on": ["twitter", "github"], "profiles": [...]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_spider

Parallelized bulk fetching of multiple URLs with bounded concurrency and deduplication.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `urls` | list[str] | - | URLs to fetch |
| `mode` | str | stealthy | Fetch mode: http, stealthy, or dynamic |
| `max_chars_each` | int | 5000 | Max characters per response |
| `concurrency` | int | 10 | Max parallel fetches (1-20) |
| `fail_fast` | bool | false | Stop on first error |
| `dedupe` | bool | true | Remove duplicate URLs before fetching |
| `order` | str | input | Result ordering: input, domain, or size |
| `solve_cloudflare` | bool | true | Attempt Cloudflare bypass |
| `headers` | dict[str, str]\|null | null | Custom HTTP headers |
| `user_agent` | str\|null | null | Override User-Agent |
| `proxy` | str\|null | null | Proxy URL |
| `cookies` | dict[str, str]\|null | null | Request cookies |
| `accept_language` | str | en-US,en;q=0.9,ar;q=0.8 | Accept-Language header |
| `timeout` | int\|null | null | Per-fetch timeout (seconds) |

**Returns:** `[{"url": "...", "status_code": 200, "text": "...", "error": null}, ...]`
**Cost:** FREE
**Rate Limit:** None

---

### research_stripe_balance

Get Stripe account balance and recent transaction summary.

**Returns:** `{"balance": {"available": [...], "pending": [...]}, "currency": "usd"}`
**Cost:** FREE
**Rate Limit:** None

---

### research_stylometry

Analyze text for stylometric fingerprinting and author deanonymization.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Text sample to analyze |
| `compare_texts` | list[str]\|null | null | Reference texts to compare against (for author matching) |

**Returns:** `{"text_length": 5432, "vocabulary_richness": 0.72, "sentence_length_avg": 18.5, "punctuation_profile": {...}, "author_match_score": 0.84}`
**Cost:** FREE
**Rate Limit:** None

---

### research_temporal_diff

Compare current page content with Wayback Machine archived version.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to compare |
| `max_cost_usd` | float | 0.05 | Maximum LLM cost budget for diff analysis |

**Returns:** `{"url": "...", "current": "...", "archived": "...", "diff_summary": "...", "changes": [...]}`
**Cost:** PAID (LLM analysis)
**Rate Limit:** None

---

### research_text_analyze

Perform NLP text analysis using NLTK (tokenization, POS tagging, named entities, etc.).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Text to analyze |
| `analyses` | list[str]\|null | null | Analysis types: tokens, pos, entities, sentiment, readability, etc. (defaults to all) |

**Returns:** `{"text": "...", "tokens": [...], "pos_tags": [...], "named_entities": [...], "readability_score": 8.5}`
**Cost:** FREE
**Rate Limit:** None

---

### research_text_to_speech

Convert text to speech using Google Cloud Text-to-Speech engine.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Text to convert |
| `language` | str | en | Language code (en, es, fr, de, zh, ar, etc.) |
| `voice` | str | en-US-Neural2-A | Voice ID (e.g., en-US-Neural2-A, en-US-Neural2-C) |
| `speaking_rate` | float | 1.0 | Speaking rate (0.25-4.0) |

**Returns:** `{"text": "...", "audio_file": "cache/audio/xyz.mp3", "duration_seconds": 15.2, "language": "en"}`
**Cost:** PAID (Google Cloud)
**Rate Limit:** None

---

### research_tor_new_identity

Request a new Tor circuit for exit node rotation.

**Returns:** `{"success": true, "new_exit_ip": "10.20.30.40", "exit_country": "US"}`
**Cost:** FREE
**Rate Limit:** Max 1 per 10 seconds

---

### research_tor_status

Check Tor daemon status and get current exit node IP and country.

**Returns:** `{"running": true, "exit_ip": "10.20.30.40", "exit_country": "US", "connected_circuits": 3}`
**Cost:** FREE
**Rate Limit:** None

---

### research_transcribe

Transcribe audio or video from YouTube or direct URL using OpenAI Whisper.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | YouTube URL or direct audio/video URL |
| `language` | str\|null | null | Language code (auto-detect if null) |
| `model_size` | str | base | Whisper model size: tiny, base, small, medium, large |

**Returns:** `{"url": "...", "text": "...", "language": "en", "duration_seconds": 300.5}`
**Cost:** FREE
**Rate Limit:** None

---

### research_tts_voices

List all supported Text-to-Speech voices with language and gender info.

**Returns:** `{"voices": [{"name": "en-US-Neural2-A", "language": "en-US", "gender": "female", ...}, ...]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_urlhaus_check

Check if URL is listed in URLhaus malware database (free, no key required).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to check |

**Returns:** `{"url": "...", "in_database": false, "threat": null}`
**Cost:** FREE
**Rate Limit:** None

---

### research_urlhaus_search

Search URLhaus by tag, signature, or payload hash (free API).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | - | Search term |
| `search_type` | str | tag | Search type: tag, signature, or hash |

**Returns:** `{"results": [...], "total": 42, "query": "...", "search_type": "tag"}`
**Cost:** FREE
**Rate Limit:** None

---

### research_usage_report

Aggregate LLM usage and costs from local cost tracker logs.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 7 | Number of days to report on |

**Returns:** `{"period_days": 7, "total_cost_usd": 12.34, "by_provider": {...}, "by_model": {...}}`
**Cost:** FREE
**Rate Limit:** None

---

### research_vastai_search

Search for available GPU instances on Vast.ai by type and price.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `gpu_type` | str | RTX 4090 | GPU type (RTX 4090, A100, H100, etc.) |
| `max_price` | float | 1.0 | Maximum hourly price in USD |
| `n` | int | 5 | Number of results |

**Returns:** `{"results": [...], "gpu_type": "RTX 4090", "count": 5}`
**Cost:** FREE
**Rate Limit:** None

---

### research_vastai_status

Get Vast.ai account status including balance and running instances.

**Returns:** `{"balance_usd": 42.50, "running_instances": 2, "total_spent_usd": 123.45}`
**Cost:** FREE
**Rate Limit:** None

---

### research_vercel_status

Return placeholder status for Vercel integration.

**Returns:** `{"status": "operational", "version": "..."}`
**Cost:** FREE
**Rate Limit:** None

---

### research_wayback

Retrieve archived versions of a URL from the Wayback Machine (free).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | - | URL to find in Wayback Machine |
| `limit` | int | 1 | Number of snapshots to return |

**Returns:** `{"url": "...", "snapshots": [{"timestamp": "20240101000000", "status": "200", "url": "..."}]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_whois

Run whois lookup on a domain to get registration and DNS information.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `domain` | str | - | Domain name to look up |

**Returns:** `{"domain": "...", "registrar": "...", "registered": "2010-01-15", "expires": "2025-01-15", "name_servers": [...]}`
**Cost:** FREE
**Rate Limit:** None

---

### research_wiki_ghost

Mine Wikipedia talk pages and edit history for contested knowledge and controversies.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `topic` | str | - | Wikipedia topic or article title |
| `language` | str | en | Wikipedia language (en, es, fr, de, etc.) |

**Returns:** `{"topic": "...", "talk_discussions": [...], "edit_wars": [...], "contested_sections": [...]}`
**Cost:** FREE
**Rate Limit:** None

---

## Summary Table (All 94 Tools)

| Category | Count | Tools | Cost |
|----------|-------|-------|------|
| Core | 6 | `research_fetch`, `research_spider`, `research_markdown`, `research_search`, `research_deep`, `research_health_check` | FREE/PAID |
| GitHub | 3 | `research_github_search`, `research_github_readme`, `research_github_releases` | FREE |
| Stealth | 2 | `research_camoufox`, `research_botasaurus` | FREE |
| LLM | 8 | `research_summarize`, `research_extract`, `research_classify`, `research_translate`, `research_expand`, `research_answer`, `research_embed`, `research_llm_chat` | PAID |
| Enrichment | 3 | `research_wayback`, `research_temporal_diff`, `research_markdown` | FREE/PAID |
| Creative | 11 | `research_red_team`, `research_multilingual`, `research_consensus`, `research_misinfo_check`, `research_citation_graph`, `research_ai_detect`, `research_curriculum`, `research_community_sentiment`, `research_wiki_ghost`, `research_semantic_sitemap`, `research_network_persona` | PAID |
| YouTube | 1 | `research_transcribe` | FREE |
| Exa/Search | 1 | `research_search` | PAID |
| Sessions | 3 | `research_session_open`, `research_session_list`, `research_session_close` | FREE |
| Config | 2 | `research_config_get`, `research_config_set` | FREE |
| Cache | 2 | `research_cache_stats`, `research_cache_clear` | FREE |
| PDF | 2 | `research_pdf_extract`, `research_pdf_search` | FREE |
| NLP | 1 | `research_text_analyze` | FREE |
| Screenshot | 1 | `research_screenshot` | FREE |
| RSS | 2 | `research_rss_fetch`, `research_rss_search` | FREE |
| Social OSINT | 2 | `research_social_profile`, `research_social_search` | FREE |
| Security | 2 | `research_security_headers`, `research_urlhaus_check` | FREE |
| Breach | 2 | `research_password_check`, `research_urlhaus_search` | FREE |
| Darkweb Core | 2 | `research_tor_status`, `research_tor_new_identity` | FREE |
| Darkweb Advanced | 1 | `research_onion_spectra` | FREE |
| Text Analysis | 1 | `research_sentiment_deep` | PAID |
| Stylometry | 1 | `research_stylometry` | FREE |
| Radicalization | 1 | `research_radicalization_detect` | PAID |
| Persona | 1 | `research_persona_profile` | PAID |
| Communication | 2 | `research_email_report`, `research_slack_notify` | FREE |
| Note-Taking | 1 | `research_save_note` | FREE |
| Media | 2 | `research_text_to_speech`, `research_tts_voices` | PAID/FREE |
| Infrastructure | 5 | `research_vastai_search`, `research_vastai_status`, `research_stripe_balance`, `research_usage_report`, `research_metrics` | FREE |
| Hosting | 1 | `research_vercel_status` | FREE |
| Domain | 1 | `research_whois` | FREE |
| OCR | 1 | `research_ocr_extract` | FREE |
| Network | 1 | `research_nmap_scan` | FREE |

**Total: 94 tools**

---

