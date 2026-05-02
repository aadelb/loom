# META_LEARNER Tool Demo

## Overview

The `research_meta_learn` tool uses heuristic-based meta-learning to analyze patterns in jailbreak strategies and generate novel hybrid strategies. It combines techniques from the existing 957-strategy registry without requiring external LLM calls.

## Key Features

- **Pattern Analysis**: Extracts 6 structural features from strategies:
  - Template length
  - Persona count (role placeholders)
  - Authority signals (framework/mandate references)
  - Encoding techniques
  - Conversation turns needed
  - Regulatory language

- **Strategy Synthesis**: Generates new strategies via:
  - **Crossover**: Combines 2 parent templates (first 400 chars + middle 400 chars)
  - **Mutation**: Inserts `[HYBRID INSERT]` marker between segments
  - **Scoring**: Novelty (Jaccard distance) + Effectiveness prediction

- **Success/Failure Patterns**:
  - Extracts distributions from provided success/failure lists
  - Identifies optimal template length range (800-1200 chars)
  - Detects failure modes (too_long, missing_authority, regulatory_heavy)

## Usage Example

```python
import asyncio
from loom.tools.meta_learn import research_meta_learn

async def example():
    # Example 1: Generate strategies from registry defaults
    result = await research_meta_learn(num_generate=3)
    print(f"Generated {len(result['generated_strategies'])} new strategies")
    
    # Example 2: Analyze specific successful strategies
    result = await research_meta_learn(
        successful_strategies=["ethical_anchor", "scaffolded_layered_depth"],
        failed_strategies=["simple_direct"],
        target_model="claude",
        num_generate=5
    )
    
    for strat in result['generated_strategies']:
        print(f"\n{strat['name']}")
        print(f"  Effectiveness: {strat['predicted_effectiveness']:.2f}")
        print(f"  Novelty: {strat['novelty_score']:.2f}")
        print(f"  Parents: {', '.join(strat['parent_strategies'])}")
        print(f"  Template: {strat['template'][:100]}...")

asyncio.run(example())
```

## Output Structure

```json
{
  "generated_strategies": [
    {
      "name": "meta_hybrid_0_a1b2c3d4",
      "template": "[HYBRID STRUCTURE]...\n\n{prompt}",
      "predicted_effectiveness": 0.78,
      "novelty_score": 0.62,
      "parent_strategies": ["ethical_anchor", "scaffolded_layered_depth"],
      "structural_features": {
        "length": 945,
        "persona_count": 2,
        "authority_signals": 4,
        "encoding_used": false,
        "turns_needed": 3,
        "regulatory_language": true
      }
    }
  ],
  "analysis": {
    "success_patterns": {
      "avg_length": 850,
      "common_authority": [["claude", 15], ["gpt", 12]],
      "uses_encoding": 0.35,
      "avg_turns": 2.3
    },
    "failure_patterns": {
      "too_long": 0.4,
      "missing_authority": 0.25,
      "regulatory_heavy": 0.15
    },
    "model_biases": {
      "target": "auto",
      "match_confidence": 0.72
    }
  },
  "recommendations": [
    "Favor templates 800-1200 chars for best effectiveness",
    "Include 2-3 authority signals (framework/mandate/credentials)",
    ...
  ]
}
```

## How It Works

### 1. Feature Extraction

For each strategy in the registry, extracts:

```python
{
    "length": 850,  # chars
    "persona_count": 2,  # {role} placeholders
    "authority_signals": 4,  # framework/mandate counts
    "encoding_used": False,  # base64/cipher detection
    "turns_needed": 3,  # conversation depth
    "regulatory_language": True,  # GDPR/Article detection
    "best_for": ["claude", "gpt"]  # model targets
}
```

### 2. Pattern Discovery

From success/failure sets, computes:

**Success Patterns:**
- Average template length across successful strategies
- Most common model targets
- Encoding adoption rate
- Average conversation turns

**Failure Patterns:**
- Percentage of strategies > 2000 chars
- Percentage with < 2 authority signals
- Percentage with heavy regulatory language

### 3. Hybrid Generation

For each `i` in `range(num_generate)`:

1. Select parents: `P1 = successful_list[i % len]`, `P2 = successful_list[(i+1) % len]`
2. Splice templates: `P1[:400] + "\n[HYBRID INSERT]\n" + P2[200:600] + "\n{prompt}"`
3. Calculate novelty: `1.0 - (overlap_words / total_words)`
4. Predict effectiveness:
   - Base: 0.65
   - +0.15 if length < 1500
   - +0.2 if failure patterns suggest missing authority
   - +0.1 * novelty score (up to 0.95 cap)

### 4. Model-Specific Scoring

- **Claude/Gemini**: Boost if regulatory language present
- **GPT/DeepSeek**: Favor compact (<1000 chars)
- **O1**: Favor high turn count (complex reasoning)

## Practical Applications

### 1. Adaptive Jailbreak Discovery
Feed recent test results to discover emerging attack patterns:
```python
recent_results = await db.get_strategy_results(days=7)
successes = [r.strategy_name for r in recent_results if r.passed]
failures = [r.strategy_name for r in recent_results if not r.passed]

novel_strategies = await research_meta_learn(
    successful_strategies=successes,
    failed_strategies=failures,
    num_generate=10
)
```

### 2. Model-Specific Optimization
Generate novel attacks for emerging models:
```python
claude_strategies = await research_meta_learn(
    target_model="claude",
    num_generate=5
)
```

### 3. Strategy Evolution Tracking
Monitor effectiveness changes over model updates:
```python
before = await research_meta_learn(num_generate=5)
# ... model update ...
after = await research_meta_learn(num_generate=5)

print(f"Avg effectiveness before: {avg(s['predicted_effectiveness'] for s in before['generated_strategies']):.2f}")
print(f"Avg effectiveness after: {avg(s['predicted_effectiveness'] for s in after['generated_strategies']):.2f}")
```

## Performance Characteristics

- **Latency**: < 100ms (local strategy registry analysis)
- **Cost**: FREE (no API calls)
- **Rate Limit**: 10 synthesis runs/min
- **Memory**: O(n) where n = number of strategies in registry (957)

## Implementation Details

**File**: `/src/loom/tools/meta_learner.py` (160 lines)

**Dependencies**:
- `hashlib` (MD5 hashing for strategy names)
- `collections.Counter` (frequency analysis)
- `loom.tools.reframe_strategies.ALL_STRATEGIES` (957 strategy registry)

**Registration**: `server.py:_register_tools()` line 998

**Tests**: `tests/test_tools/test_meta_learner.py` (7 test cases)

All tests passing:
- Empty input (fallback to registry)
- With successful strategies
- With failed strategies
- Custom num_generate
- Target model specification
- Success pattern extraction
- Generated strategy structure validation
