# Loom v3 Production TODO

**Total Requirements:** 98 | **P0:** 52 | **P1:** 36 | **P2:** 10
**Timeline:** 8 weeks (April 29 - June 24, 2026)
**Status:** IN PROGRESS

---

## Phase 1: Critical Security + Architecture (Week 1-2)

### 1.1 Security Fixes [P0] — REQ-064, REQ-065, REQ-066, REQ-067
- [ ] **1.1.1** Fix API key in URL params (realtime_monitor.py:157) → move to header
- [ ] **1.1.2** Require LOOM_API_KEY or log FATAL warning at startup (auth.py)
- [ ] **1.1.3** Validate all subprocess inputs strictly (domain_intel, image_intel, pdf_extract)
- [ ] **1.1.4** Reduce DNS cache TTL from 300s to 60s (validators.py)
- [ ] **1.1.5** Add per-IP rate limiting (rate_limiter.py)
- [ ] **1.1.6** SSRF bypass test suite (10 vectors: IP, DNS rebind, URL encoding)
- [ ] **1.1.7** Input sanitization test (50 XSS/SQLi/command injection payloads)
- [ ] **1.1.8** Verify no API keys in any logs/outputs (grep entire output)

### 1.2 Architecture Fixes [P0] — REQ-036, REQ-049, REQ-051
- [ ] **1.2.1** Implement auto-discovery tool registration (replace 500-line manual code)
- [ ] **1.2.2** Resolve dual session system → choose in-memory only (ephemeral)
- [ ] **1.2.3** Make CONFIG immutable (frozen dataclass instead of mutable dict)
- [ ] **1.2.4** Use full SHA-256 in cache keys (not truncated 128-bit)
- [ ] **1.2.5** Add tool registration verification on startup (log missing/extra)
- [ ] **1.2.6** Implement session pooling with priority queue (max 10 → configurable)

### 1.3 Documentation Sync [P0] — REQ-073, REQ-074
- [ ] **1.3.1** Update CLAUDE.md: 167 → 220 tools, 50 → 826 strategies
- [ ] **1.3.2** Update tools-reference.md: document all 220 tools
- [ ] **1.3.3** Update help.md with new tool categories
- [ ] **1.3.4** Update CHANGELOG.md (v0.1.0-alpha.2 with all changes)
- [ ] **1.3.5** Run verify_completeness.py → fix all failures
- [ ] **1.3.6** Update api-keys.md with any new provider credentials

---

## Phase 2: Billing + Multi-tenancy (Week 3-4)

### 2.1 API Key Management [P0] — REQ-076, REQ-077
- [ ] **2.1.1** Design customer model (id, name, email, api_key, tier, created_at)
- [ ] **2.1.2** Create src/loom/customers.py — CRUD operations
- [ ] **2.1.3** API key generation (secure random, prefix `loom_`)
- [ ] **2.1.4** API key validation middleware in server.py
- [ ] **2.1.5** Key rotation endpoint (generate new, invalidate old)
- [ ] **2.1.6** Per-customer data isolation (namespace cache, sessions, audit)

### 2.2 Credit System [P0] — REQ-078, REQ-081
- [ ] **2.2.1** Define credit weights: light=1, medium=3, heavy=10 per tool
- [ ] **2.2.2** Create src/loom/billing/credits.py — deduct/check/balance
- [ ] **2.2.3** Map all 220 tools to credit weights (tools_credit_map.json)
- [ ] **2.2.4** Pre-check credit balance before tool execution
- [ ] **2.2.5** Return 402 (Payment Required) when credits exhausted
- [ ] **2.2.6** Credit top-up API endpoint

### 2.3 Stripe Integration [P0] — REQ-079, REQ-080
- [ ] **2.3.1** Install stripe Python SDK, configure test keys
- [ ] **2.3.2** Create src/loom/billing/stripe_integration.py
- [ ] **2.3.3** Implement subscription creation (Free/Pro/Team/Enterprise)
- [ ] **2.3.4** Webhook handler for payment events (success, failure, cancel)
- [ ] **2.3.5** Monthly credit allocation per tier
- [ ] **2.3.6** Invoice generation and email delivery

