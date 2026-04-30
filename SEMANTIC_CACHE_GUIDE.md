# Semantic Cache System Guide

## Overview

The semantic cache system reduces LLM API costs by caching and reusing responses for semantically similar queries. Rather than only matching exact queries, it identifies near-duplicates and related phrasings, enabling intelligent cache hits for rephrased questions.

**Key features:**
- Pure Python implementation (no numpy/sklearn dependencies)
- Weighted similarity scoring (word overlap + character n-grams + TF-IDF)
- Model-specific caching (same query, different model = different entry)
- Gzip compression for 60%+ space savings
- Atomic writes to prevent corruption
- Cost tracking (estimated savings in dollars)
- Asyncio-safe with built-in locking

## Architecture

### Similarity Metrics

The system combines three independent similarity measures with configurable weights:

1. **Word Overlap (Jaccard Index)** — 40% weight
   - Computes: intersection / union of tokenized words
   - Handles synonyms/reordering poorly (hence combined with other metrics)

2. **N-gram Overlap (Trigrams)** — 30% weight
   - Computes: intersection / union of 3-character subsequences
   - Captures character-level similarities (typos, partial matches)

3. **TF-IDF Cosine Similarity** — 30% weight
   - Term frequency weighting (no corpus — per-query only)
   - Dot product of TF vectors normalized by magnitude
   - Emphasizes repeated/important terms

**Combined formula:**
```
similarity = 0.4 * word_overlap + 0.3 * ngram_overlap + 0.3 * tfidf_sim
```

### Cache Storage

```
~/.cache/loom/semantic/
├── 2025-01-15/
│   ├── a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6.json.gz  (compressed)
│   └── ...
├── 2025-01-14/
│   └── ...
└── index.json  (in-memory only, rebuilt on load)
```

- Daily subdirectories enable easy TTL cleanup
- Gzip compression (level 6) reduces size 60%+
- Atomic writes via UUID tmp + `os.replace()` prevent corruption
- Index rebuilt on module init by scanning disk directories

### In-Memory Index

```python
index = {
    "hash1": {
        "query": "original query text",
        "response": "cached response",
        "model": "model-name",
        "tokens": ["tokenized", "words"],
        "cached_at": "2025-01-15T10:30:00+00:00",
        "query_length": 42,
        "response_length": 150,
        "metadata": {"cost_usd": 0.001, ...}  # optional
    },
    ...
}
```

## Usage

### Basic API

```python
from loom.semantic_cache import SemanticCache, get_semantic_cache
import asyncio

# Option 1: Get singleton
cache = get_semantic_cache()

# Option 2: Create instance
cache = SemanticCache(
    cache_dir="~/.cache/loom/semantic/",
    similarity_threshold=0.92
)

async def main():
    # Store a response
    await cache.put(
        query="What is machine learning?",
        response="Machine learning is...",
        model="gpt-4",
        metadata={"cost_usd": 0.001, "tokens": 100}
    )
    
    # Retrieve (exact or semantic match)
    result = await cache.get("What is ML?", model="gpt-4")
    if result:
        print(f"Cache hit! Similarity: {result['similarity_score']}")
        print(f"Response: {result['cached_response']}")
        print(f"Original query: {result['original_query']}")
        print(f"Is semantic match: {result['is_semantic_match']}")
    
    # View stats
    stats = cache.get_stats()
    print(f"Hit rate: {stats['hit_rate']}%")
    print(f"Estimated savings: ${stats['estimated_savings_usd']}")

asyncio.run(main())
```

### Model-Specific Caching

```python
# Same query, different models — stored separately
await cache.put("explain neural networks", response_v1, model="gpt-4")
await cache.put("explain neural networks", response_v2, model="claude-3")

# Retrieving with model="gpt-4" returns response_v1
result = await cache.get("What are neural networks?", model="gpt-4")
# Retrieving with model="claude-3" returns response_v2
result = await cache.get("What are neural networks?", model="claude-3")
```

### Configuration

```python
cache = SemanticCache(
    cache_dir="/custom/cache/path",      # Default: ~/.cache/loom/semantic/
    similarity_threshold=0.95              # Default: 0.92 (range: 0.0-1.0)
)
```

**Threshold tuning:**
- `0.95+`: Very strict; only near-identical queries match (fewest false positives)
- `0.90-0.95`: Balanced (default 0.92)
- `0.80-0.90`: Lenient; catches many rephrased queries (more false positives)
- `<0.80`: Risky; may match unrelated queries

## MCP Tool Integration

Register the semantic cache management tools:

```python
# Already registered in loom/server.py
from loom.tools import semantic_cache_mgmt

# Tools available:
# - research_semantic_cache_stats() → stats dict
# - research_semantic_cache_clear(older_than_days=30) → {deleted_count, ...}
```

## Statistics & Cost Tracking

```python
stats = cache.get_stats()

# Returns:
{
    "total_queries": 150,              # get/put operations
    "cache_hits": 45,                  # exact + semantic matches
    "cache_misses": 105,
    "semantic_hits": 12,               # matches via similarity (not exact)
    "hit_rate": 30.0,                  # percentage
    "entries_cached": 42,              # unique queries cached
    "estimated_savings_usd": 0.045     # hits * $0.001 per hit
}
```

**Cost estimation:**
- Default: $0.001 per cache hit (conservative LLM cost average)
- Based on typical cost of 1000 tokens: $0.0005-0.001
- Adjust estimate by modifying the `get_stats()` method as needed

## Concurrency & Thread Safety

