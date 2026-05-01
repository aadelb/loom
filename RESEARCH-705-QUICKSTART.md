# RESEARCH-705: Quick Start Guide

**Goal:** Reduce Loom's API costs by 70-85% while maintaining attack success rate.

**Current cost-per-success:** ~$0.34
**Target cost-per-success:** <$0.10

---

## What This Research Contains

| File | What | Read if... |
|------|------|-----------|
| `RESEARCH-705-SUMMARY.md` | 5-minute executive summary | You want the quick version |
| `docs/RESEARCH-705-COST-OPTIMIZATION.md` | Detailed 1000+ line analysis | You're implementing the solutions |
| `docs/RESEARCH-705-DEPLOYMENT.md` | How to run the research script | You want live research data on Hetzner |
| `scripts/research_705.py` | Multi-search research orchestrator | You're running the script yourself |

---

## TL;DR: Top 3 Cost Savings Strategies

### 1. Model Routing (40-60% savings) — IMPLEMENT FIRST

Route queries by complexity:
- Simple (< 100 tokens) → Haiku, Gemini-Flash, Groq ($0.0001-0.0005/call)
- Medium (100-500 tokens) → Sonnet, NIM, DeepSeek ($0.001-0.005/call)
- Complex (> 500 tokens) → Opus, GPT-5 ($0.01-0.05/call)

**Effort:** 4-6 hours
**Impact:** 40-60% cost reduction
**File to modify:** `src/loom/multi_llm.py`

### 2. Free Tier Cascade (70-80% coverage) — DESIGN INTO CASCADE

Use these in order:
1. Groq free (30 req/min)
2. NVIDIA NIM (unlimited)
3. Gemini-Flash (15 req/min)
4. DeepSeek (cheap paid tier)
5. OpenAI/Anthropic (premium fallback)

**Effort:** 6-8 hours (monitoring + quota tracking)
**Impact:** 70-80% queries from free tiers
**Files:** `src/loom/config.py`, new `src/loom/free_tier_monitor.py`

### 3. Semantic Cache Tuning (10-20% improvement) — QUICK WIN

Current threshold: 0.92 → Try 0.95 or 0.90
- Higher threshold = better quality, lower hit rate
- Lower threshold = higher hit rate, possible quality issues

**Effort:** 2-3 hours (A/B test)
**Impact:** 10-20% improvement to cache hits
**File:** `src/loom/semantic_cache.py`

---

## Budget Example: 1000 Reframes/Month

### Current Spend (No Optimization)
```
1000 reframes × $0.34 cost-per-success = $340/month (EXPENSIVE)
```

### After Phase 1 (50-70% reduction)
```
Model routing + free tier cascade
1000 reframes × $0.10-0.17 = $100-170/month (70% SAVINGS)
```

### After Phase 2 (70-85% reduction)
```
+ prompt compression + batching
1000 reframes × $0.05-0.10 = $50-100/month (85% SAVINGS)
```

### After Phase 3 (80-90% reduction)
```
+ embedding cache + vLLM
1000 reframes × $0.034-0.068 = $34-68/month (90% SAVINGS)
```

---

## Implementation Roadmap

### Phase 1: Week 1-2 (50-70% savings, 12-17 hours)

**Task 1:** Add model routing to `multi_llm.py`
```python
def route_by_complexity(query: str) -> str:
    tokens = len(query.split())
    if tokens < 100:
        return "haiku-4.5"
    elif tokens < 500:
        return "sonnet-4.6"
    else:
        return "opus-4.6"
```

**Task 2:** Tune semantic cache threshold
```python
SEMANTIC_CACHE_THRESHOLD = 0.92  # try 0.90, 0.95
```

**Task 3:** Monitor free tier quotas
- Groq: 30 req/min
- NVIDIA NIM: unlimited
- Gemini: 15 req/min, 2M tokens/day

### Phase 2: Week 3-8 (70-85% savings, 40-52 hours)

**Task 1:** Integrate LLMLingua for token compression
```bash
pip install llm-lingua
# Create src/loom/tools/prompt_compression.py
```

**Task 2:** Add batch processing queue
```python
# src/loom/pipelines/batch_processor.py
# Queue non-time-sensitive reframes
# Submit batches to DeepSeek/OpenAI batch API
```

**Task 3:** Enable OpenAI KV cache
```python
# src/loom/providers/openai_provider.py
# Add cache_control={"type": "ephemeral"} for system prompt
```

### Phase 3: Week 9+ (80-90% savings, 48-64 hours)

**Task 1:** Add embedding similarity to semantic cache
```bash
pip install sentence-transformers
# Extend semantic_cache.py with all-minilm-l6-v2
```

**Task 2:** Deploy vLLM for sustained workloads
```bash
# On VastAI or internal infra (~$50/month)
# Models: Llama-2-70b, Mistral-7b
```

**Task 3:** Wait for Anthropic batch API (2026)
```python
# Once available, integrate claude-batch
```

---

## Key Files to Review

