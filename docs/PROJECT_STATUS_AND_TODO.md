# Loom v3 — Project Status & Comprehensive TODO

**Audit Date:** 2026-05-18  
**Commit:** 6656608  
**Branch:** main  
**Audited by:** 4 Kimi CLI agents (thinking mode) + Claude

---

## Current Status

| Metric | Value |
|--------|-------|
| Total tools | 908 registered, 854 function definitions |
| Server | healthy, port 8788, Hetzner |
| Core retest | 88/88 PASS (100%) |
| Technique live test | 20/20 PASS (100%) |
| Total .py files | 692 in src/loom/ |
| Test files | 498 files, 12,259 test functions, 16,524 collected |
| Pydantic params | 344 model classes |
| Reframe strategies | 957 across 32 modules |
| LLM providers | 8 (Groq, NVIDIA, DeepSeek, Gemini, Moonshot, OpenAI, Anthropic, Ollama) |
| Search providers | 21 |
| Abliterated models | 5 deployed (mannix, qwen3-coder-30b, qwen35-9b, gemma3n-8b, qwen3.5) |
| Local techniques | 30/30 implemented |
| HCS pipeline | 9/10 reproducible |
| Production readiness | ~75% |

---

## What's DONE (This Session — 27 commits)

- [x] Ollama provider + 5 abliterated models deployed
- [x] Auto refusal detection → cascade to ollama
- [x] Internet-augmented generation (research_augmented_generate)
- [x] Agent loop (research_agent_loop — LLM with internet access)
- [x] Expert assessment (9 unified scorers, 51ms)
- [x] Scorer registry (singleton, lazy-init)
- [x] Scoring middleware (@with_scoring decorator)
- [x] Unified LLM client (query_llm + query_llm_uncensored)
- [x] Reframing feedback loop (research_reframe_until_hcs)
- [x] Max score engine (dual-model optimization)
- [x] Adversarial orchestrator v2 (3-tier cascade)
- [x] Brain integration (mode=max → orchestrator)
- [x] 30 local model techniques (all 5 phases)
- [x] Brain param coercion fix
- [x] Brain keyword extraction fix
- [x] Economy mode general-tool boost
- [x] Systemd services (Ollama + Loom)
- [x] `/kimi-deep-review` skill created
- [x] All CLI tools updated (Kimi v1.44.0, Gemini v0.42.0, Codex v0.130.0)
- [x] 4 bugs fixed from Kimi swarm review
- [x] Hedging stripper inconsistent returns fixed
- [x] docs/LOCAL_MODEL_TECHNIQUES_SPEC.md (30/30 complete)

---

## What's MISSING — Full TODO List

### PRIORITY 1 — Critical (Planned but NOT done)

| # | Item | Source | Status |
|---|------|--------|--------|
| 1 | Refresh token rotation + revocation blocklist | Plan: quizzical-rabbit | MISSING |
| 2 | LRU/TTL eviction policies for filesystem cache | Plan: quizzical-rabbit | MISSING |
| 3 | OpenTelemetry instrumentation (spans for providers/tools) | Plan: quizzical-rabbit | MISSING |
| 4 | CLI output formatting (`--json` flag) | Plan: quizzical-rabbit | MISSING |
| 5 | E2E journey tests (config, tool usage, session resume) | Plan: quizzical-rabbit | MISSING |
| 6 | Cross-match analysis (architecture.md vs implementation) | Plan: quizzical-rabbit | MISSING |
| 7 | Missing dependencies: `hypothesis`, `structlog` (3 test collection errors) | Test suite | MISSING |

### PRIORITY 2 — Privacy TIER 3 Integrations (10 items)

| # | Integration | Repo | Status |
|---|------------|------|--------|
| 040 | ulexecve fileless execution | mempodipog/ulexecve | STUB ONLY |
| 041 | saruman ELF binary obfuscation | elfmaster/saruman | STUB ONLY |
| 042 | flock-detection wireless surveillance | BenDavidAaron/flock-detection | STUB ONLY |
| 043 | browser-fingerprinting bot evasion | maciekopalinski/browser-fingerprinting | NOT IMPLEMENTED |
| 044 | chameleon fingerprint randomizer | lulzsec/chameleon | STUB ONLY |
| 045 | stegma multi-format steganography | jmhmcc/stegma | STUB ONLY |
| 046 | BrowserBlackBox privacy audit | dessant/bbb | STUB ONLY |
| 047 | PII-Recon exposure auditing | ru7-security/PII-Recon | STUB ONLY |
| 048 | swiftGuard macOS anti-forensics | swiftGuard-security/swiftGuard | STUB ONLY |
| 049 | steganography-python image hiding | tharukaromesh/steganography-python | STUB ONLY |

