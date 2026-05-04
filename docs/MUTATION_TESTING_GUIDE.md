# Mutation Testing & Tool Selection Accuracy Benchmark

## Overview

This guide covers two quality assurance systems:

1. **Mutation Testing** — Verifies test effectiveness by mutating code and measuring test detection
2. **Tool Selection Accuracy Benchmark** — Measures semantic router precision/recall for tool recommendations

## Part 1: Mutation Testing

### What is Mutation Testing?

Mutation testing introduces deliberate code changes (mutations) and runs your test suite against them. If tests fail, the mutation was "killed" (detected). If tests pass, the mutation "survived" (undetected).

**Mutation score** = (killed mutations / total mutations) × 100%

High scores indicate comprehensive tests that catch subtle bugs.

### Setup

#### Install mutmut

```bash
pip install mutmut
```

#### Run Mutation Tests

```bash
cd /Users/aadel/projects/loom
./scripts/run_mutation_test.sh
```

This script tests three critical security modules:

1. **validators.py** — URL validation, SSRF prevention
   - Target: >80% mutation score
   - Tests: `tests/test_validators.py`

2. **pii_scrubber.py** — Data masking, anonymization
   - Target: >85% mutation score
   - Tests: `tests/test_pii_scrubber.py`

3. **errors.py** — Exception hierarchy
   - Target: >75% mutation score
   - Tests: `tests/comprehensive/test_security.py`

### Manual Mutation Testing

For custom mutations on other modules:

```bash
# Mutate a specific module
mutmut run \
  --paths-to-mutate=src/loom/module.py \
  --tests-dir=tests \
  --runner="pytest tests/test_module.py -x -q" \
  --no-cov

# View results
mutmut results

# Analyze specific mutations
mutmut show
```

### Interpreting Results

| Score  | Meaning |
|--------|---------|
| 90-100% | **Excellent** — Rare mutations escape detection |
| 80-89%  | **Good** — Most mutations caught |
| 70-79%  | **Fair** — Significant gaps remain |
| <70%    | **Poor** — Major gaps in test coverage |

### Common Patterns for Improvement

**Low mutation scores often indicate:**
- Missing boundary condition tests
- Insufficient error path coverage
- Untested exception handlers
- Missing validation tests

**Example: Improve URL validator coverage**

```python
# Current test:
def test_valid_https():
    validate_url("https://example.com")  # ✓ passes

# Add mutation-killing test:
def test_invalid_missing_scheme():
    with pytest.raises(UrlSafetyError):
        validate_url("example.com")  # Catches scheme validation mutations

def test_invalid_uppercase_scheme():
    with pytest.raises(UrlSafetyError):
        validate_url("HTTP://example.com")  # Catches case sensitivity mutations
```

## Part 2: Tool Selection Accuracy Benchmark

### What is Tool Selection?

The semantic router uses embeddings to recommend the best tools for natural language queries:

```
Input:  "search for AI papers on jailbreaking"
↓
[Embed query + all tool descriptions]
↓
[Find top-K most similar tools via cosine similarity]
↓
Output: ["research_search", "research_deep", "research_arxiv_search", ...]
```

### Benchmark Structure

File: `tests/comprehensive/test_tool_selection.py` (439 lines)

#### Test Coverage

**20 representative queries across 8 domains:**

1. **Research & Search** (3 queries)
   - "search for AI papers on jailbreaking models"
   - "find information about prompt injection attacks"
   - "look up articles about model safety and alignment"

2. **Fetching & Scraping** (3 queries)
   - "fetch and analyze the content at https://example.com"
   - "scrape multiple URLs and extract text"
   - "convert HTML to markdown from a webpage"

3. **LLM & Language** (4 queries)
   - "summarize this text using an LLM"
   - "classify this document into categories"
   - "extract entities and information from text"
   - "translate text to different languages"

4. **Security & Analysis** (3 queries)
   - "check if a domain has security vulnerabilities"
   - "scan for SSRF and XSS vulnerabilities"
   - "perform DNS reconnaissance on a target"

5. **Social & Intelligence** (3 queries)
   - "find social media profiles for a person"
   - "analyze threat actor infrastructure"
   - "monitor for data leaks and breaches"

6. **Specialized** (4 queries)
   - "detect steganography and hidden content"
   - "analyze PDF metadata and EXIF data"
   - "check for academic paper retraction status"
   - "assess model bias and fairness"

#### Metrics

**Precision@K** — What % of queries have the correct tool in top-K?

```
Precision@3 = (queries with correct tool in top-3) / total queries
Precision@5 = (queries with correct tool in top-5) / total queries
```

**Recall** — What % of queries find the correct tool anywhere?

```
Recall = (queries where correct tool appears) / total queries
```

**Targets:**
- Precision@3: >70% (correct tool in top-3)
- Precision@5: >80% (correct tool in top-5)
- Recall: >85% (correct tool found)

### Running the Benchmark

