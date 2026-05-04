# Semantic Tool Router Implementation Guide

## Overview

The semantic tool router (`semantic_router.py`) provides intelligent tool matching using sentence-transformers embeddings for semantic similarity. When integrated with the universal orchestrator, it combines semantic similarity (60% weight) with keyword matching (40% weight) for optimal tool selection.

## Architecture

### Three-Tier Fallback Strategy

The semantic router implements a graceful degradation approach:

1. **Sentence-Transformers (Primary)**: Uses `all-MiniLM-L6-v2` model for high-quality semantic embeddings
   - Dimensionality: 384
   - Processing: CPU-friendly, fast inference
   - Cache: Embeddings cached to `~/.cache/loom/tool_embeddings.npy`

2. **Sklearn TF-IDF (Fallback)**: Uses TfidfVectorizer for sparse embeddings
   - Dimensionality: up to 500 features (configurable)
   - Processing: Lightweight, no external model downloads
   - Cache: Re-vectorizes on demand

3. **Keyword Matching (Final Fallback)**: Simple token-based matching
   - No external dependencies
   - Fallback when no embedding libraries available

### Key Components

#### `semantic_router.research_semantic_route(query, top_k=5)`

Routes a single query to optimal tools via semantic embeddings.

**Parameters:**
- `query` (str): Natural language description of tools needed
- `top_k` (int): Maximum tools to return (1-25, clamped)

**Returns:**
```python
{
    "query": "user query",
    "recommended_tools": [
        {"tool": "research_search", "similarity": 0.85},
        {"tool": "research_fetch", "similarity": 0.72},
    ],
    "embedding_method": "sentence-transformers",  # or "sklearn-tfidf" or "keyword_fallback"
    "total_tools": 350,
    "embedding_dims": 384,  # if applicable
}
```

#### `semantic_router.research_semantic_batch_route(queries, top_k=5)`

Routes multiple queries with aggregated statistics.

**Returns:**
```python
{
    "routes": [/* list of individual route results */],
    "tool_distribution": {"research_search": 5, "research_fetch": 3},
    "total_queries": 3,
    "recommendation_summary": "Routed 3 queries to 8 tools. Most: research_search",
}
```

#### `semantic_router.research_semantic_router_rebuild()`

Forces a rebuild of embeddings cache. Call this when new tools are added.

**Returns:**
```python
{
    "status": "rebuilt",
    "tools": 350,
    "embedding_dims": 384,
    "cache_path": "/Users/.../.cache/loom/tool_embeddings.npy",
    "message": "Rebuilt embeddings for 350 tools",
}
```

## Integration with Universal Orchestrator

The `universal_orchestrator.research_orchestrate_smart()` now incorporates semantic routing:

### Weighted Scoring System

Tools are scored using a combined formula:

```
score = (semantic_similarity * 10 * 0.6)  # 60% semantic weight
       + (keyword_matches)                  # 40% keyword weight (base)
       + (capability_boost)                 # Category-based boost (0-3)
```

### Execution Flow

1. **Query Analysis**: Extract intent and category keywords
2. **Semantic Pre-filtering**: Embed query and find 10 most similar tools
3. **Keyword Pre-filtering**: Fallback to smart_router if semantic unavailable
4. **Score Combination**: Blend semantic and keyword scores
5. **Capability Boosting**: Enhance scores based on query category
6. **Tool Selection**: Pick top-K tools based on combined scores
7. **Execution**: Run selected tools sequentially or in parallel

### Orchestrator Response

Enhanced to include semantic routing metadata:

```python
{
    "query": "find security vulnerabilities",
    "tools_selected": [
        {
            "name": "research_search",
            "relevance_score": 15.2,
            "params_used": {"query": "find security vulnerabilities"},
        }
    ],
    "semantic_scores": {"research_search": 0.85, "research_analyze": 0.72},
    "semantic_embedding_method": "sentence-transformers",
    "results": [/* execution results */],
    # ... other fields
}
```

