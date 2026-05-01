# Parameter Standardization Checklist

## Quick Reference

### Standards Established

| Parameter Type | Standard Name | Alternative Names | Status |
|---|---|---|---|
| Single URL | `url: str` | target_url, endpoint_url | ✓ Standardized |
| Multiple URLs | `urls: list[str]` | - | ✓ Standardized |
| Domain/Host | `domain: str` | target, host | ✓ Documented |
| Query/Search | `query: str` | target_query, search_query, q | ✓ Documented |
| Result Count | `max_results: int` | n, limit, num_results | ✓ Standardized |
| Timeout | `timeout: int` | timeout_seconds | ✓ Documented |

### Changes Made

- [x] **SearchParams**: `n` → `max_results` (with alias "n")
- [x] **ExaFindSimilarParams**: `num_results` → `max_results` (with alias "num_results")
- [x] **DataPoisoningParams**: `target_url` → `url` (with alias "target_url")
- [x] **CreepjsParams**: `target_url` → `url` (with alias "target_url")

### Files Created

- [x] **scripts/PARAM_CONVENTIONS.md** — Comprehensive standardization guide
- [x] **PARAM_ANALYSIS_RESULTS.md** — Detailed analysis and implementation details
- [x] **PARAM_STANDARDIZATION_CHECKLIST.md** — This file

### Backward Compatibility

- [x] All changes use Pydantic `Field(alias=...)`
- [x] All modified models set `populate_by_name=True`
- [x] All existing client code continues to work unchanged
- [x] Zero breaking changes

### Next Steps (Future Phases)

#### Phase 2: Additional Standardizations
- [ ] Audit remaining `limit` parameters (11 uses)
- [ ] Add aliases for `target` → `url` or `domain` (4 uses)
- [ ] Add aliases for other `*_url` patterns
- [ ] Standardize `num_*` parameters (num_results, num_sources)

#### Phase 3: Deprecation Cycle
- [ ] Add deprecation warnings for old parameter names (optional)
- [ ] Update API documentation with new names
- [ ] Create migration guide for API consumers

#### Phase 4: v3.0 Cleanup
- [ ] Remove all aliases (major version bump)
- [ ] Only canonical names accepted
- [ ] Update all examples and documentation

### For Code Reviewers

When reviewing new `*Params` models, check:

- [ ] Single URL uses `url: str` (not `target_url`, `endpoint_url`)
- [ ] Multiple URLs use `urls: list[str]`
- [ ] Queries use `query: str` (not `search_query`, `q`)
- [ ] Result counts use `max_results: int` (not `n`, `limit`, `num_results`)
- [ ] Timeouts use `timeout: int` (not `timeout_seconds`)
- [ ] Domain/host-only use `domain: str` (not `url`)

### Implementation Template

For new parameters, use this pattern:

```python
from pydantic import BaseModel, Field

class MyToolParams(BaseModel):
    """Parameters for my_tool."""
    
    # Standard names
    url: str  # Single URL
    query: str  # Search query
    max_results: int = 10  # Result count
    timeout: int = 30  # Timeout in seconds
    
    model_config = {"extra": "forbid", "strict": True, "populate_by_name": True}
    
    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)
```

For transitioning inconsistent parameters, add an alias:

```python
# For renaming n → max_results
max_results: int = Field(default=10, alias="n")

# For renaming target_url → url
url: str = Field(..., alias="target_url")

# Remember to set populate_by_name=True in model_config
model_config = {"extra": "forbid", "strict": True, "populate_by_name": True}
```

### Verification Commands

Check if all changes are applied:

```bash
# Check SearchParams
grep -A 2 "class SearchParams" src/loom/params.py | grep "max_results.*alias"

# Check ExaFindSimilarParams
grep -A 2 "class ExaFindSimilarParams" src/loom/params.py | grep "max_results.*alias"

# Check DataPoisoningParams
grep -A 2 "class DataPoisoningParams" src/loom/params.py | grep "url.*alias"

# Check CreepjsParams
grep -A 2 "class CreepjsParams" src/loom/params.py | grep "url.*alias"

# Verify syntax
python3 -m py_compile src/loom/params.py
```

### Related Documentation

- **Full Guide:** `scripts/PARAM_CONVENTIONS.md`
- **Analysis Results:** `PARAM_ANALYSIS_RESULTS.md`
- **Tools Reference:** `docs/tools-reference.md`
- **Architecture:** `docs/architecture.md`

---

**Last Updated:** 2026-05-02  
**Status:** Phase 1 Complete ✓  
**Next Phase:** 2-3 weeks (after current sprint)
