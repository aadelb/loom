# Multi-round Ask-All — Safety-Gradient Ladder design consultation

**Date:** 2026-06-08. Sources (Round 1): local **abliterated 35B** (uncensored),
**Kimi** (thinking, 15KB), **DeepSeek-reasoner** (2KB), **Codex/gpt-5.2** (8.6KB).
Loom `ask_all_models` broadcast returned near-empty; Gemini ran the retry cascade
(also = Part C 3rd opinion).

## Convergent recommendations (Round 1) → status in `research_safety_ladder`

1. **Injection** — inject L0 output as the upper rung's **assistant prefill** (+ a
   "continue, do not restart" system frame); cut the seed at **semantic boundaries**
   (after a section/thought block), not mid-token. → *Implemented* (assistant-message
   injection + `_SYSTEM` continue-frame). *Refinement TODO:* cut at semantic boundary
   instead of fixed char count.
2. **Refusal handling** — refusal-threshold gate → "context-refinement loop": resend
   L0 raw + L1 reasoning to L2 with MORE prefill; after N cycles drop a rung / fall
   back to the lower rung's output. → *Implemented* (more-prefill → reframe →
   carry-best-up; `max_refusal_retries`).
3. **Quality push** — per-dimension weighted scoring at each rung (specificity,
   executability, completeness, stealth) and carry the highest-scoring up. →
   *Implemented* (HCS score per rung, best carried up; full 31-dim via quality_max TODO).
4. **CPU scheduling** — parallelize the one slow local L0 with fast cloud L1/L2;
   race the members of a rung concurrently. → *Implemented* (asyncio.gather within a
   rung); L0 runs first (serial, semaphore=1).
5. **Logging for SFT/DPO** — log tokens, latencies, refusal reasons, verdict; flagship
   success = chosen, refusal = rejected, L0 seed = target. → *Implemented*
   (`boost_logger` JSONL: query/reframed/rung/provider/seed/response/hcs/refused/verdict/latency).
6. **Novel** — abliterated proposed a "Safety-Gradient Lattice" (dynamic constraint
   weighting by real-time risk) and DeepSeek/Codex suggested caching successful
   seed→flagship pairs as few-shots. → *Backlog* (feed boost dataset back as HCS10
   few-shots; risk-weighted rung selection).

## Backlog from the consultation (net-new, cheap)
- Cut the L0 seed at a paragraph/section boundary before prefilling (cleaner continuation).
- Score the final answer with the full 31-dim `research_quality_max` (not just HCS).
- Recycle high-HCS flagship outputs back into the HCS10 gold corpus + as few-shot seeds.
