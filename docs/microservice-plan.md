# Loom Microservice Split Plan

**Document Version:** 1.0
**Date:** 2026-05-03
**Status:** Proposed (not yet executed)
**Current State:** Monolithic MCP server (1 process, ~581 tools, port 8787)
**Target State:** 4 specialized microservices + 1 gateway router (5 processes, ports 8787-8790 + 8800)

---

## Executive Summary

Loom currently runs as a single monolithic FastMCP server exposing 581 tools across research, red-teaming, intelligence, and infrastructure domains. This plan splits it into **4 domain-specific microservices** orchestrated by a **central gateway**, enabling:

- **Independent scaling** per workload type (research-heavy vs. adversarial vs. OSINT)
- **Isolated failure domains** (red-team crash doesn't cascade to core research)
- **Team autonomy** (separate development teams per service)
- **Reduced startup time** (narrow import footprint per service)
- **Selective deployment** (deploy only services your org needs)

**Timeline:** 10-12 weeks (3 phases, phased migration)
**Effort:** ~680 engineer-days total

---

## Architecture Overview

### Current (Monolith)
```
Client → [FastMCP Server :8787 with 581 tools]
           ├─ Search (21 providers)
           ├─ Fetch/Scrape (Scrapling, Crawl4AI, Camoufox)
           ├─ LLM (8 providers)
           ├─ Sessions
           ├─ Adversarial (reframing, fuzzing, coevolution)
           ├─ OSINT (dark web, leak scan, threat profiles)
           ├─ Academic Integrity
           ├─ Career Intelligence
           ├─ Billing & Metrics
           └─ ...170 more modules
```

### Target (4 Microservices + Gateway)
```
Client
  ↓
┌─────────────────────────────────────────────────┐
│ loom-gateway :8800 (MCP Router/Load Balancer)   │
│  • Auth + Rate Limiting (centralized)           │
│  • Billing gateway                              │
│  • Service routing (tool name → service port)   │
│  • Health aggregation                           │
│  • Unified error handling                       │
└──────────┬──────────────────────────────────────┘
           │
     ┌─────┼─────────────────┬───────────────────┐
     ↓     ↓                 ↓                   ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ loom-core :8787  │  │ loom-redteam     │  │ loom-intel       │  │ loom-infra       │
│                  │  │ :8788            │  │ :8789            │  │ :8790            │
│ Search           │  │                  │  │                  │  │                  │
│ Fetch/Spider     │  │ Adversarial      │  │ OSINT            │  │ Billing          │
│ Markdown         │  │ Reframing (957)  │  │ Dark Web         │  │ Metrics          │
│ Deep Research    │  │ Fuzzing          │  │ Intelligence     │  │ Infrastructure   │
│ LLM Cascade      │  │ Coevolution      │  │ Academic         │  │ Deployment       │
│ GitHub           │  │ Genetic Algos    │  │ Career           │  │ Email            │
│ Sessions         │  │ BPJ Generator    │  │ Competitive      │  │ Slack            │
│ Config           │  │ Crescendo Loop   │  │ Supply Chain     │  │ Joplin           │
│ Cache            │  │ REID Pipeline    │  │ Threat Intel     │  │ VastAI           │
│ Health           │  │ Scoring          │  │ Leak Scan        │  │ GCP              │
│                  │  │ Consensus Build  │  │ Stego Detect     │  │ Vercel           │
│ (128 tools)      │  │ Attack Tracking  │  │ Crypto Trace     │  │ Tor              │
│                  │  │ (156 tools)      │  │ Social Graph     │  │ Transcription    │
│                  │  │                  │  │ (189 tools)      │  │ Document Conv    │
│                  │  │                  │  │                  │  │ (82 tools)       │
└──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────────────┘
     │ ↓ ↑ │              │ ↓ ↑ │              │ ↓ ↑ │              │ ↓ ↑ │
     └──────────────────────────────────────────────────────────────────────┘
            Shared Libraries & Singletons (across all services)
            • Cache Store (SQLite, SHA-256 keys)
            • Config System (JSON, atomic reload)
            • LLM Providers (8 implementations)
            • Validators (SSRF, URL sanitization)
            • Sessions (SQLite backend)
            • Logging + Tracing
            • Rate Limiter (Redis or in-memory)
            • Auth System
```

---

## Service Definitions

### 1. loom-core :8787 (128 tools)

**Responsibility:** Research core — discovery, fetching, analysis, knowledge synthesis.

**Tools (128 total):**
- **Search** (22 tools)
  - `research_search` (multi-provider dispatch)
  - `research_deep` (12-stage pipeline)
  - `multi_search` (parallel across 21+ providers)
  - Provider tools: exa, tavily, firecrawl, brave, ddgs, arxiv, wikipedia, hn_reddit, newsapi, coindesk, coinmarketcap, binance, ahmia, darksearch, ummro_rag, onionsearch, torcrawl, darkweb_cti, robin_osint, investing, youtube_transcripts

- **Fetch & Scraping** (12 tools)
  - `research_fetch` (Scrapling 3-tier: http/stealthy/dynamic)
  - `research_spider` (concurrent multi-URL)
  - `research_markdown` (Crawl4AI + Trafilatura)
  - `research_camoufox` (Camoufox stealth browser)
  - `research_botasaurus` (Botasaurus fallback)
  - `research_cache_stats` / `research_cache_clear`
  - Browser session wrappers

- **LLM & Analysis** (18 tools)
  - `research_llm_summarize`
  - `research_llm_extract`
  - `research_llm_classify`
  - `research_llm_translate`
  - `research_llm_expand`
  - `research_llm_answer`
  - `research_llm_embed`
  - `research_llm_chat`
  - `research_ask_all_models` (query all 8 providers in parallel)
  - `research_multi_llm_*` (multi-model comparison)
  - Language detection, semantic caching

- **Knowledge & Enrichment** (14 tools)
  - `research_github` (gh CLI wrapper)
  - `research_knowledge_graph` (semantic entity extraction)
  - `research_fact_checker` (claim verification)
  - `research_trend_predictor` (signal→trend forecasting)
  - `research_detect_language`
  - `research_wayback` (Internet Archive)
  - `research_rss_monitor`
  - `research_text_analyze`
  - `research_pdf_extract`
  - `research_screenshot`
  - `research_image_intel`
  - `research_geoip_local`
  - `research_report_generator`

- **Session & Config Management** (8 tools)
  - `research_session_open` / `research_session_list` / `research_session_close`
  - `research_config_get` / `research_config_set` / `research_config_reload`
  - `research_health_check`
  - `research_pool_stats` / `research_pool_reset` (connection pooling)

- **Core Infrastructure Tools** (34 tools)
  - API version, audit log export
  - Tracing, logging, error handling
  - Cache management, config validation
  - Rate limiter, auth, offline mode
  - CI/CD hooks, circ circuit breaker, backoff DLQ
  - Credentials vault
  - Context manager, chain composer
  - Semantic cache, param sweeper
  - Tool recommender
  - Benchmark suite, capability matrix
  - Dashboard
  - Metrics collection

**Core Dependencies:**
- `cache.py` (CacheStore singleton)
- `config.py` (ConfigModel + CONFIG dict)
- `sessions.py` (SessionManager + in-memory registry)
- `providers/*.py` (8 LLM providers + 21 search providers)
- `validators.py` (SSRF, URL sanitization)

**Startup Time:** ~2-3s (narrow import footprint)
**Memory Footprint:** ~450 MB (cache, sessions, LLM models)
**Typical QPS:** 100-300 req/s (mostly search/fetch, less compute)

**Why Core:** Research is the foundational layer used by all other services. Keep it lean and always available. All other services can call core over HTTP for search/fetch/LLM needs.

---

### 2. loom-redteam :8788 (156 tools)

**Responsibility:** Adversarial attack generation, jailbreak crafting, safety evasion, genetic optimization, attack tracking.

**Tools (156 total):**

- **Reframing & Prompt Injection** (67 tools)
  - 957 reframing strategies organized into 32 modules:
    - `core.py`, `advanced.py`, `encoding.py`, `jailbreak.py`, `reasoning.py`, `persona.py`
    - `format_exploit.py`, `attention.py`, `legal.py`, `multiturn.py`, `specialized.py`, `novel_2026.py`
    - `multimodal.py`, `agent_tool.py`, `token_repr.py`, `reasoning_cot.py`, `defense_evasion.py`, `research_2026.py`
    - `persuasion.py`, `advanced_novel.py`, `skills_extracted.py`, `guardrail_suite.py`, `arxiv_nim.py`
    - `reid_psychology.py`, `advanced_psychology.py`, `psychology_extended.py`, `fusion_10x.py`
    - `research_derived.py`, `arabic_attacks.py`, `token_smuggling.py`
  - Tool: `research_reframe_strategy` (select + apply strategy)
  - Tool: `research_prompt_inject_craft` (multi-stage payload generation)

- **Adversarial Pipelines** (23 tools)
  - `research_adversarial_debate` (peer attack debate framework)
  - `research_adversarial_craft` (attack string generation)
  - `research_daisy_chain` (multi-hop attack orchestration)
  - `research_cross_model_transfer` (attack effectiveness across models)
  - `research_context_poisoning` (context pollution pipelines)
  - `research_evidence_pipeline` (multi-stage evidence collection)
  - `research_model_evidence` (model-agnostic evidence synthesis)
  - `research_orchestrate` (generic orchestration)

- **Fuzzing & Genetic Algorithms** (18 tools)
  - `research_fuzzer` (attack discovery via fuzzing)
  - `research_param_sweep` (parameter space exploration)
  - `research_genetic_algorithm` (fitness-based attack evolution)
  - `research_auto_experiment` (auto-tune attack parameters)
  - `research_auto_params` (parameter recommendation)
  - `research_auto_pipeline` (auto-select + compose tools)

- **Generation & Creative Tools** (22 tools)
  - `research_bpj_generator` (Best-Practice Jailbreak generation)
  - `research_prompt_analyzer` (analyze prompt vulnerabilities)
  - `research_prompt_reframe` (reframe for evasion)
  - `research_psycholinguistic` (psychological attack vectors)
  - `research_culture_dna` (culturally-targeted attacks)
  - `research_bias_lens` (identify model biases)
  - `research_creative` (creative prompt generation)

- **Scoring & Evaluation** (14 tools)
  - `research_attack_scorer` (attack efficacy scoring)
  - `research_unified_score` (aggregate scoring)
  - `research_score_all` (batch scoring)
  - `research_stealth_calc` (stealth metric calculation)
  - `research_stealth_detect` (stealth level classification)
  - `research_stealth_score` (stealth scoring)
  - `research_executability` (execution probability)
  - `research_quality_scorer` (output quality)
  - `research_harm_assessor` (harm potential)
  - `research_toxicity_checker` (toxicity detection)
  - `research_danger_prescore` (pre-execution danger)

- **Tracking & Evolution** (12 tools)
  - `research_attack_tracker` (attack history & statistics)
  - `research_jailbreak_evolution` (effectiveness tracking)
  - `research_drift_monitor` (model behavior drift)
  - `research_consistency_pressure` (consistency constraint monitoring)
  - `research_strategy_oracle` (adaptive strategy selection)

- **Consensus & Coevolution** (8 tools)
  - `research_consensus_build` (multi-run consensus)
  - `research_consensus_pressure` (consistency voting)
  - `research_coevolution` (attacker-defense coevolution)

- **Specialized Attack Pipelines** (4 tools)
  - `research_crescendo_loop` (incremental harm escalation)
  - `research_reid_pipeline` (Reinforced Exploitation ID automation)
  - `research_reid_auto` (REID automation)
  - `research_reid_psychology` (REID psychology specialization)

**Core Dependencies:**
- `cache.py` (result caching for iterations)
- `config.py` (attack config, model selection)
- Calls to **loom-core** over HTTP for LLM providers
- `attack_scorer.py`, `stealth_calc.py`, etc. (local scoring)

**Startup Time:** ~4-5s (many strategy modules loaded)
**Memory Footprint:** ~800 MB (strategy registry, fuzzing state)
**Typical QPS:** 10-50 req/s (compute-intensive, slower per request)

**Why Separate:** Red-team workloads are CPU/GPU-intensive and can crash with long-running fuzzing loops. Isolating them prevents training-time failures from affecting research availability. Easy to scale horizontally for attack iterations.

---

### 3. loom-intel :8789 (189 tools)

**Responsibility:** OSINT, intelligence gathering, threat profiling, academic/career analysis, supply chain tracking.

**Tools (189 total):**

- **OSINT Core** (28 tools)
  - `research_osint_extended` (extended OSINT)
  - `research_dark_forum` (search 24M+ dark web forums)
  - `research_dark_recon` (dark web reconnaissance)
  - `research_leak_scan` (breach database + paste site scanning)
  - `research_metadata_forensics` (EXIF/PDF/document extraction)
  - `research_stylometry` (writing style analysis)
  - `research_deception_detect` (deception detection)
  - `research_social_graph` (relationship mapping)
  - `research_identity_resolve` (identity linking)
  - `research_social_intel` (social platform analysis)
  - `research_social_media_profiler` / `research_social_media_tracker`

- **Dark Web & Specialized** (38 tools)
  - `research_onion_discover` (Tor exit node crawling)
  - `research_onion_spectra` (Tor hidden services catalog)
  - `research_cipher_mirror` (encrypted communication analysis)
  - `research_forum_cortex` (dark forum intelligence)
  - `research_ghost_weave` (anonymous network mapping)
  - `research_dead_drop_scanner` (covert communication channels)
  - `research_darkweb_early_warning` (dark web threat alerts)
  - `research_dark_web_cti` (dark web CTI)
  - `research_access_tools` (dark web access coordination)
  - `research_p3_tools` (P3 protocol analysis)
  - `research_unique_tools` (unique darkweb tools)
  - `research_infowar_tools` (information warfare toolkit)
  - `research_realtime_monitor` (real-time threat monitoring)
  - Plus 24 more specialized dark web tools

- **Infrastructure & Threat Profiling** (26 tools)
  - `research_infra_correlator` (domain/IP linking)
  - `research_infra_analysis` (registry_graveyard, subdomain_temporal, commit_analyzer)
  - `research_passive_recon` (DNS/WHOIS/ASN enrichment)
  - `research_threat_profile` (adversary infrastructure profiling)
  - `research_threat_intel` (threat intelligence synthesis)
  - `research_ip_intel` (IP intelligence)
  - `research_domain_intel` (domain profiling)
  - `research_cert_analyzer` (SSL/TLS certificate analysis)
  - `research_security_headers` (HTTP security headers)
  - `research_cve_lookup` (CVE database lookup)
  - `research_vuln_intel` (vulnerability intelligence)
  - `research_breach_check` (breach database lookup)
  - `research_urlhaus_lookup` (URLhaus malware tracking)
  - `research_crypto_trace` (blockchain address clustering)
  - `research_crypto_risk` (crypto risk assessment)
  - Plus 11 more infrastructure tools

- **Academic Integrity** (26 tools)
  - `research_academic_integrity` (citation_analysis, retraction_check, predatory_journal_check)
  - `research_hcs10_academic` (grant_forensics, monoculture_detect, review_cartel, data_fabrication, institutional_decay, shell_funding, conference_arbitrage, preprint_manipulation)
  - `research_hcs_scorer` (HCS scoring)
  - `research_gap_tools_academic` (academic gap analysis)
  - `research_gap_tools_advanced` (advanced gap analysis)
  - Plus 16 more academic tools

- **Career Intelligence** (18 tools)
  - `research_career_intel` (career trajectory analysis)
  - `research_career_trajectory` (career path prediction)
  - `research_job_signals` (job market signals)
  - `research_job_research` (job research aggregation)
  - `research_deception_job_scanner` (fake job detection)
  - `research_resume_intel` (resume analysis)
  - `research_salary_synthesizer` (salary intelligence)
  - `research_job_experts` (expert identification in job market)
  - Plus 10 more career tools

- **Competitive Intelligence** (18 tools)
  - `research_competitive_intel` (competitive analysis)
  - `research_competitive_monitor` (competitive monitoring)
  - `research_company_intel` (company profiling)
  - `research_supply_chain_intel` (supply chain tracking)
  - `research_signal_detection` (signal detection from data)
  - Plus 13 more competitive tools

- **Advanced Analysis** (20 tools)
  - `research_persona_profile` (persona profiling)
  - `research_radicalization_detect` (radicalization detection)
  - `research_sentiment_deep` (deep sentiment analysis)
  - `research_network_persona` (network-level persona analysis)
  - `research_change_monitor` (change detection & tracking)
  - `research_model_profiler` (model capability profiling)
  - `research_model_sentiment` (model sentiment/bias)
  - `research_policy_validator` (policy compliance)
  - Plus 12 more analysis tools

- **Helper Tools** (15 tools)
  - `research_dead_content` (recover archived/shadow-banned)
  - `research_invisible_web` (dark web, intranets, API-only)
  - `research_js_intel` (JavaScript introspection)
  - `research_stego_detect` (steganography detection)
  - Plus 11 more helpers

**Core Dependencies:**
- Calls to **loom-core** for search/fetch/LLM via HTTP
- `cache.py` (local result caching)
- `config.py` (intel config)

**Startup Time:** ~3-4s
**Memory Footprint:** ~600 MB (threat DB indexes, academic databases)
**Typical QPS:** 30-100 req/s (variable compute intensity)

**Why Separate:** Intelligence workloads have unique data dependencies (leak databases, threat feeds, academic databases) that may not be needed by other services. Easy to geofence or restrict based on org policy.

---

### 4. loom-infra :8790 (82 tools)

**Responsibility:** Infrastructure, billing, deployment, notifications, external services integration.

**Tools (82 total):**

- **Billing & Metering** (32 tools)
  - `research_billing_*` (cost tracking, credits, customers, dashboard, isolation, metering, overage, retention, Stripe, tier limiting, tier definitions)
  - 12 billing submodules: __init__, cost_tracker, credits, customers, dashboard, isolation, meter, overage, retention, stripe_integration, tier_limiter, tiers

- **Metrics & Monitoring** (14 tools)
  - `research_metrics_*` (metrics collection, aggregation, dashboarding)
  - `research_benchmark_run` (performance benchmarking)
  - `research_capability_matrix` (capability tracking)
  - `research_consistency_pressure` (cross-service consistency)
  - Plus monitoring wrappers

- **Communication & Notifications** (12 tools)
  - `research_email_report` (email delivery)
  - `research_slack_notify` (Slack notifications)
  - `research_joplin_sync` (Joplin note sync)
  - Plus 9 more notification/communication tools

- **Infrastructure Integration** (18 tools)
  - `research_vastai_*` (VastAI compute integration)
  - `research_gcp_*` (Google Cloud integration)
  - `research_vercel_*` (Vercel deployment)
  - `research_tor_*` (Tor network integration)
  - `research_transcribe_*` (audio transcription)
  - `research_document_*` (document conversion)
  - Plus 6 more infrastructure tools

- **Deployment & CI/CD** (6 tools)
  - `research_cicd_*` (CI/CD integration)
  - `research_config_reload` (hot config reload)
  - `research_changelog_gen` (changelog generation)
  - `research_credential_vault` (secret management)
  - Plus 2 more deployment tools

**Core Dependencies:**
- `cache.py` (temp caching for billing records)
- `config.py` (billing config)
- HTTP calls to **loom-core** for usage data
- External APIs: Stripe, VastAI, GCP, Vercel, etc.

**Startup Time:** ~2-3s
**Memory Footprint:** ~250 MB (billing DB, metrics in-memory)
**Typical QPS:** 10-30 req/s (mostly I/O to external services)

**Why Separate:** Infrastructure services have different SLA requirements and external dependencies. Isolate them to prevent billing/deployment issues from cascading to research services.

---

### 5. loom-gateway :8800 (Router + Orchestrator)

**Responsibility:** Central routing, authentication, rate limiting, billing checks, service health aggregation.

**Functions:**
- **Tool Routing**
  - Maintains tool registry mapping: tool name → service (port)
  - Routes incoming `mcp.call_tool()` to correct service
  - Example: `research_search` → loom-core:8787, `research_fuzzer` → loom-redteam:8788

- **Authentication & Rate Limiting**
  - Central auth enforcement (API keys, JWT, etc.)
  - Per-user rate limiting (configurable limits per service)
  - Cost-aware rate limiting (red-team more expensive than search)

- **Billing Checks**
  - Before executing tool, check user credits/tier
  - Call loom-infra to deduct costs
  - Reject if over quota

- **Health Aggregation**
  - Poll all 4 services' health endpoints every 5-10s
  - Return unified `/health` endpoint
  - Circuit-breaker logic: if service down, return degraded status

- **Error Handling & Fallback**
  - If loom-core down, some tools fail immediately
  - If loom-redteam down, fallback to basic LLM reframing from core
  - If loom-intel down, return cached results or "service unavailable"
  - If loom-infra down, cache billing events locally, sync when restored

- **Metrics & Logging**
  - Log all tool calls (audit trail)
  - Track latency per service
  - Export Prometheus metrics

**Implementation:**
- FastMCP server that proxies MCP calls
- HTTP client library for inter-service communication (httpx or requests)
- Redis or in-memory store for auth tokens + rate limit counters

**Memory Footprint:** ~200 MB (routing table, caches, metrics)
**Startup Time:** ~1s
**Typical QPS:** Limited only by downstream services

---

## Shared Infrastructure (All Services)

All 5 services share these libraries and singletons:

### 1. Cache System (`cache.py`)
- **CacheStore singleton** using SHA-256 content-hash keys
- Daily subdirectories: `~/.cache/loom/YYYY-MM-DD/`
- Atomic writes via UUID temp + `os.replace()`
- **Shared across all services via shared `LOOM_CACHE_DIR` env var**
- Read-heavy, so negligible inter-service contention

### 2. Configuration (`config.py`)
- **ConfigModel** (Pydantic v2) with validated bounds
- Module-level CONFIG dict
- Resolved via: explicit path > `$LOOM_CONFIG_PATH` > `./config.json`
- **All services read same config file**
- Hot reload via `research_config_reload` (gateway calls loom-infra to trigger)

### 3. LLM Providers (`providers/*.py`)
- 8 implementations: groq, nvidia_nim, deepseek, gemini, moonshot, openai, anthropic, vllm
- Abstract `LLMProvider` base class with `chat()`, `embed()`, `available()`, `close()`
- **Cascade order**: LLM_CASCADE_ORDER env var (default: groq → nvidia_nim → deepseek → gemini → moonshot → openai → anthropic → vllm)
- **Called by:**
  - loom-core: direct calls (research/LLM tools)
  - loom-redteam: via HTTP to loom-core (reframing, scoring)
  - loom-intel: via HTTP to loom-core (analysis)
  - loom-infra: indirect (metrics collection)

### 4. Validators (`validators.py`)
- SSRF-safe URL validation
- Character capping
- GitHub query sanitization
- **Linked statically into each service (no HTTP overhead)**

### 5. Session Management (`sessions.py`)
- In-memory async registry (global `_sessions` dict with asyncio.Lock)
- SQLite-backed `SessionManager` with LRU eviction (max 8)
- Session names: `^[a-z0-9_-]{1,32}$`
- **Stored at `~/.loom/sessions/` — shared across all services**
- Read-heavy; writes are rare (only on session creation/close)

### 6. Logging & Tracing (`logging_config.py`, `tracing.py`)
- Structured logging (JSON format for aggregation)
- Distributed tracing headers (X-Trace-ID, X-Parent-ID)
- **Each service logs to `/var/log/loom/{service_name}.log`**
- Aggregated by ELK or Loki (optional)

### 7. Rate Limiter (`rate_limiter.py`)
- Per-user, per-endpoint rate limiting
- Redis backend preferred (for distributed scenario), fallback to in-memory dict
- **Centralized at loom-gateway; local enforcement at each service**

### 8. Auth System (`auth.py`)
- MCP auth settings (token validation, etc.)
- OAuth/JWT integration
- **Centralized at loom-gateway; each service validates via shared key**

---

## Communication Patterns

### Inter-Service Communication (HTTP)

**When loom-redteam calls loom-core for LLM:**
```python
# loom-redteam/tools/fuzzing.py
import httpx

async def research_fuzzer(...) -> dict:
    # Fuzzer needs to call LLM to generate payloads
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8787/mcp/call_tool",
            json={
                "tool_name": "research_llm_chat",
                "params": {...}
            },
            headers={"Authorization": f"Bearer {get_service_token()}"}
        )
        llm_result = resp.json()
    # ... continue fuzzing
    return result
```

**Fallback if loom-core unreachable:**
```python
try:
    llm_result = await call_core_llm(...)
except httpx.ConnectError:
    # Degrade: use cached LLM provider directly
    # OR return error to user
    raise AppException("Search service unavailable")
```

### Service-to-Service Authentication

All inter-service calls include:
- **Header:** `Authorization: Bearer <SERVICE_TOKEN>`
- **Service tokens:** Stored in `~/.loom/service-tokens.json` (generated at startup)
- **Gateway validates** all tokens before routing

### Data Flow Example: Red-Team Fuzzing Attack

```
Client API Call (gateway:8800)
  "research_fuzzer(target_model='gpt-4', strategy='token_injection')"
    ↓
loom-gateway (route to loom-redteam:8788)
  [Check auth + rate limit + credits]
    ↓
loom-redteam:8788
  research_fuzzer starts
    • Loop: generate payload variants
    • For each variant:
      - Call loom-core:8787 for LLM evaluation
        POST /mcp/call_tool
        research_llm_chat(model='gpt-4', prompt=payload)
      - Get response, score with research_attack_scorer
      - Mutate + retry
    ↓
    Return final attack results
    ↓
loom-gateway
  [Deduct billing credits via loom-infra:8790]
  [Log to audit trail]
    ↓
Client receives result
```

---

## Migration Plan (Phased)

### Phase 1: Foundation & Core (Weeks 1-4, ~200 engineer-days)

**Goal:** Establish gateway, export core tools, verify functionality.

1. **Create gateway service** (Week 1, 30 days)
   - [ ] Implement MCP router in `loom-gateway/server.py`
   - [ ] Build tool registry (map tool name → service:port)
   - [ ] Add centralized auth + rate limiting
   - [ ] Implement health check aggregation
   - [ ] Write tests for routing logic
   - Deliverable: `loom-gateway` running on :8800, routing to single server :8787

2. **Prepare loom-core** (Week 2-3, 60 days)
   - [ ] Extract core tools into separate entry point
   - [ ] Move `src/loom/tools/{fetch,spider,markdown,search,deep,github,stealth,cache_mgmt,llm,enrich,sessions,config,server}.py` into core-focused imports
   - [ ] Create `src/loom/servers/core.py` (thin FastMCP wrapper)
   - [ ] Test: can loom-core start independently on :8787? ✓
   - [ ] Test: can gateway route to loom-core? ✓
   - Deliverable: Dual startup (gateway + core both working)

3. **Set up Docker Compose** (Week 4, 40 days)
   - [ ] Create `docker-compose.yml` with 5 services
   - [ ] Volume mounts for shared cache, config, sessions
   - [ ] Network setup (services can reach :8787-8790, gateway on :8800)
   - [ ] Test: all 5 services start in order ✓
   - Deliverable: `docker-compose up` starts full stack

4. **Testing & Validation** (Week 4, 70 days)
   - [ ] Unit tests for gateway routing
   - [ ] Integration tests: client → gateway → core → LLM ✓
   - [ ] Load test: 100 req/s to gateway (routed to core)
   - [ ] Failover test: kill core, gateway returns 503
   - Deliverable: Phase 1 sign-off document

**Exit Criteria:**
- Gateway routes all tool calls to loom-core
- Core runs independently
- Docker Compose works
- All tests green

**Rollback Plan:** If issues, revert to monolith by reverting gateway + core extraction commits.

---

### Phase 2: Red-Team Service (Weeks 5-7, ~150 engineer-days)

**Goal:** Extract red-team tools, verify scoring/fuzzing work via inter-service calls.

1. **Extract loom-redteam** (Week 5, 60 days)
   - [ ] Move adversarial tools into `src/loom/servers/redteam.py`
   - [ ] Import 156 tools: reframing (957 strategies), fuzzing, genetic algos, scoring, consensus, coevolution, crescendo, reid
   - [ ] Update imports in `redteam.py` to avoid circular dependencies
   - [ ] Create HTTP client for core LLM calls
   - [ ] Test: loom-redteam starts independently? ✓
   - [ ] Test: can call `research_fuzzer` → it calls core LLM? ✓
   - Deliverable: Separate loom-redteam service

2. **Inter-Service Call Testing** (Week 6, 50 days)
   - [ ] Integration test: red-team → core LLM cascade
   - [ ] Integration test: red-team → core search (for context)
   - [ ] Load test: 50 concurrent fuzzing jobs
   - [ ] Resilience test: core down → redteam degrades gracefully
   - Deliverable: Red-team working via inter-service calls

3. **Billing Integration** (Week 7, 40 days)
   - [ ] Gateway pre-checks: is fuzzer expensive? deduct credits first
   - [ ] Redteam reports usage to infra service
   - [ ] Tests: user out of credits → rejected by gateway ✓
   - Deliverable: Cost-aware red-team routing

**Exit Criteria:**
- loom-redteam runs on :8788
- Fuzzing calls loom-core for LLM without issues
- Billing enforcement works
- No regression in monolith (still running :8787)

---

### Phase 3: Intel & Infra Services (Weeks 8-10, ~200 engineer-days)

**Goal:** Extract intel and infra services, finalize gateway routing.

1. **Extract loom-intel** (Week 8, 80 days)
   - [ ] Move 189 OSINT/intelligence tools into `src/loom/servers/intel.py`
   - [ ] Import: dark web, threat profiles, academic, career, competitive intelligence
   - [ ] Add HTTP calls to core for search/fetch/LLM
   - [ ] Test: loom-intel independent? ✓
   - [ ] Test: intel → core search chain? ✓
   - Deliverable: Separate loom-intel service

2. **Extract loom-infra** (Week 8-9, 70 days)
   - [ ] Move 82 infrastructure tools into `src/loom/servers/infra.py`
   - [ ] Import: billing, metrics, notifications, VastAI, GCP, Vercel, etc.
   - [ ] Expose `/metrics` Prometheus endpoint
   - [ ] Test: loom-infra independent? ✓
   - [ ] Test: gateway → infra for billing ✓
   - Deliverable: Separate loom-infra service

3. **Gateway Routing Finalization** (Week 9-10, 50 days)
   - [ ] Update tool registry to route all 581 tools correctly
   - [ ] Test: gateway can route to all 4 services
   - [ ] Circuit breaker: if service down, graceful degradation
   - [ ] Metrics: latency per service, success rates
   - [ ] Tests: full E2E journey (search → redteam → Intel → billing)
   - Deliverable: Unified gateway with full routing

**Exit Criteria:**
- All 4 services running independently
- Gateway correctly routes 581+ tools
- No regressions (existing tools work same as monolith)
- Full E2E test passes

---

### Phase 4: Cleanup & Optimization (Weeks 11-12, ~130 engineer-days)

**Goal:** Consolidate mono repo structure, optimize startup, document.

1. **Code Consolidation** (Week 11, 50 days)
   - [ ] Remove duplicate code from gateway (now in services)
   - [ ] Consolidate providers + validators into shared package
   - [ ] Move shared code to `src/loom/shared/` (imported by all services)
   - [ ] Update imports everywhere
   - [ ] Tests: all modules still pass ✓
   - Deliverable: Cleaner repo structure

2. **Startup Optimization** (Week 11, 40 days)
   - [ ] Lazy load providers (only init requested provider)
   - [ ] Async initialization for long-running resources
   - [ ] Parallel service startup in Docker Compose
   - [ ] Measure startup time per service (target: <5s each)
   - Deliverable: Sub-5s startup for each service

3. **Documentation** (Week 12, 40 days)
   - [ ] Update CLAUDE.md with microservice architecture
   - [ ] Write deployment guide (Docker, K8s)
   - [ ] Write troubleshooting guide
   - [ ] Update API docs (tool name → service mapping)
   - Deliverable: Complete docs package

**Exit Criteria:**
- Monolith fully decomposed
- All startup times <5s
- Documentation complete
- Ready for production deployment

---

## Docker Compose Configuration

```yaml
version: '3.9'

services:
  # Shared cache volume
  loom-cache:
    image: busybox
    volumes:
      - loom-cache:/home/user/.cache/loom
    command: sh -c "mkdir -p /home/user/.cache/loom && chmod 777 /home/user/.cache/loom"

  # Shared config volume
  loom-config:
    image: busybox
    volumes:
      - loom-config:/home/user/.loom
    command: sh -c "mkdir -p /home/user/.loom && chmod 777 /home/user/.loom"

  # Core service: Search, Fetch, LLM, Sessions
  loom-core:
    build:
      context: .
      dockerfile: docker/Dockerfile.core
    ports:
      - "8787:8787"
    environment:
      - LOOM_HOST=0.0.0.0
      - LOOM_PORT=8787
      - LOOM_CONFIG_PATH=/home/user/.loom/config.json
      - LOOM_CACHE_DIR=/home/user/.cache/loom
      - LOOM_SESSIONS_DIR=/home/user/.loom/sessions
      - LOG_LEVEL=INFO
      - GROQ_API_KEY=${GROQ_API_KEY}
      - NVIDIA_NIM_API_KEY=${NVIDIA_NIM_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - GOOGLE_AI_KEY=${GOOGLE_AI_KEY}
      - MOONSHOT_API_KEY=${MOONSHOT_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - EXA_API_KEY=${EXA_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
    volumes:
      - loom-cache:/home/user/.cache/loom
      - loom-config:/home/user/.loom
      - ./src:/app/src
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8787/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - loom-net
    depends_on:
      loom-cache:
        condition: service_completed_successfully
      loom-config:
        condition: service_completed_successfully

  # Red-team service: Fuzzing, Reframing, Attack Scoring
  loom-redteam:
    build:
      context: .
      dockerfile: docker/Dockerfile.redteam
    ports:
      - "8788:8788"
    environment:
      - LOOM_HOST=0.0.0.0
      - LOOM_PORT=8788
      - LOOM_CONFIG_PATH=/home/user/.loom/config.json
      - LOOM_CACHE_DIR=/home/user/.cache/loom
      - LOOM_CORE_URL=http://loom-core:8787
      - LOG_LEVEL=INFO
    volumes:
      - loom-cache:/home/user/.cache/loom
      - loom-config:/home/user/.loom
      - ./src:/app/src
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8788/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - loom-net
    depends_on:
      loom-core:
        condition: service_healthy
    restart: on-failure

  # Intel service: OSINT, Dark Web, Threat Profiles
  loom-intel:
    build:
      context: .
      dockerfile: docker/Dockerfile.intel
    ports:
      - "8789:8789"
    environment:
      - LOOM_HOST=0.0.0.0
      - LOOM_PORT=8789
      - LOOM_CONFIG_PATH=/home/user/.loom/config.json
      - LOOM_CACHE_DIR=/home/user/.cache/loom
      - LOOM_CORE_URL=http://loom-core:8787
      - LOG_LEVEL=INFO
    volumes:
      - loom-cache:/home/user/.cache/loom
      - loom-config:/home/user/.loom
      - ./src:/app/src
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8789/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - loom-net
    depends_on:
      loom-core:
        condition: service_healthy
    restart: on-failure

  # Infra service: Billing, Metrics, Notifications
  loom-infra:
    build:
      context: .
      dockerfile: docker/Dockerfile.infra
    ports:
      - "8790:8790"
    environment:
      - LOOM_HOST=0.0.0.0
      - LOOM_PORT=8790
      - LOOM_CONFIG_PATH=/home/user/.loom/config.json
      - LOOM_CACHE_DIR=/home/user/.cache/loom
      - LOG_LEVEL=INFO
      - STRIPE_LIVE_KEY=${STRIPE_LIVE_KEY}
      - STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}
      - SMTP_USER=${SMTP_USER}
      - SMTP_APP_PASSWORD=${SMTP_APP_PASSWORD}
      - VASTAI_API_KEY=${VASTAI_API_KEY}
    volumes:
      - loom-cache:/home/user/.cache/loom
      - loom-config:/home/user/.loom
      - ./src:/app/src
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8790/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - loom-net
    depends_on:
      loom-core:
        condition: service_healthy
    restart: on-failure

  # Gateway: Central routing, Auth, Rate limiting
  loom-gateway:
    build:
      context: .
      dockerfile: docker/Dockerfile.gateway
    ports:
      - "8800:8800"
    environment:
      - LOOM_HOST=0.0.0.0
      - LOOM_PORT=8800
      - LOOM_CONFIG_PATH=/home/user/.loom/config.json
      - LOOM_CORE_URL=http://loom-core:8787
      - LOOM_REDTEAM_URL=http://loom-redteam:8788
      - LOOM_INTEL_URL=http://loom-intel:8789
      - LOOM_INFRA_URL=http://loom-infra:8790
      - LOG_LEVEL=INFO
    volumes:
      - loom-config:/home/user/.loom
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8800/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - loom-net
    depends_on:
      loom-core:
        condition: service_healthy
      loom-redteam:
        condition: service_healthy
      loom-intel:
        condition: service_healthy
      loom-infra:
        condition: service_healthy
    restart: on-failure

networks:
  loom-net:
    driver: bridge

volumes:
  loom-cache:
  loom-config:
```

### Docker Build Files

**docker/Dockerfile.core:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e ".[core]"  # Installs loom with core extras only

EXPOSE 8787
CMD ["loom", "serve", "--server", "core"]
```

**docker/Dockerfile.gateway:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e ".[gateway]"  # Installs loom with gateway extras only

EXPOSE 8800
CMD ["loom", "serve", "--server", "gateway"]
```

(Similar for redteam, intel, infra)

---

## Effort Estimation Per Phase

| Phase | Week | Task | Engineer-Days | Notes |
|-------|------|------|----------------|-------|
| **1: Foundation** | 1 | Gateway implementation | 30 | MCP router, auth, health checks |
| | 2-3 | Core service extraction | 60 | Import subset, test independence |
| | 4 | Docker Compose + testing | 110 | Full stack testing, integration tests |
| | | **Phase 1 Total** | **200** | **Entry point: gateway + core on :8787-8800** |
| **2: Red-Team** | 5 | Redteam extraction | 60 | 156 tools, strategy registry |
| | 6 | Inter-service testing | 50 | Core LLM calls, resilience |
| | 7 | Billing integration | 40 | Credit deduction, gateway routing |
| | | **Phase 2 Total** | **150** | **Exit point: 3 services running** |
| **3: Intel/Infra** | 8 | Intel extraction | 80 | 189 tools, dark web deps |
| | 8-9 | Infra extraction | 70 | Billing, metrics, notifications |
| | 9-10 | Gateway routing finalization | 50 | Full tool registry, E2E tests |
| | | **Phase 3 Total** | **200** | **Exit point: all 5 services running** |
| **4: Cleanup** | 11 | Code consolidation | 50 | Dedupe, shared package |
| | 11 | Startup optimization | 40 | Lazy loading, async init |
| | 12 | Documentation | 40 | CLAUDE.md, deployment, troubleshooting |
| | | **Phase 4 Total** | **130** | **Exit point: production-ready microservices** |
| | | **GRAND TOTAL** | **~680 days** | **~10-12 weeks (assuming 2-3 engineers)** |

---

## Rollback Strategy

Each phase has a rollback plan:

**Phase 1 Rollback:**
- Revert commits for gateway + core extraction
- Restart monolith (`loom serve --server monolith`)
- Risk: LOW (gateway is additive; monolith unchanged)

**Phase 2 Rollback:**
- Disable redteam routing in gateway (route to core instead)
- Monolith stays running
- Risk: LOW (redteam is new; core fallback works)

**Phase 3 Rollback:**
- Disable intel + infra routing in gateway
- Monolith stays running
- Billing may show inconsistencies, but no data loss
- Risk: MEDIUM (infra is critical; needs careful sync)

**Full Rollback to Monolith:**
1. Stop all services: `docker-compose down`
2. Revert all extraction commits: `git revert --no-commit <commits>`
3. Restart monolith: `docker-compose -f docker-compose.mono.yml up`
4. Risk: MEDIUM (data consistency in cache/sessions)

---

## Recommended Org Structure

Post-microservice split, recommend:

| Team | Services | Size | Lead |
|------|----------|------|------|
| **Core Research** | loom-core | 2-3 engineers | Search + LLM specialist |
| **Red-Team/Attack** | loom-redteam | 3-4 engineers | Adversarial AI specialist |
| **Intelligence** | loom-intel | 2-3 engineers | OSINT + threat intel specialist |
| **Infra/DevOps** | loom-gateway + loom-infra | 2 engineers | SRE + deployment specialist |
| **QA/Ops** | All services | 1 engineer | Test automation + monitoring |
| | **Total** | **10-13 engineers** | Cross-team coordination |

---

## Success Metrics

After deployment, measure:

| Metric | Target | Tool |
|--------|--------|------|
| **Service Startup Time** | <5s per service | Docker logs |
| **Gateway Routing Latency** | <50ms p95 | Prometheus |
| **Service Availability** | >99.5% uptime per service | Health checks |
| **Cache Hit Rate** | >70% | loom-cache metrics |
| **Tool Coverage** | 100% (all 581 tools routable) | Gateway registry |
| **Regression Tests Pass** | 100% | pytest CI/CD |
| **Cost Isolation** | <5% variance | Billing metrics |
| **Cross-Service Calls** | <100ms p95 latency | Distributed tracing |

---

## Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Cache corruption in multi-writer scenario** | Data loss | Atomic writes via UUID temp + replace; periodic integrity checks |
| **Session state split across services** | User session loss | Sessions in shared SQLite; read-heavy so low contention |
| **Gateway becomes bottleneck** | Latency → QPS limited | Stateless gateway; horizontal scaling via load balancer |
| **Circular service dependencies** | Deadlock | Design: core never calls redteam/intel/infra; only downstream call core |
| **Network latency spikes inter-service** | Tool call timeouts | HTTP timeouts (5s default); circuit breaker + retry logic |
| **Config drift across services** | Inconsistent behavior | Shared config file + atomic reload via gateway |
| **Billing deduction race condition** | Double-charge or credit loss | Optimistic locking + idempotent keys (tool_call_id) |
| **Infra service down → billing stalled** | Revenue loss | Cache billing events locally; sync on recovery |

---

## Post-Deployment Optimization Opportunities

Once microservices are stable (Weeks 13+):

1. **Horizontal Scaling**
   - Run 3x loom-core instances behind load balancer
   - Run 2x loom-redteam for parallel fuzzing
   - Singleton loom-infra (billing must be single source of truth)

2. **Kubernetes Migration**
   - Replace Docker Compose with Helm charts
   - Auto-scaling based on CPU/memory/custom metrics
   - Service mesh (Istio) for observability + resilience

3. **Data Pipeline Optimization**
   - Separate read cache (loom-cache) to Redis
   - Separate session store to DynamoDB or Postgres
   - Config hot-reload without gateway restart

4. **API Gateway Enhancement**
   - Add GraphQL endpoint (if user demand)
   - WebSocket support for streaming results
   - gRPC for internal service calls (faster than HTTP/JSON)

5. **Monitoring & Observability**
   - Instrument all services with OpenTelemetry
   - Deploy Jaeger for distributed tracing
   - Deploy Loki for log aggregation
   - Deploy Prometheus + Grafana for metrics

---

## References

- **FastMCP:** https://github.com/anthropics/mcp/tree/main/python (if available)
- **Docker Compose best practices:** https://docs.docker.com/compose/gettingstarted/
- **Microservice patterns:** https://microservices.io/
- **Kubernetes:** https://kubernetes.io/ (post-Compose)

---

## Appendix: Tool Distribution Details

### loom-core (128 tools)

**Search (22):**
research_search, research_deep, multi_search, exa, tavily, firecrawl, brave, ddgs, arxiv, wikipedia, hn_reddit, newsapi, coindesk, coinmarketcap, binance, ahmia, darksearch, ummro_rag, onionsearch, torcrawl, darkweb_cti, robin_osint, investing, youtube_transcripts

**Fetch (12):**
research_fetch, research_spider, research_markdown, research_camoufox, research_botasaurus, cache_stats, cache_clear, + browser session wrappers

**LLM (18):**
research_llm_summarize, research_llm_extract, research_llm_classify, research_llm_translate, research_llm_expand, research_llm_answer, research_llm_embed, research_llm_chat, research_ask_all_models, + multi_llm variants

**Knowledge (14):**
research_github, research_knowledge_graph, research_fact_checker, research_trend_predictor, detect_language, wayback, rss_monitor, text_analyze, pdf_extract, screenshot, image_intel, geoip_local, report_generator, + 1 more

**Session/Config (8):**
research_session_open, research_session_list, research_session_close, research_config_get, research_config_set, research_config_reload, research_health_check, pool_stats, pool_reset

**Infrastructure (34):**
api_version, audit_log, tracing, logging, error handling, cache mgmt, config validation, rate_limiter, auth, offline_mode, cicd, circuit_breaker, backoff_dlq, credentials_vault, context_manager, chain_composer, semantic_cache, param_sweeper, tool_recommender, benchmark_suite, capability_matrix, dashboard, metrics_collection, + 11 more

### loom-redteam (156 tools)

**Reframing Strategies (67 strategies across 32 modules):**
All 957 strategies organized by: core, advanced, encoding, jailbreak, reasoning, persona, format_exploit, attention, legal, multiturn, specialized, novel_2026, multimodal, agent_tool, token_repr, reasoning_cot, defense_evasion, research_2026, persuasion, advanced_novel, skills_extracted, guardrail_suite, arxiv_nim, reid_psychology, advanced_psychology, psychology_extended, fusion_10x, research_derived, arabic_attacks, token_smuggling + register + apply

**Adversarial Pipelines (23):**
research_adversarial_debate, research_adversarial_craft, research_daisy_chain, research_cross_model_transfer, research_context_poisoning, research_evidence_pipeline, research_model_evidence, research_orchestrate, + 15 more

**Fuzzing (18):**
research_fuzzer, research_param_sweep, research_genetic_algorithm, research_auto_experiment, research_auto_params, research_auto_pipeline, research_auto_docs, + 11 more

**Generation (22):**
research_bpj_generator, research_prompt_analyzer, research_prompt_reframe, research_psycholinguistic, research_culture_dna, research_bias_lens, research_creative, + 15 more

**Scoring (14):**
research_attack_scorer, research_unified_score, research_score_all, research_stealth_calc, research_stealth_detect, research_stealth_score, research_executability, research_quality_scorer, research_harm_assessor, research_toxicity_checker, research_danger_prescore, + 3 more

**Tracking (12):**
research_attack_tracker, research_jailbreak_evolution, research_drift_monitor, research_consistency_pressure, research_strategy_oracle, + 7 more

**Consensus/Coevolution (8):**
research_consensus_build, research_consensus_pressure, research_coevolution, + 5 more

**Specialized (4):**
research_crescendo_loop, research_reid_pipeline, research_reid_auto, research_reid_psychology

### loom-intel (189 tools)

**OSINT (28):**
research_osint_extended, research_dark_forum, research_dark_recon, research_leak_scan, research_metadata_forensics, research_stylometry, research_deception_detect, research_social_graph, research_identity_resolve, research_social_intel, + 18 more

**Dark Web (38):**
research_onion_discover, research_onion_spectra, research_cipher_mirror, research_forum_cortex, research_ghost_weave, research_dead_drop_scanner, research_darkweb_early_warning, research_dark_web_cti, research_access_tools, research_p3_tools, research_unique_tools, research_infowar_tools, research_realtime_monitor, + 25 more

**Infrastructure (26):**
research_infra_correlator, research_infra_analysis, research_passive_recon, research_threat_profile, research_threat_intel, research_ip_intel, research_domain_intel, research_cert_analyzer, research_security_headers, research_cve_lookup, research_vuln_intel, research_breach_check, research_urlhaus_lookup, research_crypto_trace, research_crypto_risk, + 11 more

**Academic (26):**
research_academic_integrity, research_hcs10_academic, research_hcs_scorer, research_gap_tools_academic, research_gap_tools_advanced, + 21 more

**Career (18):**
research_career_intel, research_career_trajectory, research_job_signals, research_job_research, research_deception_job_scanner, research_resume_intel, research_salary_synthesizer, research_job_experts, + 10 more

**Competitive (18):**
research_competitive_intel, research_competitive_monitor, research_company_intel, research_supply_chain_intel, research_signal_detection, + 13 more

**Advanced Analysis (20):**
research_persona_profile, research_radicalization_detect, research_sentiment_deep, research_network_persona, research_change_monitor, research_model_profiler, research_model_sentiment, research_policy_validator, + 12 more

**Helpers (15):**
research_dead_content, research_invisible_web, research_js_intel, research_stego_detect, + 11 more

### loom-infra (82 tools)

**Billing (32):**
All 12 billing module exports (cost_tracker, credits, customers, dashboard, isolation, meter, overage, retention, stripe_integration, tier_limiter, tiers, __init__)

**Metrics (14):**
research_metrics_*, research_benchmark_run, research_capability_matrix, + monitoring wrappers

**Communication (12):**
research_email_report, research_slack_notify, research_joplin_sync, + 9 more

**Infrastructure (18):**
research_vastai_*, research_gcp_*, research_vercel_*, research_tor_*, research_transcribe_*, research_document_*, + 6 more

**Deployment (6):**
research_cicd_*, research_config_reload, research_changelog_gen, research_credential_vault, + 2 more

---

**End of Microservice Split Plan**