## Caching Strategy

### Embedding Cache

- **Location**: `~/.cache/loom/tool_embeddings.npy` (numpy binary format)
- **Metadata**: `~/.cache/loom/tool_names.npy` (tool name index)
- **Refresh**: Cache rebuilds when tools are added/removed (detected via checksum comparison)
- **Thread-safe**: Uses asyncio.Lock for concurrent access

### Model Cache

- **Location**: Automatically handled by sentence-transformers (HuggingFace cache)
- **Model**: `all-MiniLM-L6-v2` (45MB)
- **First Load**: Downloaded on first use, then reused
- **Lazy Loading**: Model loaded on first query, not at startup

## Performance Characteristics

### Query Latency (Approximate)

| Scenario | Embedding Method | Latency | Notes |
|----------|------------------|---------|-------|
| Cached embeddings | sentence-transformers | 50-100ms | Query embedding only |
| Cached embeddings | sklearn-tfidf | 20-50ms | Vectorization only |
| Cached embeddings | keyword fallback | <10ms | Pure token matching |
| Cold start | sentence-transformers | 2-5s | Includes model loading |
| Rebuild (350 tools) | sentence-transformers | 5-10s | One-time cost |

### Memory Usage

| Component | Size | Notes |
|-----------|------|-------|
| Embeddings (350 tools) | ~1.3 MB | sentence-transformers (384 dims) |
| Model | ~45 MB | all-MiniLM-L6-v2 (loaded once) |
| TF-IDF vectorizer | ~500 KB | sklearn fallback |

## Usage Examples

### Example 1: Single Query Routing

```python
import asyncio
from loom.tools import semantic_router

async def main():
    result = await semantic_router.research_semantic_route(
        query="find security vulnerabilities in GitHub repositories",
        top_k=5
    )
    for tool in result["recommended_tools"]:
        print(f"{tool['tool']}: {tool['similarity']:.2%}")

asyncio.run(main())
```

**Output:**
```
research_search: 88%
research_github: 85%
research_threat_intel: 72%
research_security_headers: 65%
research_fetch: 58%
```

### Example 2: Using with Orchestrator

```python
import asyncio
from loom.tools import universal_orchestrator

async def main():
    result = await universal_orchestrator.research_orchestrate_smart(
        query="analyze DNS records for phishing domains",
        max_tools=3,
        strategy="parallel"
    )
    
    print(f"Embedding method: {result['semantic_embedding_method']}")
    print(f"Selected tools: {[t['name'] for t in result['tools_selected']]}")
    print(f"Execution time: {result['total_duration_ms']:.1f}ms")

asyncio.run(main())
```

### Example 3: Batch Routing

```python
import asyncio
from loom.tools import semantic_router

async def main():
    queries = [
        "search the dark web",
        "analyze network traffic",
        "extract emails from documents",
    ]
    
    result = await semantic_router.research_semantic_batch_route(
        queries=queries,
        top_k=3
    )
    
    print(result["recommendation_summary"])
    for tool, count in result["tool_distribution"].items():
        print(f"{tool}: recommended {count} times")

asyncio.run(main())
```

### Example 4: Rebuild Cache

```python
import asyncio
from loom.tools import semantic_router

async def main():
    # After adding new tools to the system
    result = await semantic_router.research_semantic_router_rebuild()
    print(f"Cache rebuilt with {result['tools']} tools")
    print(f"Embedding dimensions: {result['embedding_dims']}")

asyncio.run(main())
```

## Troubleshooting

### Issue: "semantic_router not available"

**Solution**: The semantic_router module failed to import. Check:
- All imports in `src/loom/tools/semantic_router.py`
- numpy is installed: `pip install numpy`
- If using fallback embedding methods, sklearn is available: `pip install scikit-learn`

### Issue: Slow First Query (5+ seconds)

**Cause**: Sentence-transformers model being downloaded and loaded.

