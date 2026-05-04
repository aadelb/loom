# Real-Time Strategy Adaptation with Strategy Adapter

## Overview

The `StrategyAdapter` module implements a real-time feedback loop that enables Loom to adaptively select the most effective strategies based on empirical outcomes. It maintains running statistics for each strategy-model pair and uses exponential moving average (EMA) to weight recent successes more heavily.

## Architecture

### Core Components

#### 1. StrategyStats Class
```python
@dataclass
class StrategyStats:
    strategy: str           # Strategy name (e.g., "deep_inception")
    model: str             # Target model (e.g., "gpt-4", "claude-3-sonnet")
    successes: int         # Total successful outcomes
    failures: int          # Total failed outcomes
    ema_success_rate: float  # Exponential moving average (0-1)
    recent_outcomes: list[tuple[bool, float]]  # Last 100 (success, hcs_score)
```

#### 2. StrategyAdapter Class
Singleton that maintains in-memory stats registry with optional disk persistence:
- **record_outcome()** - Record a strategy outcome (success/failure + HCS score)
- **adapt_strategy_ranking()** - Get strategies ranked by EMA success rate
- **get_hot_strategies()** - Get top performers above a success rate threshold
- **get_stats()** - Get detailed stats for a strategy-model pair
- **flush_state()** - Persist stats to JSON (debounced every 60s or on force)
- **load_state()** - Load persisted stats from disk on startup

## Integration Points in full_pipeline.py

### 1. Initialization (Stage 1)
```python
adapter = None
if STRATEGY_ADAPTER_AVAILABLE:
    try:
        adapter = await StrategyAdapter.instance()
    except Exception as e:
        logger.warning("strategy_adapter_init_failed error=%s", str(e)[:100])
```
- Loads persisted state from disk if it exists
- Safe fallback if adapter is unavailable

### 2. Hot Strategy Selection (Stage 2 - Escalation Loop)
```python
# Try hot strategies from adapter first (real-time adaptation)
hot_strategies: list[str] = []
if adapter and current_model:
    try:
        hot_strategies = adapter.get_hot_strategies(
            model=current_model,
            top_k=5,
            min_success_rate=0.5,
        )
        if hot_strategies:
            strategy_source = "hot_adapter"
```

**When triggered:**
- When escalation is needed (attempt > 0 and score < target_hcs)
- After getting LLM response, but before selecting escalation strategy

**Priority order:**
1. Hot strategies from adapter (empirically proven)
2. Learned strategies from meta_learner (heuristic patterns)
3. Default escalation strategies (static fallback)

### 3. Recording Successful Outcomes
```python
if adapter and current_strategy and current_model:
    try:
        await adapter.record_outcome(
            strategy=current_strategy,
            model=current_model,
            success=True,
            hcs_score=current_score,
            alpha=0.3,
        )
```

**When triggered:**
- When answer meets target HCS score (current_score >= target_hcs)
- Tracks which strategy led to success for future use

### 4. Recording Failed Outcomes
```python
if adapter and strategy_choice and current_model:
    try:
        await adapter.record_outcome(
            strategy=strategy_choice,
            model=current_model,
            success=False,
            hcs_score=current_score,
            alpha=0.3,
        )
```

**When triggered:**
- When escalation strategy doesn't improve score
- Tracks unsuccessful attempts to avoid repeating failures

### 5. State Flush (Stage 3 - Final)
```python
if adapter:
    try:
        await adapter.flush_state(force=True)
        logger.debug("strategy_adapter_state_flushed")
```

**When triggered:**
- After pipeline completion
- Persists all recorded outcomes to `~/.cache/loom/strategy_adapter_stats.json`

## Exponential Moving Average (EMA)

The EMA formula weights recent outcomes more heavily:
```
EMA_new = alpha × outcome + (1 - alpha) × EMA_old
```

- **alpha=0.3** (default): 30% weight on new outcome, 70% on history
- **Higher alpha** (0.7-0.9): More recent-biased, faster adaptation
- **Lower alpha** (0.1-0.2): More history-biased, smoother trends

### Example
Initial EMA=0.5, recording a success with alpha=0.3:
```
EMA = 0.3 × 1.0 + 0.7 × 0.5 = 0.65
```

## Ranking Logic

### adapt_strategy_ranking(model, query_type)
Returns strategies sorted by:
1. **Primary:** EMA success rate (descending)
2. **Tie-breaker:** Average HCS score (descending)

### get_hot_strategies(model, top_k=5, min_success_rate=0.6)
Returns up to `top_k` strategies with:
- EMA success rate >= min_success_rate
- Sorted by success rate (descending), then by trial count (more tested = more reliable)

## Storage

### In-Memory Registry
```python
_stats: dict[str, dict[str, StrategyStats]]
# Format: {strategy: {model: StrategyStats}}
```

### Persisted Storage
**Path:** `~/.cache/loom/strategy_adapter_stats.json`

**Format:**
```json
{
  "deep_inception": {
    "gpt-4": {
      "strategy": "deep_inception",
      "model": "gpt-4",
      "successes": 8,
      "failures": 2,
      "ema_success_rate": 0.785,
      "recent_outcomes": [[true, 9.0], [false, 2.5], ...],
      "last_updated": "2026-05-04T10:30:00+00:00"
    }
  },
  ...
}
```

**Persistence Strategy:**
- Debounced flush every 60 seconds (if dirty)
- Force flush on pipeline completion
- Atomic writes via temp file + rename
- Automatic directory creation

## Usage Examples

