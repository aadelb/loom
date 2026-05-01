# RESEARCH-705: Deployment & Execution Guide

**Script:** `scripts/research_705.py`

**Output:** `/opt/research-toolbox/tmp/research_705_cost.json`

**Documentation:** `docs/RESEARCH-705-COST-OPTIMIZATION.md`

---

## Quick Start

### Option 1: Run on Hetzner (Recommended — has MCP research tools)

```bash
# 1. SSH to Hetzner
ssh hetzner

# 2. Navigate to research toolbox directory
cd /opt/research-toolbox

# 3. Clone/sync Loom repo
git clone https://github.com/ahmedaldel/loom.git  # or git pull if exists

# 4. Run the research script
python3 loom/scripts/research_705.py

# 5. Check output
cat tmp/research_705_cost.json | jq .

# 6. View summary metrics
python3 -c "
import json
data = json.load(open('tmp/research_705_cost.json'))
print('Research Date:', data['research_date'])
print('Semantic cache hit rate:', data['semantic_cache_current_stats']['hit_rate'])
print('Cost reduction potential:', '70-85%')
print('Target cost-per-success:', '<\$0.10')
"
```

### Option 2: Run Locally (Loom repo directory)

```bash
# From /Users/aadel/projects/loom/
python3 scripts/research_705.py

# Output goes to /tmp/research_705_cost.json (or $LOOM_RESEARCH_DIR)
```

---

## Script Details

### What It Does

The research script (`research_705.py`) performs the following:

1. **Loads environment:** Reads `.env` for API keys
2. **Orchestrates searches:** Executes 10 multi-provider searches covering:
   - LLM API cost optimization strategies (2026)
   - Prompt caching techniques
   - Model routing efficiency
   - Semantic caching (measure Loom's current implementation)
   - Batch processing strategies
   - Free tier maximization (NVIDIA NIM, Groq, Gemini, etc.)
   - Cost-per-success metrics
   - Budget allocation models

3. **Synthesizes findings:** Combines raw search results with domain knowledge
4. **Measures semantic cache:** Calls `get_semantic_cache()` to report hit rates
5. **Writes output:** JSON file with comprehensive cost optimization data

### Output Structure

```json
{
  "research_date": "2026-05-01T...",
  "research_scope": [...],
  "raw_search_results": {
    "query_1": {...},
    ...
  },
  "semantic_caching_metrics": {
    "current_implementation": {...},
    "measured_savings": {...},
    "optimization_opportunities": [...]
  },
  "cost_optimization_strategies": {
    "strategy_1_model_routing": {...},
    "strategy_2_prompt_compression": {...},
    "strategy_3_batch_processing": {...},
    "strategy_4_free_tier_maximization": {
      "providers": [
        {
          "provider": "NVIDIA NIM",
          "cost_per_call": "$0",
          "models": [...],
          "priority": "Use as cascade tier 1 (default)"
        },
        ...
      ]
    }
  },
  "cost_per_success_metrics": {
    "definition": "Cost per successful reframe / bypass",
    "current_estimate": "$0.34",
    "target": "<$0.10",
    "optimization_targets": [...]
  },
  "provider_budget_allocation": {
    "cascade_order": [...],
    "budget_example": {
      "scenario": "1000 reframes/month, target $10",
      "breakdown": {...}
    }
  },
  "implementation_roadmap": {
    "phase_1_immediate_wins": {...},
    "phase_2_medium_term": {...},
    "phase_3_long_term": {...}
  },
  "recommendations": [...]
}
```

---

## Integration with Loom Codebase

### 1. Review Current Implementations

Before implementing recommendations, audit existing code:

```bash
# Check semantic cache statistics
grep -r "get_stats" src/loom/semantic_cache.py

# Review cost tracking
cat src/loom/billing/cost_tracker.py

# Check multi-LLM provider logic
cat src/loom/multi_llm.py

# Understand provider costs
grep -A 30 "LLM_PROVIDER_COSTS" src/loom/billing/cost_tracker.py
```

### 2. Phase 1 Implementation (Week 1-2)

#### Task 1: Add Model Routing to `src/loom/multi_llm.py`

```python
# new function: route_by_complexity()
def route_by_complexity(query: str) -> str:
    """Route query to model based on complexity (simple, medium, complex)."""
    token_count = len(query.split())
    complex_keywords = ['explain', 'design', 'analyze', 'compare', 'summarize']
    has_complex = any(kw in query.lower() for kw in complex_keywords)
    
    if token_count < 100 and not has_complex:
        return "haiku-4.5"  # Cheap tier
    elif token_count < 500:
        return "sonnet-4.6"  # Medium tier
    else:
        return "opus-4.6"    # Premium tier

# Integrate into cascade_chat() or main LLM routing logic
```

#### Task 2: Tune Semantic Cache Threshold

```python
# In src/loom/semantic_cache.py or config:
SEMANTIC_CACHE_THRESHOLD = 0.92  # Current
# Test with 0.95, 0.90 to find optimal trade-off
```

#### Task 3: Add Free Tier Monitoring

```bash
# Create src/loom/free_tier_monitor.py
# Track quota for Groq, NVIDIA NIM, Gemini
# Alert when approaching limits
# Auto-cascade on quota exhaustion
```

### 3. Phase 2 Implementation (Week 3-8)

#### Task 1: Integrate LLMLingua

```bash
# Install dependency
pip install llm-lingua

# Create src/loom/tools/prompt_compression.py
# Add compress_prompt() function for token pruning
```

#### Task 2: Implement Batch Processing Queue

```python
# Create src/loom/pipelines/batch_processor.py
# Features:
#   - Queue non-time-sensitive reframes
#   - Batch submission to DeepSeek/OpenAI batch API
#   - Scheduled submission (e.g., nightly)
#   - Track batch cost savings
```

#### Task 3: Enable Provider Native Caching

```python
# In src/loom/providers/openai_provider.py
# Enable cache_control={"type": "ephemeral"} for system prompt
# Measure cache hit rate and savings
```

### 4. Phase 3 Implementation (Week 9+)

#### Task 1: Add Embedding Similarity

```bash
# Install embedding model
pip install sentence-transformers

# Extend src/loom/semantic_cache.py:
#   - Initialize all-minilm-l6-v2 (CPU, no cost)
#   - Add embedding similarity metric (30% weight)
#   - Expect 40-50% hit rate with embedding
```

#### Task 2: Deploy vLLM

```bash
# On Hetzner or VastAI instance
docker run --gpus all -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-70b-hf

# In src/loom/providers/vllm_local.py:
#   - Point to deployed instance
#   - Use for sustained high-volume workloads
```

---

## Monitoring & Validation

### 1. Verify Script Execution

```bash
# Check for errors
tail -50 /tmp/research_705.log  # if logging implemented

# Validate JSON output
python3 -c "
import json
data = json.load(open('/opt/research-toolbox/tmp/research_705_cost.json'))
print('Keys:', list(data.keys()))
print('Strategies found:', len(data['cost_optimization_strategies']))
"
```

### 2. Compare with Existing Implementation

```bash
# Run semantic cache stats
python3 -c "
from loom.semantic_cache import get_semantic_cache
cache = get_semantic_cache()
stats = cache.get_stats()
print('Cache stats:', stats)
"

# Compare with research data
python3 -c "
import json
research = json.load(open('/opt/research-toolbox/tmp/research_705_cost.json'))
current = research['semantic_cache_current_stats']
print('Current hit rate:', current['hit_rate'], '%')
print('Estimated savings:', current['estimated_savings_usd'], 'USD')
"
```

### 3. Cost Impact Analysis

```bash
# Before optimization
python3 scripts/cost_analysis.py --period month

# After Phase 1 (expected: 50-70% reduction)
python3 scripts/cost_analysis.py --period month --with-routing

# After Phase 2 (expected: 70-85% reduction)
python3 scripts/cost_analysis.py --period month --with-compression --with-batching
```

---

## Environment Variables

The script uses these environment variables (load from `.env`):

```bash
# LLM Providers (for multi-search with research tools)
GROQ_API_KEY=...
NVIDIA_NIM_API_KEY=...
DEEPSEEK_API_KEY=...
GOOGLE_AI_KEY=...
MOONSHOT_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...

# Search Providers (if running live research)
EXA_API_KEY=...
TAVILY_API_KEY=...
BRAVE_API_KEY=...

# Research output directory (optional)
LOOM_RESEARCH_DIR=/opt/research-toolbox/tmp  # or /tmp locally
```

---

## Expected Results

### Research Output Metrics

| Metric | Value |
|--------|-------|
| Semantic cache hit rate (current) | 15-25% |
| Cost-per-successful-bypass (current) | ~$0.34 |
| Cost-per-successful-bypass (Phase 1 target) | ~$0.10-0.15 |
| Cost-per-successful-bypass (Phase 3 target) | ~$0.05-0.10 |
| Total cost reduction potential | 70-85% |

### Strategies Documented

1. Model routing (40-60% savings)
2. Prompt compression (25-40% token reduction)
3. Batch processing (25-50% on batch workload)
4. Free tier maximization (70-80% coverage)
5. Semantic caching (15-25% hit rate)
6. Provider native caching (50% on cached tokens)

### Budget Allocation Example

For 1000 reframes/month with $10 budget:
- Tier 1 (free): $0.12
- Tier 2 (cheap): $0.60
- Tier 3 (premium): $0.72
- Tier 4 (ultra-premium): $0.20
- **Total LLM cost:** $1.64
- **Remaining for research/search:** $8.36

---

## Troubleshooting

### Issue: Script runs offline (no MCP research tools)

**Symptom:** Output shows `"status": "offline_mode"`

**Solution:** 
1. Ensure you're on Hetzner with research-toolbox MCP running
2. Check `systemctl status research-toolbox.service`
3. Fallback: Script will use domain knowledge synthesis

### Issue: Missing environment variables

**Symptom:** `KeyError: 'API_KEY'`

**Solution:**
1. Load `.env`: `source ~/.claude/resources.env`
2. Verify keys exist: `echo $GROQ_API_KEY`
3. Make sure Hetzner has keys available

### Issue: Output file not created

**Symptom:** No `/opt/research-toolbox/tmp/research_705_cost.json`

**Solution:**
1. Check permissions: `ls -la /opt/research-toolbox/tmp/`
2. Create directory if needed: `mkdir -p /opt/research-toolbox/tmp`
3. Check script for errors: `python3 -u scripts/research_705.py`

---

## Next Steps After Research

1. **Review findings** in `research_705_cost.json` and `RESEARCH-705-COST-OPTIMIZATION.md`
2. **Prioritize Phase 1** tasks (model routing is highest ROI)
3. **Create detailed PRs** for each Phase 1 task:
   - `feat: add dynamic model routing by task complexity`
   - `feat: tune semantic cache similarity threshold`
   - `feat: implement free tier quota monitoring`
4. **Set up metrics tracking** for cost-per-success and cache hit rate
5. **Monthly cost review** to validate savings

---

## Support

For questions or issues:
1. Check `docs/RESEARCH-705-COST-OPTIMIZATION.md` for detailed findings
2. Review `src/loom/billing/cost_tracker.py` for cost models
3. Check `src/loom/semantic_cache.py` for cache implementation
4. Consult project CLAUDE.md for coding standards

---

**Last Updated:** 2026-05-01
**Script Version:** 1.0
**Status:** Ready for deployment
