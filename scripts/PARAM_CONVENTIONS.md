# Parameter Naming Conventions

## Overview

This document standardizes parameter naming conventions across all Pydantic models in `src/loom/params.py`. These conventions ensure consistency across 130+ parameter models while maintaining backward compatibility through field aliases.

**Last Updated:** 2026-05-02  
**Scope:** All parameter models in `src/loom/params.py`  
**Breaking Changes:** None (all changes use `Field(alias=...)`for backward compatibility)

---

## Key Principles

1. **Standardize Semantic Meaning:** Parameters with the same semantic purpose use the same name
2. **Backward Compatibility:** Old names remain valid via Pydantic `alias` fields
3. **Minimal Refactoring:** Only add aliases to new/problematic params; don't refactor existing code
4. **Documentation:** All standards documented here for new tool development

---

## Standard Parameter Names

### 1. URL Parameters

#### Primary Standard: `url` (single URL) / `urls` (multiple URLs)

| Parameter | Usage | Use When | Example |
|-----------|-------|----------|---------|
| `url: str` | Single URL target | Fetch, parse, or analyze one document | `FetchParams`, `MarkdownParams`, `DeadContentParams` |
| `urls: list[str]` | Multiple URL targets | Batch fetch/spider multiple documents | `SpiderParams` |
| `domain: str` | Domain/hostname only | DNS, WHOIS, cert analysis (no protocol) | `WhoisParams`, `DNSLookupParams` |

#### Inconsistencies Found & Migration Path

| Existing | Standard | Affected Classes | Status | Notes |
|----------|----------|------------------|--------|-------|
| `url` | `url` ✓ | FetchParams (32 uses) | **STANDARD** | Already dominant |
| `target` | `url` or `domain` | NmapScanParams, NucleiScanParams (4 uses) | NEEDS ALIAS | Use `domain` for host-only, `url` for full URL |
| `target_url` | `url` | DataPoisoningParams, CreepjsParams (3 uses) | NEEDS ALIAS | Add `alias="target_url"` |
| `repo_url` | `url` | GithubReadmeParams, GithubReleasesParams (3 uses) | SEMANTIC-SPECIFIC | Keep; domain = GitHub repos |
| `feed_url` | `url` | RSSFetchParams (1 use) | SEMANTIC-SPECIFIC | Keep; domain = RSS feeds |
| `image_url` | `url` | OCRAdvancedParams, PaddleOCRParams (2 uses) | SEMANTIC-SPECIFIC | Keep; domain = image processing |
| `pdf_url` | `url` | PDFAdvancedParams (1 use) | SEMANTIC-SPECIFIC | Keep; domain = PDF tools |

#### Action Items

- [ ] **`NmapScanParams`**: Change `target: str` → `domain: str` (or `url: str` if full URL expected)
- [ ] **`DataPoisoningParams`**: Add `alias="target_url"` to `url` field
- [ ] **`CreepjsParams`**: Add `alias="target_url"` to `url` field
- [ ] **`NucleiScanParams`**: Clarify if `target` is domain/URL and rename/alias accordingly

---

### 2. Query Parameters

#### Primary Standard: `query`

| Parameter | Usage | Use When |
|-----------|-------|----------|
| `query: str` | Search/analysis query | Text search, semantic search, LLM prompts |

#### Inconsistencies Found & Migration Path

| Existing | Standard | Affected Classes | Status |
|----------|----------|------------------|--------|
| `query` | `query` ✓ | SearchParams, DeepParams, etc. (35 uses) | **STANDARD** |
| `target_query` | `query` | ContextPoisoningParams (1 use) | NEEDS ALIAS |

#### Action Items

- [ ] **`ContextPoisoningParams`**: Add `alias="target_query"` to `query` field

---

### 3. Count/Limit/Result Parameters

#### Primary Standard by Tool Type

