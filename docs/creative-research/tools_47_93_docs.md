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

