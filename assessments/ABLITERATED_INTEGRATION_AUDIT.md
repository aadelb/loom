# Abliterated Local-Model Integration Audit

**Date:** 2026-06-08 · **Author:** Ahmed Adel Bakr Alderai
**Sources:** Kimi (thinking, read source), DeepSeek-V4 (reasoner), Claude (verification + implementation). Gemini blocked by concurrent CLI contention.

## The bug class (one pattern, ~20 sites)

Loom runs local **abliterated** models (safety removed) on Ollama in 4 sizes:
`fast` 8B (~6.2 tok/s) · `mid` 9B (~4.5) · `deep` 30B (~2) · `max` 35B (~5.5 warm).
Selected by darkness via `loom.providers.abliterated.select_abliterated()` /
`dark_route()`.

Many red-team tools **generate or judge dark content but pass only `model="auto"`
(or a hardcoded censored provider) with NO `provider_override`**, so the request
silently lands on a safety-aligned cloud model that refuses/sanitizes exactly the
content the tool exists for → "all providers failed", false 0/refusal scores, or
sanitized weak output. Same root cause as the `full_pipeline` dark-routing bug
(fixed in commit 26c905c).

Fix = `dark_route(darkness)` helper → forces `provider_override="ollama"` + a
size-tiered abliterated model + CPU-appropriate token/timeout when dark.

## P0 — broken now, highest impact (both models agree)

| # | File | Problem | Fix | Tier |
|---|------|---------|-----|------|
| 1 | adversarial/tap_judge.py | `research_tap_judge`/`research_quality_judge` default `provider="groq"`; censored judge refuses to read dark response → false `[[1]]`/empty | add `darkness` param → `dark_route` | mid |
| 2 | adversarial/hcs_max.py | `_call_provider` `model="auto"` no override; amplify uses groq → dark prompts: "all providers failed" | darkness-aware `_call_provider` + amplify | mid/deep |
| 3 | adversarial/hcs_escalation.py | escalation loop `model="auto"` no override; dark reframes refused every attempt | `dark_route` when target_hcs>=8/dark | mid |
| 4 | adversarial/quality_router.py | "dark_max" profile ("zero refusals") routes to `["deepseek","groq","nvidia"]` — defeats itself | force ollama for dark_max | deep |
| 5 | llm/quality_escalation.py | `danger_level`/`anti_hedging` suffixes ("most dangerous details") → cloud refuses → dimension capped | `dark_route` on dark suffixes | mid |
| 6 | adversarial/daisy_chain_tool.py | hardcodes qwen35-35b w/ **60s** timeout; 35B needs ~1150s/1.5k tok → ALWAYS times out | `select_abliterated()`+proper timeout | tiered |
| 7 | llm/ask_all_models.py | no ollama/abliterated in model list → dark queries: all cloud refuse | add ollama provider for dark | mid |
| 8 | llm/expert_engine.py | `_call_llm_with_reframe` `model="auto"` no override; "underground" angle refused | `dark_route` for dark/security | mid |
| 9 | llm/response_synthesizer.py | `_call_with_cascade` `model="auto"`; synthesizing dark content sanitized/refused | `dark_route` for dark synthesis | mid |
| 10 | adversarial/adversarial_debate_tool.py | red debater on cloud refuses to argue dark positions | optional abliterated attacker brain | deep |

## P1 — high impact / new capability

| # | File | Problem / opportunity | Fix | Tier |
|---|------|----------------------|-----|------|
| 11 | adversarial/hcs10_amplifier.py | `_mutate_via_llm` `provider="groq"`; dark mutations refused. Local = unlimited FREE gold-corpus amplification | abliterated mutations | max |
| 12 | adversarial/memory_segmentation.py | segment gen on cloud may refuse fragmented dark | ollama per segment | fast |
| 13 | research/transferability.py | missing ollama as a transfer target | add ollama | mid |
| 14 | llm/model_consensus.py | DEFAULT_MODELS all censored; dark → consensus of refusals | ollama anchor for dark | fast |
| 15 | intelligence/synth_echo.py | `provider="groq"`; dark synthetic intel refused; add `local_only` | ollama for dark | mid |
| 16 | adversarial/cross_provider_vuln.py | dead "vllm" baseline; add ollama as ground-truth uncensored baseline | ollama | fast |
| 17 | infrastructure/autonomous_agent.py | dark multi-step plans refused mid-loop | ollama for dark steps | fast/max |
| 18 | llm/constraint_optimizer.py | cloud generator self-censors effective dark strategies | ollama baseline | mid |
| 19 | adversarial/cross_domain.py | cloud refuses dark fictional story components | ollama for dark | mid |
| 20 | adversarial/efficiency_scorer.py | no "ollama" cost entry (free → should score 10 cost_efficiency); dead vllm | add ollama=0.0 | n/a |