| Parameter | Usage | Recommended For | Default |
|-----------|-------|-----------------|---------|
| `max_results: int` | Search result count | General search tools (semantic, graph, analysis) | 10-20 |
| `limit: int` | Record limit | Data fetching tools (RSS, archive, logs) | 10-20 |
| `n: int` | Result count (short form) | Backward compatibility only | 10 |

#### Inconsistencies Found & Migration Path

| Existing | Standard | Count | Affected Classes | Status |
|----------|----------|-------|------------------|--------|
| `limit` | **STANDARDIZE TO `max_results`** | 11 uses | CacheStatsParams, RSSFetchParams, etc. | INCONSISTENT |
| `max_results` | **STANDARDIZE TO `max_results`** | 6 uses | DeepParams, PatentLandscapeParams | PREFERRED |
| `n` | `max_results` | 1 use | SearchParams | LEGACY |
| `num_results` | `max_results` | 1 use | ExaFindSimilarParams | INCONSISTENT |
| `num_sources` | `max_results` | 1 use | ConsensusParams | INCONSISTENT |

#### Rationale

- **`max_results`** is explicit and unambiguous across REST/GraphQL conventions
- **`limit`** is database-specific terminology; less clear in API contexts
- **`n`** is too terse and confuses new developers
- **`num_*`** variations waste cognitive load

#### Action Items

**HIGH PRIORITY:**
- [ ] **`SearchParams`**: Rename `n: int = 10` → `max_results: int = 10` and add `alias="n"`
- [ ] **`ExaFindSimilarParams`**: Rename `num_results` → `max_results` and add `alias="num_results"`

**MEDIUM PRIORITY (batch in next sprint):**
- [ ] Audit all `limit` uses: if fetching results, rename to `max_results`; if fetching paginated records, keep as `limit`
- [ ] Classes to audit: CacheStatsParams, RSSFetchParams, RSSSearchParams, etc.

---

### 4. Timeout Parameters

#### Primary Standard: `timeout`

| Parameter | Usage | Type | Unit | Range |
|-----------|-------|------|------|-------|
| `timeout: int` | Single timeout | seconds | 1-120s typical | Per-tool validation |
| `timeout_per_model: float` | Per-model timeout | seconds | Float for sub-second precision | Specialized |

#### Inconsistencies Found & Migration Path

| Existing | Standard | Count | Affected Classes | Status |
|----------|----------|-------|------------------|--------|
| `timeout` | `timeout` ✓ | 25 uses | FetchParams, MarkdownParams, etc. | **STANDARD** |
| `timeout_per_model` | `timeout_per_model` | 1 use | DaisyChainParams | SEMANTIC-SPECIFIC |

#### Decision

- No migration needed; standard is well-established
- `timeout_per_model` is semantically distinct; keep as-is

---

### 5. Other Common Parameters (Reference)

#### Semantic-Specific (Keep As-Is)

These parameters are domain-specific and should NOT be standardized:

| Parameter | Meaning | Example Classes |
|-----------|---------|-----------------|
| `language` | Language code (ISO 639) | SearchParams, GitHubParams |
| `target_language` | Language for translation | LLMTranslateParams |
| `region` | Geographic region filter | SearchParams |
| `provider` | Data source provider | SearchParams (exa, tavily, etc.) |
| `domain` | Domain/hostname | WhoisParams, DNSLookupParams |
| `model_name` | LLM model identifier | BenchmarkParams, various |
| `session_name` | Browser session identifier | SessionOpenParams, NodriverSessionParams |

#### Avoid Ambiguity (Document Intent Clearly)

Use descriptive names when semantic meaning is unclear:

**GOOD:**
- `include_community: bool` - Explicitly means "add HN/Reddit sentiment"
- `include_citations: bool` - Explicitly means "extract references"
- `max_evidence_sources: int` - Clearly bounds the source count

**AVOID:**
- `include: bool` - Too vague; include what?
- `count: int` - Count of what? Results? Pages? Time units?
- `sources: int` - Same problem as `count`