#### Full Suite

```bash
cd /Users/aadel/projects/loom

# Run all tool selection tests
pytest tests/comprehensive/test_tool_selection.py -v

# Run with coverage
pytest tests/comprehensive/test_tool_selection.py --cov=src/loom/tools/semantic_router -v

# Run only accuracy tests (skip edge cases and performance)
pytest tests/comprehensive/test_tool_selection.py::TestToolSelectionAccuracy -v
```

#### Individual Query Testing

```bash
# Test specific query (e.g., query 5)
pytest tests/comprehensive/test_tool_selection.py::TestToolSelectionAccuracy::test_individual_query[q5] -v

# Test only successful routing (quick validation)
pytest tests/comprehensive/test_tool_selection.py::TestToolSelectionAccuracy -v -k "test_tool_selection_all_queries"
```

#### Performance Profiling

```bash
# Run performance tests
pytest tests/comprehensive/test_tool_selection.py::TestToolSelectionPerformance -v

# With timing info
pytest tests/comprehensive/test_tool_selection.py::TestToolSelectionPerformance -v -s
```

### Output Interpretation

The benchmark prints detailed results:

```
================================================================================
TOOL SELECTION ACCURACY BENCHMARK
================================================================================

Total queries tested: 20

Precision@3 (correct tool in top-3):
  14/20 (70.0%)

Precision@5 (correct tool in top-5):
  18/20 (90.0%)

Recall (correct tool found in results):
  19/20 (95.0%)

================================================================================
PER-QUERY RESULTS
================================================================================

✓ SUCCESSES (19):

  ★ Query: search for AI papers on jailbreaking models
    Expected: research_search
    Top-3: ['research_search', 'research_deep', 'research_arxiv_search']

  ◆ Query: fetch and analyze the content at https://example.com
    Expected: research_fetch
    Top-3: ['research_fetch', 'research_markdown', 'research_spider']

✗ FAILURES (1):

  ✗ Query: detect steganography and hidden content
    Expected: research_stego_detect
    Got (top-5): ['research_metadata_forensics', 'research_leak_scan', ...]
    Description: Should recommend steganography detection
```

**Symbols:**
- `★` = Found in top-3 (excellent match)
- `◆` = Found in top-5 (good match)
- `•` = Found in top-5+ (acceptable)
- `✗` = Not found (needs improvement)

### Improving Tool Selection

When precision/recall is low:

1. **Add more discriminative queries** to reveal weak tool similarity
2. **Rebuild embeddings** if tools were recently added/modified:
   ```bash
   # Trigger embedding rebuild
   curl http://127.0.0.1:8787/research_semantic_router_rebuild
   ```

3. **Enhance tool descriptions** — More descriptive docstrings improve matching:
   ```python
   # Before
   async def research_fetch(url: str):
       """Fetch URL content."""
   
   # After
   async def research_fetch(url: str):
       """Fetch and extract text from a single URL.
       
       Uses 3-tier escalation (HTTP → stealthy → dynamic) to bypass
       bot detection. Returns cleaned text, metadata, and links.
       """
   ```

4. **Check embedding method** — Response includes which fallback was used:
   ```python
   response = await research_semantic_route(query, top_k=5)
   print(response.get("embedding_method"))  # "sentence-transformers", "tfidf", or "keyword"
   ```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Quality Checks
on: [push, pull_request]

jobs:
  mutation-testing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install mutmut pytest
      - run: ./scripts/run_mutation_test.sh
      
  tool-selection-benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install -e .[all]
      - run: pytest tests/comprehensive/test_tool_selection.py -v
```

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/run_mutation_test.sh` | 95 | Mutation testing automation script |
| `tests/comprehensive/test_tool_selection.py` | 439 | Tool selection accuracy benchmark |
| `docs/MUTATION_TESTING_GUIDE.md` | This file | Configuration & interpretation guide |

## Quick Reference

### Run Everything

```bash
# Mutation testing
./scripts/run_mutation_test.sh

# Tool selection benchmark
pytest tests/comprehensive/test_tool_selection.py -v --tb=short
```

### Check Test Effectiveness

```bash
# After writing new tests, verify they catch mutations
mutmut run --paths-to-mutate=src/loom/your_module.py \
  --runner="pytest tests/test_your_module.py -x -q"
mutmut results
```

### Optimize Tool Recommendations

```bash
# Check if semantic router is using embeddings or fallback
python3 -c "
import asyncio
from loom.tools.semantic_router import research_semantic_route
result = asyncio.run(research_semantic_route('search papers'))
print(f\"Method: {result.get('embedding_method')}\")
print(f\"Tools: {[t['name'] for t in result['recommended_tools'][:3]]}\")
"
```

## Related Documentation

- [Architecture Guide](./architecture.md) — Tool design patterns
- [Tools Reference](./tools-reference.md) — All 220+ tool specifications
- [Testing Guide](../README.md#testing) — Overall testing strategy