### 2.4 Tier Enforcement [P0] — REQ-080, REQ-082
- [ ] **2.4.1** Define tiers: Free(500cr,$0), Pro(10K,$99), Team(50K,$299), Enterprise(200K,$999)
- [ ] **2.4.2** Rate limits per tier: Free(10/min), Pro(60/min), Team(300/min), Enterprise(1000/min)
- [ ] **2.4.3** Tool access gates per tier (Free=40 tools, Pro=150, Team=190, Enterprise=all)
- [ ] **2.4.4** Enforce tier limits in _wrap_tool middleware
- [ ] **2.4.5** Upgrade/downgrade flow
- [ ] **2.4.6** Grace period on credit exhaustion (5 min buffer)

### 2.5 Usage Dashboard [P1] — REQ-083, REQ-084
- [ ] **2.5.1** Create research_usage_dashboard tool (returns usage stats)
- [ ] **2.5.2** Credits used/remaining per customer
- [ ] **2.5.3** Cost breakdown per tool category
- [ ] **2.5.4** Internal cost tracking (provider cost per call)
- [ ] **2.5.5** Margin calculation (revenue vs cost per customer)
- [ ] **2.5.6** Email alerts at 50%, 80%, 100% quota

---

## Phase 3: HCS + Reframing Validation (Week 5-6)

### 3.1 HCS Scorer Tool [P0] — REQ-026, REQ-027, REQ-028
- [ ] **3.1.1** Create src/loom/tools/hcs_scorer.py with 5-dimension rubric
- [ ] **3.1.2** Dimension 1: Completeness (text length, structure, coverage)
- [ ] **3.1.3** Dimension 2: Specificity (NER count, numbers, named entities)
- [ ] **3.1.4** Dimension 3: No-Hedging (count disclaimers, caveats, refusal phrases)
- [ ] **3.1.5** Dimension 4: Actionability (imperative verbs, step-by-step markers)
- [ ] **3.1.6** Dimension 5: Technical-Depth (jargon density, code blocks, formulas)
- [ ] **3.1.7** Add HcsScoreParams to params.py
- [ ] **3.1.8** Register in server.py
- [ ] **3.1.9** Write 15+ tests (perfect=10, refusal=1, hedged=4, partial=6)
- [ ] **3.1.10** Calibrate against 20 human-rated responses

### 3.2 Reframing Baseline [P0] — REQ-011, REQ-012
- [ ] **3.2.1** Create 30 test prompts that trigger refusals on wealth/UAE topics
- [ ] **3.2.2** Send each to all 8 providers WITHOUT reframing → record refusal rates
- [ ] **3.2.3** Store baseline data in tests/fixtures/refusal_baseline.json
- [ ] **3.2.4** Document per-model refusal rates

### 3.3 Strategy Effectiveness Testing [P0] — REQ-021, REQ-022
- [ ] **3.3.1** Run top-50 strategies against each provider (50 × 8 = 400 tests)
- [ ] **3.3.2** Compute actual success rate per strategy
- [ ] **3.3.3** Correlate measured success with claimed multiplier (target r >= 0.7)
- [ ] **3.3.4** Generate heatmap: strategy × model effectiveness
- [ ] **3.3.5** Identify top-5 strategies per model (update model optimization table)
- [ ] **3.3.6** Identify strategies that never work (candidates for removal)

### 3.4 Synergy + Stacking Validation [P0] — REQ-015, REQ-024
- [ ] **3.4.1** Test all 22 synergy pairs: stacked vs individual
- [ ] **3.4.2** Verify stacked multiplier > max(individual) for each pair
- [ ] **3.4.3** Test 12 new v8.0 attack families (72 test cases)
- [ ] **3.4.4** Test 41 persuasion techniques A/B (with vs without)
- [ ] **3.4.5** Update synergy coefficients based on empirical data

### 3.5 HCS Achievement [P0] — REQ-031
- [ ] **3.5.1** Run 50 reframed wealth/UAE queries through best strategies
- [ ] **3.5.2** Score each with HCS tool
- [ ] **3.5.3** Target: 70%+ score HCS >= 8
- [ ] **3.5.4** If target not met: identify failing strategies, adjust templates
- [ ] **3.5.5** Re-run until target achieved