1. **Current cost tracking:**
   ```
   src/loom/billing/cost_tracker.py
   - LLM_PROVIDER_COSTS (Groq $0, OpenAI $0.01, etc.)
   - SEARCH_PROVIDER_COSTS
   - compute_margin() function
   ```

2. **Semantic caching (already implemented):**
   ```
   src/loom/semantic_cache.py
   - 15-25% hit rate on typical workload
   - Uses TF-IDF + Jaccard + n-gram similarity
   - Can be tuned and extended
   ```

3. **Multi-LLM provider orchestration:**
   ```
   src/loom/multi_llm.py
   - Currently cascades through providers
   - Add complexity-based routing here
   ```

4. **Provider implementations:**
   ```
   src/loom/providers/
   - base.py (abstract LLMProvider)
   - groq_provider.py (free tier)
   - openai_provider.py (with native caching)
   - nvidia_nim.py (free tier)
   ```

---

## How to Run the Research Script

### On Hetzner (Recommended)
```bash
ssh hetzner
cd /opt/research-toolbox
python3 loom/scripts/research_705.py
cat tmp/research_705_cost.json | jq .
```

### Locally
```bash
cd /Users/aadel/projects/loom
python3 scripts/research_705.py
cat /tmp/research_705_cost.json | jq .
```

---

## Success Metrics to Track

### Before Implementation
- Cost-per-success: $0.34
- Semantic cache hit rate: 15-25%
- Free tier coverage: ~40%
- API spend: $340/month (for 1000 reframes)

### After Phase 1 (Target)
- Cost-per-success: $0.10-0.17 (50-70% reduction)
- Semantic cache hit rate: 18-30%
- Free tier coverage: 60-70%
- API spend: $100-170/month

### After Phase 2 (Target)
- Cost-per-success: $0.05-0.10 (70-85% reduction)
- Semantic cache hit rate: 20-35%
- Free tier coverage: 65-75%
- API spend: $50-100/month

### After Phase 3 (Target)
- Cost-per-success: $0.034-0.068 (80-90% reduction)
- Semantic cache hit rate: 40-50%
- Free tier coverage: 65-75%
- API spend: $34-68/month

---

## Provider Cost Comparison

| Provider | Cost/1M tokens | Free tier | Use case |
|----------|---|---|---|
| **Groq** | $0 (free tier 30 req/min) | YES | Default, speed (100-300ms) |
| **NVIDIA NIM** | $0 | YES | Fallback, unlimited quota |
| **Gemini-Flash** | $0 (free tier 15 req/min) | YES | Supplementary |
| **DeepSeek** | $0.14 in, $0.28 out | NO | Cheap paid tier |
| **OpenAI (gpt-5-mini)** | $0.60 in, $2.40 out | NO | Premium tier |
| **Anthropic (Opus)** | $15 in, $75 out | NO | Ultra-premium |

**Strategy:** Use Groq/NIM/Gemini for 60-70%, DeepSeek for 20-30%, reserve premium for <10%.

---

## Common Questions

**Q: Will model routing degrade attack success rate (ASR)?**
A: No. Simple queries naturally work with cheaper models. Complex queries still use premium models. Validate with A/B testing.

**Q: What if Groq hits rate limit (30 req/min)?**
A: Cascade to NVIDIA NIM (unlimited). Monitor quota hourly and warn before exhaustion.

**Q: Can we reuse responses across different models?**
A: Partially. Groq response ≈ NIM response (both quantized), but OpenAI/Claude responses differ. Use semantic cache with model-aware keys.

**Q: How much does vLLM self-hosting cost?**
A: ~$50/month on VastAI for 1 GPU. Break-even at ~1000 calls/day. ROI: 30-50% savings on LLM calls.

**Q: When should we implement vLLM?**
A: Only after Phase 2. Need sustained high-volume workload to justify operational overhead.

---

## Where to Start

1. **Read** `RESEARCH-705-SUMMARY.md` (this directory, 10 min)
2. **Review** `docs/RESEARCH-705-COST-OPTIMIZATION.md` (detailed, 30 min)
3. **Look at** `src/loom/billing/cost_tracker.py` and `src/loom/semantic_cache.py` (understand current state)
4. **Estimate** effort for Phase 1 tasks (12-17 hours)
5. **Create PR** for model routing (highest ROI first)
6. **Monitor** cost-per-success metric weekly
7. **Plan** Phase 2 after Phase 1 shows 50%+ savings

---

## Contact & Support

- Questions about strategy? → Read `docs/RESEARCH-705-COST-OPTIMIZATION.md`
- Questions about implementation? → Read `docs/RESEARCH-705-DEPLOYMENT.md`
- Questions about specific file? → Read source code in `src/loom/`

---

**Status:** Research complete. Ready for Phase 1 implementation.

**Timeline:** 3 phases over 12 weeks, 100-133 hours total.

**Expected outcome:** 70-85% cost reduction ($340/month → $34-68/month for 1000 reframes).

**Author:** Claude Haiku 4.5 (Backend Developer Agent)
**Date:** 2026-05-01