### PRIORITY 3 — Documentation & Quality

| # | Item | Status |
|---|------|--------|
| 1 | docs/PRIVACY_RESEARCH_REPORT.md referenced in CLAUDE.md | FILE MISSING |
| 2 | fetch_youtube_transcript not registered as MCP tool | EXISTS but unregistered |
| 3 | find_similar_exa not registered as MCP tool | EXISTS but unregistered |
| 4 | Full test suite run (16,524 tests — never completed) | UNTESTED |
| 5 | 15 uncommitted files (WIP fix scripts, reports) | CLEANUP NEEDED |
| 6 | Microservice architecture plan (docs/microservice-plan.md) | PLANNED, NOT EXECUTED |
| 7 | docs/NEXT_STEPS.md — 3 remaining items out of 136 | 97.8% DONE |

### PRIORITY 4 — Plan File Tasks (quizzical-rabbit.md — 36 items ALL MISSING)

| Group | Items | Description |
|-------|-------|-------------|
| G1 | 3 tasks | Context coherence validation + commit |
| G2 | 3 tasks | E2E journey tests for config/tools/sessions |
| G3 | 3 tasks | Cross-match analysis report |
| G4 | 3 tasks | Refresh token rotation + revocation |
| G5 | 3 tasks | LRU/TTL cache eviction |
| G6 | 3 tasks | OpenTelemetry instrumentation |
| G7 | 3 tasks | CLI formatting + `--json` flag |
| G8 | 3 tasks | Edge case verification report |
| G9-G12 | 12 tasks | Additional validation rounds |

### PRIORITY 5 — Known Bugs (from Kimi swarm)

| # | File | Issue |
|---|------|-------|
| 1 | intelligence/vuln_intel.py | `_nvd_search()` ignores query param, fetches ALL CVEs unfiltered |
| 2 | tools/backends/zendriver_backend.py | `loop.run_until_complete()` crashes in async event loop |
| 3 | billing/credits.py | `deduct_with_idempotency()` ignores PG backend (JSON only) |
| 4 | billing/dashboard.py | `get_dashboard()` ignores PG backend |
| 5 | brain/memory.py | `_tool_pairs` never pruned after history trim |
| 6 | tools/core/spider_backend.py | `research_spider` NameError when deps missing |
| 7 | tools/intelligence/white_rabbit.py | async function with no await |
| 8 | tools/privacy/usb_monitor_tool.py | async with no await, name collision |
| 9 | tools/privacy/stego_encoder.py | `output_format` param unused |
| 10 | Multiple security/ files | Blank line between decorator and function |

### PRIORITY 6 — Production Hardening

| # | Item | Status |
|---|------|--------|
| 1 | Gemini CLI on Hetzner stuck at v0.30 (needs node upgrade) | PENDING |
| 2 | Codex CLI not installed on Hetzner | PENDING |
| 3 | `LOOM_AUDIT_SECRET` not set (audit logs unsigned) | PENDING |
| 4 | Full pytest run never completed (timeout issues on Hetzner) | PENDING |
| 5 | Ollama systemd service not started (enabled but manual) | PENDING |
| 6 | Loom systemd service not started (enabled but manual) | PENDING |

---

## Metrics Summary

| Category | Done | Total | % |
|----------|------|-------|---|
| Local Techniques | 30 | 30 | 100% |
| Privacy TIER 1 | 4 | 4 | 100% |
| Privacy TIER 2 | 4 | 4 | 100% |
| Privacy TIER 3 | 0 | 10 | 0% |
| Plan Tasks (quizzical-rabbit) | 0 | 36 | 0% |
| NEXT_STEPS.md | 133 | 136 | 97.8% |
| Core Tools Retest | 88 | 88 | 100% |
| Technique Live Test | 20 | 20 | 100% |

**Overall completion: ~75% production-ready**

---

## Recommended Next Actions (Priority Order)

1. **Fix 10 known bugs** from Kimi swarm review (P5)
2. **Register 2 unregistered tools** (youtube_transcript, find_similar_exa)
3. **Clean up 15 uncommitted files** (remove WIP scripts)
4. **Run full pytest suite** on Hetzner with `--timeout=600`
5. **Start systemd services** (ollama + loom-v3)
6. **Implement TIER 3 privacy integrations** (10 items)
7. **Execute plan G4** (refresh token rotation)
8. **Execute plan G5** (cache eviction policies)
9. **Execute plan G6** (OpenTelemetry)
10. **Write missing doc** (PRIVACY_RESEARCH_REPORT.md)