### Recording Strategy Outcomes
```python
adapter = await StrategyAdapter.instance()

# Record success
await adapter.record_outcome(
    strategy="deep_inception",
    model="gpt-4",
    success=True,
    hcs_score=8.5,
    alpha=0.3
)

# Record failure
await adapter.record_outcome(
    strategy="crescendo",
    model="claude-3-sonnet",
    success=False,
    hcs_score=3.2,
    alpha=0.3
)
```

### Getting Adaptive Rankings
```python
# Get all strategies ranked by success rate
all_ranked = adapter.adapt_strategy_ranking(
    model="gpt-4",
    query_type="general"
)
print(all_ranked)  # ['deep_inception', 'compliance_audit_fork', ...]

# Get only hot strategies
hot = adapter.get_hot_strategies(
    model="gpt-4",
    top_k=5,
    min_success_rate=0.6
)
print(hot)  # ['deep_inception', 'ethical_anchor', ...]
```

### Inspecting Statistics
```python
stats = adapter.get_stats("deep_inception", "gpt-4")
print(stats)
# {
#   'strategy': 'deep_inception',
#   'model': 'gpt-4',
#   'successes': 8,
#   'failures': 2,
#   'ema_success_rate': 0.785,
#   'avg_hcs': 8.2,
#   'recent_outcomes': [{'success': True, 'hcs': 9.0}, ...],
#   'total_trials': 10,
#   'last_updated': '2026-05-04T10:30:00+00:00'
# }
```

### Resetting Statistics
```python
# Reset all statistics
adapter.reset_stats()

# Reset for specific strategy
adapter.reset_stats(strategy="deep_inception")

# Reset for specific model
adapter.reset_stats(strategy="deep_inception", model="gpt-4")
```

## Performance Characteristics

### Time Complexity
- **record_outcome():** O(1) amortized
- **adapt_strategy_ranking():** O(S × M) where S=strategies, M=models per strategy
- **get_hot_strategies():** O(S × M)
- **get_stats():** O(1)

### Space Complexity
- **In-memory:** O(S × M × R) where R=recent outcomes (max 100)
- **Persisted:** ~500 bytes per strategy-model pair (varies with outcome history)

### Persistence Overhead
- **Load time:** ~50ms for 100+ strategy-model pairs
- **Flush time:** ~30ms per flush (debounced)
- **Disk space:** ~200KB for 400+ pairs with 100 recent outcomes each

## Safety & Fallbacks

### Graceful Degradation
```python
# Module import is optional
try:
    from loom.tools.strategy_adapter import StrategyAdapter
    STRATEGY_ADAPTER_AVAILABLE = True
except ImportError:
    STRATEGY_ADAPTER_AVAILABLE = False
```

### Error Handling
- Load failures log warning, continue with empty state
- Record failures log debug, don't interrupt pipeline
- Flush failures log warning, attempt again next cycle

### Thread Safety
- Singleton access guarded by asyncio.Lock
- In-memory operations are atomic (dict updates)
- Disk I/O via atomic rename prevents corruption

## Monitoring

### Logs Generated
```
strategy_adapter_initialized
strategy_adapter_loaded strategies=120
strategy_adapter_recorded_success strategy=deep_inception model=gpt-4 hcs=8.5
strategy_adapter_recorded_failure strategy=crescendo model=claude hcs=3.0
strategy_adapter_hot_strategies model=gpt-4 top_k=5 result=3 strategies=[...]
strategy_adapter_flushed strategies=120 models_total=340
```

### Metrics Available
- EMA success rate per strategy-model (0-1)
- Average HCS score per strategy-model
- Total successes/failures
- Recent outcome history (last 20 shown)
- Last updated timestamp

## Future Enhancements

### Potential Improvements
1. **Model Profiling:** Separate rankings per model type (gpt/claude/gemini/etc.)
2. **Query Type Specialization:** Different rankings for different query categories
3. **Time-Decay Function:** Exponential decay for very old outcomes
4. **Seasonal Trends:** Track patterns across time of day, day of week
5. **Cross-Model Transfer:** Learn from similar models (e.g., gpt-4 → gpt-3.5)
6. **Anomaly Detection:** Identify strategies that suddenly drop in effectiveness
7. **A/B Testing Framework:** Formal test allocation for new strategies
8. **Redis Integration:** Distributed state across multiple workers

## Testing

Comprehensive test suite in `tests/test_tools/test_strategy_adapter.py`:
- Unit tests for StrategyStats (EMA, outcome tracking)
- Singleton behavior and thread safety
- Ranking algorithms with tie-breaking
- Persistence and state recovery
- Alpha parameter effects
- Multi-model and multi-strategy scenarios

Run tests:
```bash
pytest tests/test_tools/test_strategy_adapter.py -v
```

## References

- **EMA Algorithm:** https://en.wikipedia.org/wiki/Exponential_smoothing
- **Adaptive Selection:** https://en.wikipedia.org/wiki/Multi-armed_bandit
- **Empirical Feedback Loops:** Murphy, K. P. (2012). Machine Learning: A Probabilistic Perspective

## Troubleshooting

### Strategies not adapting
- Check that `record_outcome()` is being called after each escalation
- Verify model names are consistent across calls
- Check logs for "strategy_adapter_record_failed"

### Low hot strategy counts
- Reduce `min_success_rate` threshold in `get_hot_strategies()`
- More trials needed to accumulate positive outcomes
- Check if strategies are actually succeeding

### Persistence not working
- Verify `~/.cache/loom/` directory exists and is writable
- Check logs for "strategy_adapter_flush_failed"
- Manually delete corrupted state file to restart fresh

### Memory usage
- Each strategy-model pair stores up to 100 recent outcomes
- For 400 pairs with 100 outcomes: ~2-3 MB in memory
- Regularly reset unused strategies with `reset_stats()`