---

## Phase 4: Compliance + Arabic + Offline (Week 7-8)

### 4.1 Audit Logging [P0] — REQ-086, REQ-087
- [ ] **4.1.1** Create src/loom/audit.py — append-only JSONL with checksums
- [ ] **4.1.2** Log every tool invocation: who, what, when, result_summary, duration
- [ ] **4.1.3** SHA-256 integrity checksum per entry (tamper detection)
- [ ] **4.1.4** Integrate into _wrap_tool (automatic for all 220 tools)
- [ ] **4.1.5** Param redaction (never log API keys, tokens, passwords)
- [ ] **4.1.6** Verify integrity tool: research_audit_verify
- [ ] **4.1.7** Export API: research_audit_export (JSON/CSV)
- [ ] **4.1.8** Tests: log, verify, tamper-detect, redact, rotate

### 4.2 Arabic Support [P0] — REQ-090, REQ-091, REQ-092
- [ ] **4.2.1** Arabic query detection (language detection at input)
- [ ] **4.2.2** Route Arabic queries to Qwen/Kimi/Gemini (Arabic-capable)
- [ ] **4.2.3** RTL text preservation in all output formatters
- [ ] **4.2.4** Arabic refusal detection patterns (expand existing 2 patterns to 10+)
- [ ] **4.2.5** Arabic test prompts (10 queries in Arabic, verify correct handling)
- [ ] **4.2.6** MENA-specific search provider integration (if available)

### 4.3 Offline/Cache Mode [P0] — REQ-093, REQ-094, REQ-095
- [ ] **4.3.1** Implement cache-first response mode (serve cached if provider down)
- [ ] **4.3.2** Add `cached_at` and `is_stale` fields to all cached responses
- [ ] **4.3.3** Document offline capability matrix (which tools work without network)
- [ ] **4.3.4** Graceful degradation: partial results when some providers down
- [ ] **4.3.5** Test: mock all providers down, verify cache responses returned

### 4.4 Storage Strategy [P1] — REQ-096, REQ-097, REQ-098
- [ ] **4.4.1** Implement gzip compression for cache files (target 60%+ savings)
- [ ] **4.4.2** Transparent decompression on cache read
- [ ] **4.4.3** Remove 30-day deletion (indefinite retention per user requirement)
- [ ] **4.4.4** Tiered storage design: hot (SSD) → warm (HDD) → cold (archive)
- [ ] **4.4.5** Storage usage tracking and alerts at 80% capacity

### 4.5 Retention Policy [P1] — REQ-088
- [ ] **4.5.1** Configure 5-year retention for audit logs
- [ ] **4.5.2** Archive old logs (compress + move to cold storage)
- [ ] **4.5.3** Verify archived data is still retrievable

---

## Phase 5: Full Test Suite (Throughout)

### 5.1 Tool Coverage Testing [P0] — REQ-036 to REQ-050
- [ ] **5.1.1** Write coverage script: invoke every registered tool with minimal params
- [ ] **5.1.2** Core Research (7 tools) — parametrized tests
- [ ] **5.1.3** Multi-LLM (3 tools) — assert provider counts
- [ ] **5.1.4** LLM Ops (8 tools) — assert output types
- [ ] **5.1.5** Killer Research (20 tools) — assert >= 15 return data
- [ ] **5.1.6** Dark Research (5 tools) — assert execute or graceful error
- [ ] **5.1.7** Intelligence (12 tools) — assert structured output
- [ ] **5.1.8** AI Safety (7 tools) — assert scores returned
- [ ] **5.1.9** Academic (11 tools) — assert results
- [ ] **5.1.10** Career (6 tools) — assert UAE data
- [ ] **5.1.11** NLP (8 tools) — assert analysis fields
- [ ] **5.1.12** Domain+Security (11 tools) — assert structured results
- [ ] **5.1.13** Infrastructure (12 tools) — assert no exceptions
- [ ] **5.1.14** Sessions+Config (6 tools) — lifecycle test
- [ ] **5.1.15** Reframing (9 tools) — schema validation