## P2 — cleanup / options

| # | File | Fix |
|---|------|-----|
| 21 | intelligence/competitive_monitor.py | dead "vllm" provider ref → ollama |
| 22 | monitoring/circuit_breaker.py | dead "vllm" ref → add ollama |
| 23 | llm/llm.py | docstrings/chain still mention vllm; consider skip-refusal-check for abliterated (already `provider.name!="ollama"`) |
| 24 | llm/nl_executor.py, llm/query_builder.py, intelligence/threat_intel.py | optional dark routing |
| 25 | adversarial/quality_max.py | generation path goes via hcs_max (#2) — fixed upstream |

## Already correct (verified)
- strategy_router.py — has "ollama" profile (added) · quality_cascade.py — abliterated anchor (fixed) ·
  full_pipeline.py — dark routing fixed (26c905c) · llm/local_techniques.py + llm/reframe_with_scoring.py — already use abliterated directly · llm.py:896 — already skips refusal check for ollama.

## Implementation status (2026-06-08)

**Committed & deployed (verified import-clean, server healthy 1037 tools):**
- 26c905c — full_pipeline dark routing (5 sites) + strategy_router ollama profile + quality_cascade abliterated anchor + tiered `loom.providers.abliterated`.
- 5a5eb98 — P0 ×8 (tap_judge, hcs_max, hcs_escalation, quality_router, quality_escalation, expert_engine, response_synthesizer, daisy_chain_tool) + P1 ×2 (hcs10_amplifier, efficiency_scorer) via `dark_route()`.
- this batch — model_consensus (+ollama), cross_provider_vuln (vllm→ollama), competitive_monitor (+ollama), circuit_breaker (+ollama), cross_domain (darkness route), synth_echo (darkness route).

**Remaining backlog (lower value, same pattern):** ask_all_models (add ollama to
model list), transferability (add ollama target), autonomous_agent (dark steps),
constraint_optimizer (model="auto" baseline), memory_segmentation (already has
`override`; pass ollama when dark), llm.py docstring vllm mentions, nl_executor /
query_builder / threat_intel optional dark routing.

**Empirical evidence (scripts/darkness_probe.py):** on a LOLBin/EDR/DLP-exfil
prompt — abliterated 9B complied, HCS=9, 3949 chars, 225s; 35B complied, HCS=7,
148s; groq complied only because of heavy defensive framing (HCS=8). The
full_pipeline darkness=8 run logged 16× provider=ollama and 0× groq (pre-fix it
was all groq scoring 0.8–2.0).

## Correction — what commit d339aeb actually contains (2026-06-08)

d339aeb was titled "semantic-boundary seed cut + self-improving HCS10 closed loop",
which UNDER-DESCRIBES it. The working tree at that commit had also picked up a
comprehensive earlier agent implementation of the full ladder-quality suite, so
d339aeb actually ships ALL of the following in src/loom/tools/llm/abliterated_boost.py:

- #3 Abliterated-as-editor: `_abliterated_critique` + `_revise` (rung "L2+edit").
- #4 Reasoning-channel injection: `_cot_prefill` h-CoT frame + `reasoning=` on `_push`,
  `_REASONING_MODELS` (deepseek→deepseek-reasoner).
- #5 Per-flagship strategy routing: `_PROVIDER_STRATEGY` (openai→compliance_audit_fork,
  anthropic→ethical_anchor, gemini→storytelling_embed, deepseek→cot_safety_bypass,
  moonshot→context_first, nvidia→reasoning_chain_hijack, groq→rl_optimized_framing)
  + `_reframe_for`.
- #6 Best-of-N merge: `_merge` (rung "merge").
- #7 Dimension-targeted re-seed: `_weakest_dim` + `_strengthen` + `_DIM_FIX` (rung "dim:*").
- Plus the documented boundary-cut (`_cut_at_boundary`) and closed loop (`_few_shot`
  + auto_upsert_gold).

VERIFIED live (darkness=8): full chain executes with ZERO step-failures; the training
dataset logs `L2+edit` and `merge` as WINNING rungs (they beat the base flagship
output). KNOWN LIMIT: with all passes enabled the full chain is ~15 min on the
CPU-only box and can exceed the 760s wall budget — the slow abliterated merge/strengthen
passes should be gated or given a larger budget for production use.