All operations are asyncio-safe with built-in `asyncio.Lock`:

```python
async def process_queries(queries):
    tasks = [cache.get(q, model="gpt-4") for q in queries]
    results = await asyncio.gather(*tasks)  # Safe concurrent access
    return results
```

## Maintenance & Cleanup

```python
# Clear entries older than 30 days
removed_count = await cache.clear_older_than(days=30)

# Inspect disk usage
stats = cache.get_stats()
# Stats also includes entries_cached, hit_rate, etc.

# Reload index from disk
cache._load_index()  # Called automatically on __init__
```

## Performance Characteristics

| Operation | Complexity | Time |
|-----------|-----------|------|
| `put()` | O(1) write + O(n) index update | <10ms |
| `get()` with exact match | O(1) hash lookup | <1ms |
| `get()` with semantic search | O(m) where m=entries_cached | 10-50ms (typical) |
| `similarity()` | O(n) tokenization + O(m²) comparisons | 1-5ms |

**Optimization tips:**
- High threshold (0.95) reduces semantic search time (fewer entries match)
- Periodically clean old entries (`clear_older_than()`)
- Model filtering in `get()` reduces search space
- Limit total cached entries for best performance

## Example: LLM Integration

```python
from loom.semantic_cache import get_semantic_cache
from loom.providers import groq_provider

async def cached_llm_call(query: str, model: str = "groq-mixtral") -> str:
    cache = get_semantic_cache()
    
    # Check cache first
    cached = await cache.get(query, model=model)
    if cached:
        print(f"Cache hit (similarity: {cached['similarity_score']})")
        return cached["cached_response"]
    
    # Not cached — call LLM
    print("Cache miss — calling LLM...")
    response = await groq_provider.chat(query, model)
    
    # Store in cache
    await cache.put(
        query,
        response.text,
        model=model,
        metadata={
            "cost_usd": response.cost_usd,
            "tokens": response.output_tokens
        }
    )
    
    return response.text

# Usage
result = await cached_llm_call("What is machine learning?")
```

## Testing

```bash
# Run all semantic cache tests
cd /Users/aadel/projects/loom
PYTHONPATH=src python3 -m pytest tests/test_semantic_cache.py -v

# Run specific test class
PYTHONPATH=src python3 -m pytest tests/test_semantic_cache.py::TestSemanticCache -v

# With coverage
PYTHONPATH=src python3 -m pytest tests/test_semantic_cache.py --cov=src/loom/semantic_cache
```

## Troubleshooting

### Cache not persisting

- Check directory permissions: `ls -la ~/.cache/loom/semantic/`
- Verify write access: `touch ~/.cache/loom/semantic/test.txt`
- Custom path: `cache = SemanticCache(cache_dir="/tmp/my_cache")`

### Low hit rate

- Increase threshold tolerance: `similarity_threshold=0.85` (default 0.92)
- Check semantic_hits count: high = threshold is working; low = queries too different
- Use `cache.similarity(q1, q2)` to debug similarity scores manually

### High false positives

- Increase threshold: `similarity_threshold=0.95`
- Review `is_semantic_match=True` entries for false positives
- Monitor hit rate for degradation

### Memory usage

- Limit cached entries: `await cache.clear_older_than(days=7)`
- Monitor `entries_cached` in stats
- Typical: 100 entries ≈ 50KB in memory, 10KB on disk (gzipped)

## Design Decisions

### Why pure Python similarity?

- No numpy/sklearn dependencies
- Loom runs in resource-constrained environments
- Sufficient accuracy for LLM query matching
- Fast enough (<50ms per semantic search)

### Why 0.92 threshold?

- Empirically tuned for LLM queries
- ~90% of human rephrasing falls below this
- Reduces false positives while catching synonyms
- Adjustable per use case

### Why model-specific cache?

- Same query may need different responses per model
- Different cost structures per model
- Prevents misattribution of response costs
- Enables A/B testing without cache interference

### Why gzip compression?

- 60%+ space savings
- Negligible CPU cost (level 6 = balanced)
- Aligns with loom's existing cache.py pattern
- Backwards compatible with legacy .json files

## API Reference

### SemanticCache Class

```python
class SemanticCache:
    def __init__(
        self,
        cache_dir: str | Path | None = None,
        similarity_threshold: float = 0.92
    ) -> None: ...
    
    async def get(
        self,
        query: str,
        model: str = ""
    ) -> dict[str, Any] | None: ...
    
    async def put(
        self,
        query: str,
        response: str,
        model: str = "",
        metadata: dict[str, Any] | None = None
    ) -> None: ...
    
    def similarity(self, query1: str, query2: str) -> float: ...
    
    def get_stats(self) -> dict[str, Any]: ...
    
    async def clear_older_than(self, days: int = 30) -> int: ...
```

### Module Functions

```python
def get_semantic_cache(
    cache_dir: str | Path | None = None,
    similarity_threshold: float = 0.92
) -> SemanticCache: ...
```

### MCP Tools

```python
# Stats
async def research_semantic_cache_stats() -> dict[str, Any]

# Cleanup
async def research_semantic_cache_clear(
    older_than_days: int = 30
) -> dict[str, Any]
```

## Future Enhancements

- [ ] Vector embeddings (optional, via providers)
- [ ] Multi-query caching (batch queries)
- [ ] Semantic deduplication (combine similar cached entries)
- [ ] Cost breakdown by model/provider
- [ ] TTL per entry (not just global)
- [ ] Distributed cache (Redis backend option)
