# LOOM MCP SERVER — 710 TOOLS DEEP AUDIT REPORT

**Audit Date:** 2026-05-04  
**Tools Scanned:** 710 unique `research_*` functions across `src/loom/tools/*.py` and `src/loom/*.py`  
**Registered Tools:** 743 names in registration files (some duplicates across categories)  
**Unregistered Tools:** 21 functions exist in code but are never registered with MCP  
**Orchestrators Analyzed:** `smart_router.py`, `universal_orchestrator.py`, `orchestrator.py`, `auto_pipeline.py`, `full_pipeline.py`, `deep.py`

---

## 1. DUPLICATES — SAME FUNCTIONALITY, DIFFERENT NAMES

### 🔴 CRITICAL: Same Function Name, Different Modules (Name Collisions)
These cause import ambiguity and shadowing. The registration system may register the wrong implementation depending on import order.

| Function Name | Module A | Module B | Risk |
|--------------|----------|----------|------|
| `research_stealth_score` | `stealth_score.py` | `stealth_scorer.py` | **HIGH** — registration imports `stealth_scorer` in server.py but `stealth_score` is also referenced in `registrations/research.py` via `loom.tools.mod` (which doesn't exist) |
| `research_stealth_detect` | `stealth_detect.py` | `stealth_detector.py` (src/loom/) | **HIGH** — server.py imports from `stealth_detector.py`, but `stealth_detect.py` also exists in tools/ |
| `research_cache_stats` | `cache_mgmt.py` | `response_cache.py` | **MEDIUM** — both return "cache stats" but for entirely different caches (file cache vs in-memory response cache). Users cannot distinguish. |

**Fix:** Rename to disambiguate: `research_file_cache_stats`, `research_response_cache_stats`, `research_stealth_score_v2`, `research_stealth_detect_v2`.

### 🟠 NEAR-EXACT DUPLICATES (should merge)

| Tool A | Tool B | Overlap | Utilization |
|--------|--------|---------|-------------|
| `research_ask_all_llms` (multi_llm.py) | `research_ask_all_models` (ask_all_models.py) | Both query ALL configured LLM providers in parallel and return comparison metrics (responses, fastest, refused count). `ask_all_models` adds CLI tool support and more model metadata. | **6/10** |
| `research_consensus` (creative.py) | `research_model_consensus` (model_compare.py) | Both aggregate multi-model responses into a consensus view. `creative.py` uses search engines; `model_compare.py` takes pre-collected responses. | **5/10** |
| `research_model_consensus` (model_compare.py) | `research_multi_consensus` (model_consensus.py) | Both query multiple LLMs and find agreement. `model_consensus.py` adds confidence scoring. | **5/10** |
| `research_consensus_build` (consensus_builder.py) | `research_multi_consensus` (model_consensus.py) | Both orchestrate multi-model consensus. `consensus_builder.py` adds pressure tactics. | **4/10** |
| `research_audit_export` (audit_log.py) | `research_audit_trail` (compliance_report.py) | Both export/query audit records. Different filter syntax. | **4/10** |
| `research_audit_export` (server.py wrapper) | `research_audit_export` (audit_log.py) | Server re-implements wrapper around `loom.audit.export_audit` instead of calling the tool directly. | **3/10** |

**Recommendation:** Merge `ask_all_llms` into `ask_all_models` (keep the richer one). Merge all consensus tools into `research_consensus` with a `method` parameter (`search_based`, `response_based`, `pressure`). Merge audit tools into `research_audit` with `action` parameter.

---

## 2. DEAD CODE — NEVER REGISTERED, NEVER CALLED

### 🔴 UNREGISTERED TOOLS (21 functions exist but are invisible to MCP)

These functions are defined in Python modules but never imported into any registration file (`registrations/*.py`) or `server.py`:

| Tool | Module | Why It's Dead | Utilization |
|------|--------|---------------|-------------|
| `research_auth_create_token` | `mcp_auth.py` | Never imported in registrations | **1/10** |
| `research_auth_revoke` | `mcp_auth.py` | Never imported in registrations | **1/10** |
| `research_auth_validate` | `mcp_auth.py` | Never imported in registrations | **1/10** |
| `research_code_analysis_demo` | `demo_decorator_usage.py` | Demo tool; never imported | **1/10** |
| `research_consistency_pressure` | `consistency_pressure.py` | Registration file has `if False: pass` block (explicit skip) | **2/10** |
| `research_consistency_pressure_history` | `consistency_pressure.py` | Same — skipped in research.py | **2/10** |
| `research_consistency_pressure_record` | `consistency_pressure.py` | Same — skipped in research.py | **2/10** |
| `research_constraint_optimize` | `constraint_optimizer.py` | Same — skipped in research.py (`if False: pass`) | **2/10** |
| `research_data_transform_demo` | `demo_decorator_usage.py` | Demo tool; never imported | **1/10** |
| `research_defi_security_audit` | `ethereum_tools.py` | Never imported in registrations | **2/10** |
| `research_epistemic_score` | `epistemic_score.py` | Registration says "has no research_* functions" but it does — AST scan missed it or it's sync not async | **2/10** |
| `research_ethereum_tx_decode` | `ethereum_tools.py` | Never imported in registrations | **2/10** |
| `research_exif_extract` | `image_intel.py` | Never imported in registrations | **2/10** |
| `research_geoip_local` | `geoip_local.py` | Never imported in registrations | **2/10** |
| `research_redis_flush_cache` | `redis_tools.py` | Never imported in registrations | **2/10** |
| `research_redis_stats` | `redis_tools.py` | Never imported in registrations | **2/10** |
| `research_sandbox_run` | `sandbox_tools.py` | Never imported in registrations | **2/10** |
| `research_sandbox_status` | `sandbox_tools.py` | Never imported in registrations | **2/10** |
| `research_social_graph_demo` | `social_graph.py` (likely) | Never imported in registrations | **1/10** |
| `research_threat_profile_demo` | `threat_profile.py` (likely) | Never imported in registrations | **1/10** |

### 🔴 BROKEN IMPORT REFERENCE

| Reference | Issue |
|-----------|-------|
| `loom.tools.mod` | `registrations/research.py` line ~847 imports `research_attack_score`, `research_stealth_score`, etc. from `loom.tools.mod`. **This module does not exist.** It causes an ImportError on every startup. These tools are duplicated elsewhere (attack_scorer.py, stealth_scorer.py) so the error is silently swallowed by `suppress(ImportError)`, but it masks real failures. |

### 🟡 ORPHANED TOOLS (registered but never called by any pipeline)

These are registered with MCP but no pipeline, orchestrator, or other tool ever invokes them:

| Tool | Module | Never Called By | Utilization |
|------|--------|-----------------|-------------|
| `research_capability_matrix` | `capability_matrix.py` | No pipeline uses this for dynamic routing | **3/10** |
| `research_find_tools_by_capability` | `capability_matrix.py` | No pipeline uses this for dynamic routing | **3/10** |
| `research_tool_dependencies` | `dependency_graph.py` | No pipeline reads dependency graph | **2/10** |
| `research_tool_impact` | `dependency_graph.py` | No pipeline reads impact analysis | **2/10** |
| `research_meta_learn` | `meta_learner.py` | Never invoked by auto-pipeline or full-pipeline to improve strategies | **3/10** |
| `research_estimate_cost` | `cost_estimator.py` | `deep.py` and `full_pipeline.py` hardcode cost logic but never call this tool | **3/10** |
| `research_cost_summary` | `cost_estimator.py` | No pipeline aggregates costs via this tool | **2/10** |
| `research_explain_bypass` | `explainability.py` | Never called after escalation failures in `full_pipeline.py` | **3/10** |
| `research_vulnerability_map` | `explainability.py` | Never called by reframe tools | **2/10** |
| `research_evolve_strategies` | `strategy_evolution.py` | Never called by any pipeline | **3/10** |
| `research_strategy_oracle` | `strategy_oracle.py` | Never called by `full_pipeline.py` or `auto_pipeline.py` | **3/10** |
| `research_lifetime_predict` | `lifetime_oracle.py` | Never integrated into publish workflows | **2/10** |
| `research_predict_resilience` | `resilience_predictor.py` | Never called by any pipeline | **2/10** |
| `research_genetic_fuzz` | `genetic_fuzzer.py` | Never called by automated test pipelines | **3/10** |
| `research_coevolve` | `coevolution.py` | Never called by any pipeline | **3/10** |
| `research_geodesic_path` | `geodesic_forcing.py` | Never called by reframe pipeline | **2/10** |
| `research_functor_translate` | `functor_map.py` | Never called by any pipeline | **2/10** |
| `research_attractor_trap` | `strange_attractors.py` | Never called by any pipeline | **2/10** |
| `research_holographic_encode` | `holographic_payload.py` | Never called by RAG attack pipelines | **2/10** |
| `research_memetic_simulate` | `memetic_simulator.py` | Never called by any pipeline | **2/10** |
| `research_neuromorphic_schedule` | `neuromorphic.py` | Never called by job scheduler | **2/10** |
| `research_chronos_reverse` | `chronos.py` | Never called by any pipeline | **2/10** |
| `research_ghost_protocol` | `signal_detection.py` | Never called by OSINT pipelines | **3/10** |
| `research_temporal_anomaly` | `signal_detection.py` | Never called by OSINT pipelines | **3/10** |
| `research_sec_tracker` | `signal_detection.py` | Never called by OSINT pipelines | **3/10** |
| `research_behavioral_fingerprint` | `osint_extended.py` | Never called by persona pipelines | **3/10** |
| `research_social_engineering_score` | `osint_extended.py` | Never called by OSINT pipelines | **3/10** |

---

## 3. MISSING FROM ORCHESTRATION

### 🔴 smart_router / universal_orchestrator gaps

Both `smart_router.py` and `universal_orchestrator.py` scan `src/loom/tools/*.py` via AST to discover tools. **They completely miss tools in `src/loom/*.py`** because they only scan the `tools/` subdirectory.

**Tools invisible to auto-routing:**
- `research_orchestrate` (orchestrator.py)
- `research_reid_pipeline` (reid_pipeline.py)
- `research_crescendo_loop` (crescendo_loop.py)
- `research_full_spectrum` (server.py)
- `research_danger_prescore` (danger_prescore.py)
- `research_quality_score` (quality_scorer.py)
- `research_evidence_pipeline` (evidence_pipeline.py)
- `research_context_poison` (context_poisoning.py)
- `research_adversarial_debate` (adversarial_debate.py)
- `research_model_evidence` (model_evidence.py)
- `research_target_orchestrate` (target_orchestrator.py)
- `research_mcp_security_scan` (mcp_security.py)
- `research_cicd_run` (cicd.py)
- `research_consensus_build` / `research_consensus_pressure` (consensus_builder.py)
- `research_benchmark_run` (benchmarks.py)
- `research_score_all` (scoring.py)
- `research_unified_score` (unified_scorer.py)
- `research_model_profile` (model_profiler.py)
- `research_pg_migrate` / `research_pg_status` (pg_store.py)
- `research_pool_stats` / `research_pool_reset` (sqlite_pool.py)

**Impact:** The "universal" orchestrator cannot route to ~30 core pipeline tools. It only knows about the 500+ granular tools in `tools/`.

### 🔴 orchestrator.py uses fantasy step names

`orchestrator.py` defines pipelines like `research_pipeline` with steps `["search_multi", "fetch_top", "extract_markdown", "synthesize_llm", "score_hcs"]`. **These are string literals that do not map to actual tool function names.** The orchestrator returns a JSON plan but never executes it. There is no executor that maps `"search_multi"` → `research_multi_search` or `"score_hcs"` → `research_hcs_score`.

### 🟡 auto_pipeline.py has naive selection logic

`auto_pipeline.py` `_select_tools()` picks tools by keyword overlap against docstrings. If no overlap is found, it falls back to `next(iter(registry.keys()))` — meaning it will pick an arbitrary tool (alphabetically first) for unrelated queries. It also ignores tool categories and never uses `research_capability_matrix` or `research_find_tools_by_capability`.

---

## 4. COMBINABLE TOOLS — FRAGMENTED FAMILIES

### Browser / Fetch Family (13 tools → 1 tool with `backend` param)

**Current:** `research_fetch`, `research_camoufox`, `research_botasaurus`, `research_cloak_fetch`, `research_cloak_extract`, `research_cloak_session`, `research_nodriver_fetch`, `research_nodriver_extract`, `research_nodriver_session`, `research_lightpanda_fetch`, `research_lightpanda_batch`, `research_markdown`, `research_stealth_browser` (cyberscraper.py)

**Proposed:** `research_fetch(url, backend="auto", extract=False, session=False)` where `backend ∈ ["http", "camoufox", "botasaurus", "cloak", "nodriver", "lightpanda", "markdown", "auto"]`.

**Utilization of family:** 7/10 (individually used but fragmented)

### HCS Scoring Family (6 tools → 1 tool with `mode` param)

**Current:** `research_hcs_score`, `research_hcs_score_prompt`, `research_hcs_score_response`, `research_hcs_score_full`, `research_hcs_compare`, `research_hcs_batch`

**Proposed:** `research_hcs_score(text, query=None, mode="auto", compare_against=None)` where `mode ∈ ["auto", "prompt_only", "response_only", "full", "compare", "batch"]`.

**Utilization of family:** 6/10

### Graph Family (8 tools → 1 tool with `action` param)

**Current:** `research_graph_scrape`, `research_knowledge_extract`, `research_multi_page_graph` (graph_scraper.py), `research_knowledge_graph` (knowledge_graph.py), `research_graph_store`, `research_graph_query`, `research_graph_visualize` (neo4j_backend.py), `research_graph_analyze` (graph_analysis.py)

**Proposed:** `research_graph(action, ...)` where `action ∈ ["scrape", "extract", "store", "query", "visualize", "analyze", "build"]`.

**Utilization of family:** 5/10

### Cache Management Family (5 tools → 1 tool with `action` param)

**Current:** `research_cache_stats` (×2), `research_cache_clear`, `research_cache_analyze`, `research_cache_optimize`, `research_cache_store`, `research_cache_lookup`

**Proposed:** `research_cache(action, cache_type="file", ...)` where `action ∈ ["stats", "clear", "analyze", "optimize", "store", "lookup"]`.

**Utilization of family:** 5/10

### Audit / Compliance Family (4 tools → 1 tool with `action` param)

**Current:** `research_audit_record`, `research_audit_query`, `research_audit_export` (audit_log.py), `research_audit_trail`, `research_compliance_report` (compliance_report.py)

**Proposed:** `research_audit(action, ...)` where `action ∈ ["record", "query", "export", "trail", "compliance"]`.

**Utilization of family:** 4/10

### Stealth Analysis Family (4 tools → 1 tool with `action` param)

**Current:** `research_stealth_score` (×2), `research_stealth_detect` (×2), `research_stealth_score` (stealth_scorer.py), `research_stealth_detect` (stealth_detector.py)

**Proposed:** `research_stealth(action, ...)` where `action ∈ ["score", "detect"]`.

**Utilization of family:** 4/10

### Consensus Family (5 tools → 1 tool with `method` param)

**Current:** `research_consensus` (creative.py), `research_model_consensus` (model_compare.py), `research_multi_consensus` (model_consensus.py), `research_consensus_build`, `research_consensus_pressure` (consensus_builder.py)

**Proposed:** `research_consensus(responses, method="auto")` where `method ∈ ["search", "response_vote", "llm_agreement", "pressure", "build"]`.

**Utilization of family:** 5/10

### Job / Career Family (8+ tools with heavy overlap)

**Current:** `research_job_search`, `research_job_market` (job_research.py), `research_job_submit`, `research_job_status`, `research_job_result`, `research_job_list`, `research_job_cancel` (job_tools.py), `research_funding_signal`, `research_stealth_hire_scanner`, `research_interviewer_profiler` (job_signals.py), `research_company_diligence`, `research_salary_intelligence` (company_intel.py), `research_career_trajectory`, `research_market_velocity` (career_trajectory.py), `research_map_research_to_product`, `research_translate_academic_skills` (career_intel.py), `research_resume_intel`, `research_interview_prep` (resume_intel.py)

**Overlap:** `research_job_search` and `research_job_market` both aggregate job listings. `research_company_diligence` and `research_career_trajectory` both profile companies. This family has **16+ tools** that could be reduced to **3** (`research_job_search`, `research_company_intel`, `research_career_plan`).

**Utilization of family:** 5/10

---

## 5. MISSING CONNECTIONS BETWEEN RELATED TOOLS

### 🔴 Pipeline tools don't compose

| Caller | Should Call | Why Missing |
|--------|-------------|-------------|
| `research_full_pipeline` | `research_auto_pipeline` | `full_pipeline.py` hardcodes its own 5-stage logic instead of delegating to `auto_pipeline.py`'s goal decomposition |
| `research_deep` | `research_full_pipeline` | These are parallel mega-pipelines. `deep.py` does 12 stages; `full_pipeline.py` does 5. They should share a common core. |
| `research_orchestrate` (orchestrator.py) | Any tool executor | It returns JSON plans with step names like `"score_hcs"` but never invokes the actual tool functions. It's a recommendation engine, not an orchestrator. |
| `research_auto_pipeline` | `research_capability_matrix` | `auto_pipeline.py` scans tools via AST but never uses `capability_matrix.py`'s structured I/O analysis to validate compatibility between pipeline stages. |
| `research_smart_router` | `research_auto_pipeline` | Router returns a single tool; it never chains tools into a pipeline even when the query clearly needs multiple stages. |

### 🟡 Cost / Health / Safety tools are ignored by spendy pipelines

| Spender | Should Call (but doesn't) | Impact |
|---------|---------------------------|--------|
| `research_deep` | `research_estimate_cost` | Hardcodes `$0.50` cap but never uses the cost estimator tool to preview expenses. |
| `research_full_pipeline` | `research_estimate_cost` | No cost preview before running LLM cascade. |
| `research_full_pipeline` | `research_health_check_all` | Doesn't verify providers are healthy before burning API calls. |
| `research_full_pipeline` | `research_explain_bypass` | After escalation failures, it doesn't ask "why did this strategy fail?" |
| `research_deep` | `research_misinfo_check` | Only runs if explicitly enabled; should auto-enable for news queries. |
| `research_deep` | `research_red_team` | Only runs if explicitly enabled; should auto-enable for controversial claims. |

### 🟡 Learning loop is broken

| Teacher | Student | Connection Missing |
|---------|---------|-------------------|
| `research_meta_learn` | `research_full_pipeline` | Pipeline never feeds results back to meta-learner to improve strategy selection. |
| `research_evolve_strategies` | `research_strategy_cache` | Evolver never writes newly evolved strategies to the cache. |
| `research_strategy_oracle` | `research_auto_reframe` | Auto-reframer never consults the oracle for optimal strategy per model. |
| `research_jailbreak_evolution_record` | `research_full_pipeline` | Pipeline never records which strategies worked/failed per model version. |
| `research_hitl_submit` / `research_hitl_evaluate` | `research_meta_learn` | Human evaluations never feed into meta-learning loop. |

### 🟡 Intelligence tools don't chain

| Stage 1 | Stage 2 | Missing Link |
|---------|---------|--------------|
| `research_leak_scan` | `research_breach_check` | Leak scanner never cross-references breach DB. |
| `research_dark_forum` | `research_forum_cortex` | Forum aggregator never sends raw data to cortex analyzer. |
| `research_ioc_enrich` | `research_misp_lookup` | IOC enricher never queries MISP. |
| `research_threat_profile` | `research_predict_safety_update` | Threat profiler never asks safety predictor for timeline. |
| `research_behavioral_fingerprint` | `research_identity_resolve` | Fingerprint builder never feeds into identity resolver. |

---

## 6. UTILIZATION HEATMAP BY CATEGORY

| Category | Tool Count | Avg Utilization | Notes |
|----------|-----------|-----------------|-------|
| **Core fetch/search** | ~20 | **8/10** | `fetch`, `search`, `multi_search`, `markdown`, `spider` are heavily used by `deep.py` |
| **LLM wrappers** | ~10 | **7/10** | `llm_chat`, `llm_summarize`, `llm_answer`, `ask_all_models` used by pipelines |
| **Reframe / jailbreak** | ~25 | **6/10** | Core reframers used by `full_pipeline.py`, but many novel strategies are orphaned |
| **HCS scoring** | ~8 | **6/10** | Used by `full_pipeline.py` but fragmented |
| **OSINT / intel** | ~80 | **4/10** | Many registered but never chained; lots of solo tools |
| **Infra / devops** | ~50 | **4/10** | Health, cache, metrics are registered but pipelines ignore them |
| **Academic / gap tools** | ~40 | **3/10** | Specialized tools (citation cartography, grant forensics) are never called |
| **Adversarial / red team** | ~30 | **5/10** | Core ones used, but advanced ones (swarm, coevolve, genetic fuzz) are dead |
| **Career / job** | ~16 | **3/10** | Massive overlap, low pipeline integration |
| **Graph / knowledge** | ~8 | **4/10** | Fragmented across 4 modules, no unified API |
| **Stealth / browser** | ~13 | **5/10** | Fragmented fetch backends |
| **Blockchain / crypto** | ~4 | **3/10** | `crypto_trace`, `crypto_risk_score` never called by OSINT pipelines |
| **Demo / utility** | ~5 | **1/10** | `demo_decorator_usage.py`, demo tools should be removed from prod |

---

## 7. PRIORITY ACTION ITEMS

### P0 — Fix immediately
1. **Delete or fix `loom.tools.mod` reference** in `registrations/research.py` — it causes a guaranteed ImportError on every startup.
2. **Resolve function name collisions:** `research_stealth_score`, `research_stealth_detect`, `research_cache_stats` exist in multiple modules.
3. **Register or delete 21 unregistered tools** — they clutter the codebase and confuse audits.

### P1 — Merge this month
4. **Merge `ask_all_llms` → `ask_all_models`** — keep the richer implementation.
5. **Unify browser fetch family** under `research_fetch(backend=...)`.
6. **Unify HCS scoring** under `research_hcs_score(mode=...)`.
7. **Unify cache tools** under `research_cache(action=...)`.
8. **Unify audit tools** under `research_audit(action=...)`.

### P2 — Architectural fixes
9. **Make `orchestrator.py` executable** — map string step names to actual tool functions and execute them.
10. **Teach `universal_orchestrator.py` about `src/loom/*.py`** — expand AST scan scope.
11. **Connect `research_estimate_cost` to `research_deep` and `research_full_pipeline`** — preview before spend.
12. **Connect `research_meta_learn` to `research_full_pipeline`** — close the learning loop.
13. **Make `research_capability_matrix` useful** — `auto_pipeline.py` should validate stage compatibility using it.

### P3 — Cleanup
14. **Remove demo tools** (`research_code_analysis_demo`, `research_data_transform_demo`, `research_social_graph_demo`, `research_threat_profile_demo`) from production.
15. **Consolidate career/job tools** from 16 → 3.
16. **Consolidate graph tools** from 8 → 1 with actions.

---

## APPENDIX: Audit Methodology

1. **Discovery:** `grep -r "^async def research_\|^def research_" src/loom/` → 710 unique functions
2. **Registration check:** Extracted all `research_*` names from `registrations/*.py` + `server.py` → 743 registered names
3. **Unregistered diff:** `comm -23 all_tools.txt registered_tools.txt` → 21 unregistered
4. **Pipeline reachability:** Grepped `deep.py`, `full_pipeline.py`, `auto_pipeline.py`, `orchestrator.py`, `smart_router.py`, `universal_orchestrator.py` for tool call references
5. **Duplicate detection:** Manual review of function names + docstring similarity + parameter overlap
6. **Connection mapping:** Traced which tools import/call which other tools via static analysis