**Solution**: Pre-warm the cache:
```bash
python3 -c "
import asyncio
from loom.tools import semantic_router
asyncio.run(semantic_router.research_semantic_route('test'))
"
```

This downloads and caches the model for subsequent use.

### Issue: Out of Memory on Embedded System

**Solution**: Fall back to TF-IDF or keyword routing:
1. Uninstall sentence-transformers: `pip uninstall -y sentence-transformers`
2. Semantic router will auto-detect and use sklearn TF-IDF instead

### Issue: Stale Embeddings Cache

**Cause**: Tool descriptions changed but cache not rebuilt.

**Solution**: Rebuild manually:
```python
import asyncio
from loom.tools import semantic_router
asyncio.run(semantic_router.research_semantic_router_rebuild())
```

Or delete cache:
```bash
rm ~/.cache/loom/tool_embeddings.npy ~/.cache/loom/tool_names.npy
```

## Configuration

### Environment Variables

| Variable | Default | Effect |
|----------|---------|--------|
| `LOOM_EMBEDDING_METHOD` | auto-detect | Force method: `sentence-transformers`, `sklearn-tfidf`, `keyword` |
| `LOOM_TOP_K_DEFAULT` | 5 | Default max tools returned |
| `LOOM_SEMANTIC_WEIGHT` | 0.6 | Semantic score weight (0.0-1.0) |
| `LOOM_KEYWORD_WEIGHT` | 0.4 | Keyword score weight (0.0-1.0) |

### Programmatic Configuration

```python
from loom.tools import semantic_router

# Set maximum embedding dimensions
semantic_router._MAX_EMBEDDING_DIMS = 768

# Set cache directory
semantic_router._CACHE_PATH = Path("/custom/path/embeddings.npy")
```

## Testing

### Unit Tests

```bash
pytest tests/test_tools/test_semantic_router.py -v
```

### Integration Tests

```bash
pytest tests/test_integration/test_semantic_orchestration.py -v
```

### Performance Benchmarking

```bash
python3 -m pytest tests/ -k semantic --benchmark --durations=10
```

## Implementation Details

### Tool Description Extraction

The semantic router extracts tool descriptions from AST parsing:

1. Scans all `.py` files in `src/loom/tools/`
2. Parses function definitions with `ast.parse()`
3. Extracts first line of docstring as description
4. Builds dictionary mapping `tool_name` → `description`

### Embedding Caching

Cache is stored as numpy arrays for efficient I/O:

```
~/.cache/loom/
├── tool_embeddings.npy       # Shape: (num_tools, embedding_dims)
├── tool_names.npy            # Shape: (num_tools,) dtype=object
```

On load, verify:
1. File exists
2. Tool names match current tool set
3. Array shape matches expected dimensions

### Cosine Similarity Calculation

Uses sklearn's optimized `cosine_similarity`:

```python
similarities = cosine_similarity(query_embedding, tool_embeddings)[0]
```

Returns normalized scores in [0, 1] range.

## Future Enhancements

### Planned Improvements

1. **Hybrid Chunking**: Split long tool descriptions into multiple semantic units
2. **Category-aware Embeddings**: Fine-tune embeddings on tool categories
3. **User Feedback Loop**: Learn from tool execution to improve routing
4. **Real-time Embedding Updates**: Rebuild embeddings incrementally as tools change
5. **GraphRAG Integration**: Use knowledge graph for tool relationships

### Experimental Features

1. **Semantic Deduplication**: Identify and consolidate redundant tools
2. **Tool Clustering**: Group similar tools by semantic similarity
3. **Intent Detection**: Pre-classify query intent before routing

## References

- [Sentence-Transformers](https://www.sbert.net/) - Documentation
- [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) - Model card
- [Cosine Similarity](https://en.wikipedia.org/wiki/Cosine_similarity) - Algorithm reference
- [Sklearn TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html) - Fallback method

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review test files for usage examples
3. Examine server.py for tool registration patterns
4. Consult src/loom/tools/smart_router.py for keyword-based alternatives