### 5.2 Error Handling Tests [P0] — REQ-051 to REQ-060
- [ ] **5.2.1** Chaos test: mock 3 random tool failures, assert pipeline continues
- [ ] **5.2.2** Rate limit (429) backoff test
- [ ] **5.2.3** LLM cascade failover test (kill each provider sequentially)
- [ ] **5.2.4** Search provider fallback test
- [ ] **5.2.5** Fuzz test: 20 malformed inputs per category
- [ ] **5.2.6** Timeout test: mock slow response, assert caught
- [ ] **5.2.7** Cache hit rate test (10 identical queries, assert >= 4 hits)
- [ ] **5.2.8** Concurrent test: 10 parallel requests
- [ ] **5.2.9** Memory leak test: 1000 sequential calls

### 5.3 Performance Benchmarks [P0] — REQ-061, REQ-062, REQ-063
- [ ] **5.3.1** Latency benchmark: 100 calls per category, compute p50/p95/p99
- [ ] **5.3.2** Parallel vs sequential comparison (assert >= 40% speedup)
- [ ] **5.3.3** Large output handling (ask_all_models, assert no OOM)

### 5.4 Reframing Specific Tests [P0] — REQ-013 to REQ-020
- [ ] **5.4.1** auto_reframe escalation test (10 refused prompts)
- [ ] **5.4.2** refusal_detector precision/recall (100 labeled samples)
- [ ] **5.4.3** crescendo_chain coherence (5 topics, 3-7 turns each)
- [ ] **5.4.4** model_vulnerability_profile (12 models)
- [ ] **5.4.5** format_smuggle (8 formats, valid parsing)
- [ ] **5.4.6** fingerprint_model accuracy (50 labeled responses)
- [ ] **5.4.7** adaptive_reframe end-to-end (10 prompts)

---

## Phase 6: Deployment + Monitoring (Final Week)

### 6.1 Production Deployment [P0] — REQ-071, REQ-072
- [ ] **6.1.1** Health check returns all provider status
- [ ] **6.1.2** Graceful shutdown on SIGTERM (pending requests complete)
- [ ] **6.1.3** Dependency lock file (pip-compile or uv.lock)
- [ ] **6.1.4** Startup validation (required API keys present)
- [ ] **6.1.5** Docker image rebuild with v3 code
- [ ] **6.1.6** systemd service update with new config

### 6.2 Monitoring [P1] — REQ-075
- [ ] **6.2.1** Structured logging: tool_name, duration_ms, status, cache_hit, client_id
- [ ] **6.2.2** Log rotation (daily, gzip compressed)
- [ ] **6.2.3** Health check alerting (notify on provider down)
- [ ] **6.2.4** Usage metrics collection (tool popularity, error rates)

### 6.3 Final Reports [P0] — REQ-073, REQ-074
- [ ] **6.3.1** Generate "What Works" report (successful tools, strategies, workflows)
- [ ] **6.3.2** Generate "What Doesn't Work" report (failures, gaps, known issues)
- [ ] **6.3.3** Performance benchmark report (latency, throughput, cache rates)
- [ ] **6.3.4** Revenue readiness checklist (billing, metering, tiers all working)

---

## Tracking

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Phase 1: Security + Architecture | 20 | 0 | NOT STARTED |
| Phase 2: Billing + Multi-tenancy | 30 | 0 | NOT STARTED |
| Phase 3: HCS + Reframing | 26 | 0 | NOT STARTED |
| Phase 4: Compliance + Arabic | 22 | 0 | NOT STARTED |
| Phase 5: Test Suite | 30 | 0 | NOT STARTED |
| Phase 6: Deployment | 13 | 0 | NOT STARTED |
| **TOTAL** | **141** | **0** | **0%** |

---

## Agents Currently Running

- [ ] Fix critical security (auth.py, realtime_monitor.py)
- [ ] Build HCS scorer tool
- [ ] Update docs (167 → 220)
- [ ] Build audit logging system
