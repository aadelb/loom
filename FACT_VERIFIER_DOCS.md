# Fact Verifier Tools Documentation

## Overview

The Fact Verifier tools provide cross-source fact verification for claims through multi-provider search and evidence aggregation.

- **research_fact_verify**: Single claim verification
- **research_batch_verify**: Batch claim verification (parallel processing)

## Functions

### research_fact_verify

Verifies a single claim across multiple search providers using agreement-based confidence scoring.

**Signature**
```python
async def research_fact_verify(
    claim: str,
    sources: int = 3,
    min_confidence: float = 0.6,
) -> dict[str, Any]:
```

**Parameters**
- `claim` (str): The claim to verify (5-500 characters)
- `sources` (int, default=3): Number of search results per provider (1-20)
- `min_confidence` (float, default=0.6): Minimum confidence threshold (0.0-1.0)

**Returns**
```python
{
    "claim": str,                           # Original claim
    "verdict": str,                         # "supported" | "contradicted" | "unverified" | "mixed"
    "confidence": float,                    # 0-1 confidence score
    "supporting_sources": list[dict],       # Sources supporting the claim
    "contradicting_sources": list[dict],    # Sources contradicting the claim
    "evidence_summary": str,                # Concise summary of findings
    "total_sources_analyzed": int,          # Count of unique sources
    "error": str | None,                    # Error message if verification failed
}
```

**Source Object Structure**
```python
{
    "url": str,          # Source URL
    "evidence": str,     # Evidence snippet (max 500 chars)
    "title": str,        # Article/source title
    "source": str,       # Source name
}
```

**Confidence Scoring Logic**
- 3+ sources agree: confidence 0.85-1.0 (supported/contradicted)
- 2 sources agree: confidence 0.7 (supported/contradicted)
- 1 source with conflicting: confidence 0.5 (mixed)
- 1 source only: confidence 0.3-0.4 (unverified)
- No sources: confidence 0.1 (unverified)

**Example Usage**
```python
import asyncio
from loom.tools.fact_verifier import research_fact_verify

async def verify_claim():
    result = await research_fact_verify(
        "The Earth is round",
        sources=5,
        min_confidence=0.7
    )
    print(f"Verdict: {result['verdict']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Sources analyzed: {result['total_sources_analyzed']}")

asyncio.run(verify_claim())
```

---

### research_batch_verify

Verifies multiple claims in parallel, ideal for bulk fact-checking operations.

**Signature**
```python
async def research_batch_verify(
    claims: list[str],
    sources: int = 3,
    min_confidence: float = 0.6,
) -> list[dict[str, Any]]:
```

**Parameters**
- `claims` (list[str]): List of claims to verify (1-50 claims, each 5-500 chars)
- `sources` (int, default=3): Number of search results per provider (1-20)
- `min_confidence` (float, default=0.6): Minimum confidence threshold (0.0-1.0)

**Returns**
```python
[
    {
        "claim": str,
        "verdict": str,
        "confidence": float,
        "supporting_sources": list[dict],
        "contradicting_sources": list[dict],
        "evidence_summary": str,
        "total_sources_analyzed": int,
        "error": str | None,
    },
    # ... one dict per claim
]
```

**Example Usage**
```python
import asyncio
from loom.tools.fact_verifier import research_batch_verify

async def verify_multiple():
    results = await research_batch_verify(
        [
            "The Earth is round",
            "Water boils at 100°C",
            "The moon is made of cheese",
        ],
        sources=3,
        min_confidence=0.6
    )
    
    for result in results:
        print(f"\nClaim: {result['claim']}")
        print(f"Verdict: {result['verdict']}")
        print(f"Confidence: {result['confidence']}")

asyncio.run(verify_multiple())
```

---

## Verification Algorithm

### Step 1: Search Phase
The tool searches for the claim across three providers in parallel:
- Exa (semantic search)
- Tavily (multi-domain search)
- Brave (general search)

Each provider returns up to N results (default N=3).

### Step 2: Evidence Extraction
From each search result, the tool extracts:
- URL
- Title
- Snippet (capped at 500 characters)
- Source identifier

### Step 3: Classification
Each source is classified based on keyword analysis:

**Supporting Keywords**
- confirm, support, verify, prove, evidence
- true, yes, agree, right, correct
- valid, authentic, real

**Contradicting Keywords**
- contradict, deny, refute, disprove
- false, no, wrong, disagree
- incorrect, invalid, fake, hoax, misleading

### Step 4: Confidence Calculation
Agreement scoring:
1. Count sources in each category (supporting, contradicting, mixed)
2. Apply confidence thresholds based on agreement levels
3. Filter results below min_confidence (mark as "unverified")

### Step 5: Output Generation
Return structured result with:
- Verdict (supported/contradicted/mixed/unverified)
- Confidence score (0-1)
- Classified sources
- Evidence summary

---

## Error Handling