---

## Implementation Guide

### For New Tools

When defining a new `*Params` model in `src/loom/params.py`:

```python
class MyToolParams(BaseModel):
    """Parameters for my_tool."""
    
    # Use standard names
    url: str  # Single URL
    urls: list[str] | None = None  # Multiple URLs
    query: str  # Search query
    max_results: int = 10  # Result count
    timeout: int = 30  # Timeout in seconds
    
    model_config = {"extra": "forbid", "strict": True}
    
    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)
```

### For Existing Tools with Inconsistencies

Add Pydantic field aliases to maintain backward compatibility:

```python
from pydantic import Field

class MyToolParams(BaseModel):
    """Parameters for my_tool."""
    
    # Standard name with alias for backward compatibility
    url: str = Field(..., alias="target_url")  # Old name still works
    max_results: int = Field(default=10, alias="n")  # SearchParams case
    
    model_config = {"extra": "forbid", "strict": True, "populate_by_name": True}
```

**Key Settings:**
- `populate_by_name=True` - Allows BOTH canonical and aliased names
- `alias="old_name"` - Accepts the old parameter name in API calls

---

## Rollout Plan

### Phase 1 (Immediate)
- [ ] Add this conventions doc to repo
- [ ] Document the 4 core standards (URL, Query, Limit, Timeout)
- [ ] Create aliases for top 3 offenders:
  - [ ] SearchParams: `n` → `max_results` (with alias)
  - [ ] DataPoisoningParams: `target_url` → `url` (with alias)
  - [ ] CreepjsParams: `target_url` → `url` (with alias)

### Phase 2 (Next Sprint)
- [ ] Audit all `limit` vs `max_results` uses
- [ ] Create migration guide for API clients
- [ ] Add validator warnings for deprecated names (optional)

### Phase 3 (Future)
- [ ] Deprecation cycle (v2.x): warn on old names, document sunset date
- [ ] v3.0: remove aliases, only canonical names accepted

---

## How to Check Compliance

### For Code Review

When reviewing new `*Params` models:

1. ✓ Single URL uses `url: str`
2. ✓ Multiple URLs use `urls: list[str]`
3. ✓ Queries use `query: str`
4. ✓ Result counts use `max_results: int` (not `n`, `limit`, `num_results`)
5. ✓ Timeouts use `timeout: int` or `timeout_<qualifier>: float`
6. ✓ Domain/hostname-only use `domain: str` (not `url`)

### For Users/Clients

Old parameter names still work via aliases—no breaking changes:

```python
# Both work identically
client.search(query="cat", n=10)           # Old (deprecated but valid)
client.search(query="cat", max_results=10)  # New (preferred)
```

---

## Summary of Standards

| Category | Standard | Rationale |
|----------|----------|-----------|
| Single URL | `url: str` | Explicit, conventional, 32/47 uses |
| Multiple URLs | `urls: list[str]` | Matches `url` singular/plural pattern |
| Domain/Host | `domain: str` | Semantic difference: no protocol/port |
| Search Query | `query: str` | Explicit, conventional, 35/36 uses |
| Result Count | `max_results: int` | REST convention, unambiguous, explicit |
| Timeout | `timeout: int` | Units in seconds, well-established |

---

## References

- **Pydantic Field Aliases:** https://docs.pydantic.dev/latest/concepts/fields/#field-aliases
- **REST API Naming Guide:** Google Cloud API Design Guide (parameter naming section)
- **Python Conventions:** PEP 8 (variable/parameter naming)

---

## Questions?

For questions or edge cases, refer to the tool's domain semantics:
- **Network tools:** Use domain/url per context
- **Search tools:** Always use `query` and `max_results`
- **Data tools:** Use `limit` only for database pagination; otherwise `max_results`
- **Time-sensitive:** Use `timeout` with units specified