### Validation Errors
- Claim too short (<5 chars): Returns unverified with error
- Claim too long (>500 chars): Returns unverified with error
- Invalid sources parameter: Auto-corrected to valid range
- Invalid min_confidence: Auto-corrected to 0.6

### Search Errors
- Provider failure: Gracefully skips provider, uses remaining sources
- Network timeout: Returns unverified with error message
- No results from any provider: Returns unverified (0 sources)

### Batch Errors
- Empty claims list: Returns error response
- Too many claims (>50): Auto-capped at 50
- Individual claim failures: Returns per-claim error, batch continues

---

## Performance Characteristics

### Single Claim (research_fact_verify)
- Time: 5-15 seconds (depends on provider response time)
- Search calls: 3 (exa, tavily, brave in parallel)
- Results processed: Up to 3×N (where N=sources param)

### Batch Claims (research_batch_verify)
- Time: ~(5-15s) per claim (parallel batch execution)
- Parallelization: All claims verified concurrently
- Memory: Minimal (streaming results)

### Example Performance
- 1 claim with sources=3: ~8 seconds
- 10 claims with sources=3: ~12 seconds (parallel)
- 50 claims with sources=3: ~15 seconds (batch capped, parallel)

---

## Integration Points

### With research_search
The fact verifier internally uses `research_search` to:
- Query multiple search providers
- Get diverse evidence sources
- Leverage existing caching

### With LLM Tools
Can be combined with `research_llm_summarize` to:
- Create detailed fact-check reports
- Analyze nuanced evidence
- Generate natural language summaries

### With Batch Tools
Pairs well with:
- `research_batch_verify`: Bulk fact-checking
- `research_score_all`: Performance benchmarking
- `research_consensus_build`: Evidence consensus

---

## Use Cases

### 1. Real-time Claim Verification
```python
# Verify a social media claim
result = await research_fact_verify(
    "COVID-19 vaccines contain microchips"
)
```

### 2. Bulk Content Moderation
```python
# Check multiple user claims
claims = extract_claims_from_user_posts()
results = await research_batch_verify(claims)
filtered = [r for r in results if r['verdict'] == 'contradicted']
```

### 3. Research Support
```python
# Verify facts in a research proposal
proposal_facts = extract_factual_claims(proposal)
verifications = await research_batch_verify(proposal_facts)
confidence_report = {
    fact: v['confidence'] 
    for fact, v in zip(proposal_facts, verifications)
}
```

### 4. News Verification
```python
# Fact-check news articles
article_claims = extract_claims_from_article(article)
results = await research_batch_verify(
    article_claims,
    sources=5,  # More sources for news
    min_confidence=0.7
)
```

---

## Configuration

### Parameters Configuration
Set via `research_config_set`:

```python
await research_config_set("FACT_VERIFIER_DEFAULT_SOURCES", "5")
await research_config_set("FACT_VERIFIER_MIN_CONFIDENCE", "0.7")
```

### Search Provider Preferences
Modify provider fallback order via `DEFAULT_SEARCH_PROVIDER` config.

---

## Limitations

### Current Implementation
1. **Keyword-based Classification**: Uses heuristic keyword matching, not semantic understanding
2. **English-focused**: Keywords optimized for English text
3. **Snippet-based**: Only analyzes search result snippets, not full page content
4. **No LLM Analysis**: Doesn't use LLM for nuanced evidence interpretation
5. **Rate Limiting**: Subject to search provider rate limits

### Future Enhancements
- Integrate full-page content analysis via `research_fetch`
- Add LLM-powered semantic classification
- Support multilingual fact-checking
- Add source credibility weighting
- Support fact-check database integration (Snopes, PolitiFact)

---

## API Parameter Validation

### FactVerifyParams
```python
claim: str              # 5-500 chars (required)
sources: int            # 1-20 (default 3)
min_confidence: float   # 0.0-1.0 (default 0.6)
```

### BatchVerifyParams
```python
claims: list[str]       # 1-50 items, each 5-500 chars
sources: int            # 1-20 (default 3)
min_confidence: float   # 0.0-1.0 (default 0.6)
```

---

## Testing

### Unit Tests Location
`tests/test_tools/test_fact_verifier.py`

### Coverage Areas
- Evidence extraction from search results
- Agreement scoring with different source combinations
- Parameter validation
- Error handling
- Batch processing
- Integration with search tools

### Running Tests
```bash
# Unit tests only
pytest tests/test_tools/test_fact_verifier.py -m unit

# Integration tests
pytest tests/test_tools/test_fact_verifier.py -m integration

# All tests
pytest tests/test_tools/test_fact_verifier.py
```

---

## Author Notes

- **Added**: 2026-05-04
- **Status**: Stable
- **Location**: `/Users/aadel/projects/loom/src/loom/tools/fact_verifier.py`
- **Parameters**: `/Users/aadel/projects/loom/src/loom/params/research.py`
- **Registration**: `/Users/aadel/projects/loom/src/loom/registrations/research.py`
