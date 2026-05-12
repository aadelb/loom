# Loom-Legal: Architecture Decision Records (ADRs)

---

## ADR-001: Plugin Package vs. Core Integration

**Status**: Accepted

**Context**: Loom-legal extends Loom with 20+ UAE legal tools. Two approaches:
1. **Plugin Package** (separate repo, installed via pip, entry_points discovery)
2. **Core Integration** (direct addition to loom/tools/, part of Loom core)

**Decision**: Plugin Package (standalone loom-legal repository)

**Consequences**:

### Positive
- Loom core remains domain-agnostic (not UAE-specific)
- loom-legal can release independently (bug fixes, new tools, API updates)
- Easier for users to opt-in (only install if needed)
- Clear separation of concerns (research infrastructure ≠ legal domain)
- Version compatibility managed per package (no coupling)

### Negative
- Requires entry_points mechanism (adds complexity to server.py discovery)
- Installation dependency: loom-legal depends on loom-research (must install core first)
- Development requires coordinating two repos (CI/CD, PR reviews)
- Entry point loading is implicit (harder to debug if registration fails)

### Risks
- **Entry point discovery fails silently**: Mitigate with `research_validate_startup()` that logs all registered plugins
- **Version mismatch**: Loom API changes break loom-legal. Mitigate with semantic versioning + compatibility matrix

---

## ADR-002: Data Source Architecture (Clients vs. Direct HTTP)

**Status**: Accepted

**Context**: How to access UAE government APIs + portals?
- Option A: Direct HTTP calls in each tool function (simpler, more duplication)
- Option B: Dedicated source clients (uae_legislation.py, dubai_law.py, etc.) with shared retry/rate limit logic

**Decision**: Dedicated source clients in loom_legal/sources/

**Consequences**:

### Positive
- Rate limiting + retry logic centralized (one place to fix bugs)
- API auth tokens managed in one place (easier rotation)
- Caching layer can wrap sources (not individual tools)
- Testing: mock entire source client, not individual tools
- Code reuse: multiple tools call same source (e.g., research_uae_legislation + research_uae_law_amendment both use uae_legislation client)

### Negative
- Extra indirection (tool → source client → HTTP)
- Each source client is ~150-200 LOC (8 clients = 1200+ LOC)
- If source API changes, must update both client + tools

### Risks
- **Source unavailable**: Mitigate with fallback to cache + graceful degradation
- **Auth token expiry**: Mitigate with automatic refresh 1 hour before expiry

---

## ADR-003: Caching Strategy (Per-Tool vs. Per-Source)

**Status**: Accepted

**Context**: Where to cache results?
- Option A: Each tool caches individually
- Option B: Centralized cache at source client level
- Option C: Hybrid (cache at both levels)

**Decision**: Hybrid caching
- **Level 1 (Source Client)**: Raw API responses cached for 1 day
- **Level 2 (Tool)**: Processed results cached per tool parameters for variable TTL

**Consequences**:

### Positive
- Avoids repeated API calls for same raw data (Level 1)
- Tools with light processing can reuse cache hits (Level 1)
- Tools with heavy processing (NLP, synthesis) cache independently (Level 2)
- Example: research_uae_legislation + research_uae_law_amendment both benefit from Level 1 cache of legislation_db
- TTL tuned per tool (legislation: 7 days, company registry: 1 day)

### Negative
- Dual caching adds complexity (when does L1 evict? L2?)
- Harder to reason about cache freshness (which layer is stale?)

### Risks
- **Cache coherence**: If L1 updates but L2 doesn't, tools return stale data. Mitigate with explicit versioning (cache key includes source hash)

---

## ADR-004: Arabic Language Support (UTF-8 vs. Transliteration)

**Status**: Accepted

**Context**: UAE legal data is bilingual (Arabic + English). How to handle?
- Option A: English-only (simple, loses ~50% of data)
- Option B: UTF-8 native Arabic (complex, encoding issues on some clients)
- Option C: UTF-8 + transliteration fallback (complex, data duplication)

**Decision**: Full UTF-8 + transliteration fallback
- All tool results include both `title_ar` (UTF-8) and `title_ar_transliterated` (Buckwalter/DIN 31635)
- Default: return UTF-8 Arabic
- Fallback: If client cannot render, use transliteration

**Consequences**:

### Positive
- Supports all clients (modern UTF-8 + legacy ASCII-only systems)
- Users can request either format via `transliterate=True/False` parameter
- Preserves full semantic meaning (transliteration is best-effort)

### Negative
- All results are 50% larger (2x strings in response)
- Transliteration libraries imperfect (homographs have multiple forms)

### Risks
- **Bad transliteration**: Mitigate by using standard DIN 31635, only on display (preserve UTF-8 in storage)

---

## ADR-005: NLP Model Strategy (AraLegal-BERT vs. Off-the-Shelf)

**Status**: Accepted

**Context**: Tools 23-24 need Arabic legal text classification + NER. Options:
- Option A: Use off-the-shelf BERT (AraBERT, CAMeLBERT) — less accurate, simpler
- Option B: Fine-tune AraLegal-BERT on 50K+ legal documents — better accuracy, but training cost
- Option C: Use only rule-based NLP (regex + heuristics) — fastest, least accurate

**Decision**: AraLegal-BERT fine-tuned model (via sentence-transformers)
- Pre-trained weights downloaded on first use (model cached in ~/.cache/loom/models/)
- Fine-tuning on 50K legal documents (from University of Dubai corpus + court decisions)
- Inference: fast enough for sync requests (<2s)

**Consequences**:

### Positive
- State-of-the-art accuracy for legal document classification
- Supports both Arabic + English (model trained on both)
- Model cached locally (no API call, no rate limits, offline-capable)

### Negative
- Model size ~400MB (downloads once, stored locally)
- Optional dependency (`pip install loom-legal[nlp]`) to avoid bloat for non-NLP users
- Training corpus requires copyright clearance

### Risks
- **Model size**: Mitigate with optional dependency + clear documentation
- **Training requires labeled data**: Mitigate by licensing existing UAE legal corpus from University of Dubai

---

## ADR-006: Jurisdiction Precedence & Conflict Resolution

**Status**: Accepted

**Context**: UAE has overlapping jurisdictions (federal, emirate, DIFC, ADGM). Which law applies?
- Federal law applies generally, but emirates can enact stricter laws (labor law exception: Federal Law 33/2021 overrides emirate versions)
- DIFC = Dubai + separate jurisdiction (DIFC law applies to DIFC transactions only)
- ADGM = Abu Dhabi + separate jurisdiction

**Decision**: Tool results include explicit jurisdiction scope + conflict resolution guidance
- Each result has `jurisdiction` field: "UAE" | "Dubai" | "DIFC" | "ADGM"
- research_jurisdiction_compare() shows conflicts + which law takes precedence (with explanation)
- Default assumption: Federal law applies unless context suggests otherwise

**Consequences**:

### Positive
- Users can't accidentally apply wrong jurisdiction
- Conflicts highlighted explicitly
- research_jurisdiction_compare() provides legal reasoning for precedence

### Negative
- Complex jurisdiction logic increases tool logic by ~20%
- Legal precedence is sometimes ambiguous (requires lawyer judgment)

### Risks
- **Incorrect precedence**: Mitigate with disclaimer in docs ("Results for informational purposes; consult lawyer for binding advice")

---

## ADR-007: PII Handling & Privacy

**Status**: Accepted

**Context**: Court decisions + labor disputes contain personal information (names, IDs, addresses). How to handle?
- Option A: Include full PII (useful for practitioners, but privacy risk)
- Option B: Auto-mask all PII (privacy-safe, less useful)
- Option C: Configurable masking (default mask, override with explicit flag)

**Decision**: Configurable masking (default mask)
- National IDs: [REDACTED-ID-****]
- Personal names: [REDACTED-PERSON-**** ]
- Emails/phones: [REDACTED-CONTACT]
- Addresses: City only (no street/building)
- **Override**: `include_pii=True` (logs audit event, requires explicit parameter)

**Consequences**:

### Positive
- Privacy-safe by default (GDPR-aligned)
- Power users can opt-in to full data when needed
- Audit trail tracks PII access

### Negative
- NER required to detect PII (adds ~500ms to processing)
- False positives: names that aren't actually names get masked
- Some users may disable masking by default (security risk)

### Risks
- **PII leakage**: Mitigate with comprehensive NER testing + audit logging for all include_pii=True calls

---

## ADR-008: Rate Limiting & Quota Management

**Status**: Accepted

**Context**: Government APIs have rate limits (moj.gov.ae: 100 req/hr; DIFC: 500 req/hr). How to enforce?
- Option A: Per-source limits (enforce source's declared limit)
- Option B: Global limit per user (all tools share a bucket)
- Option C: Tool-specific limits (each tool has own quota)

**Decision**: Per-source limits (enforce source's declared limit)
- Configured in source client: moj_client.rate_limit = 100 / 3600  # 100 req/hr
- Shared across all tools using that source
- Backoff: exponential (1s, 2s, 4s, ...) on 429 response
- Fallback: Return cached result if fresh cache available

**Consequences**:

### Positive
- Respects each source's API terms
- Simple to implement (each source client has rate limiter)
- Backoff prevents cascading failures

### Negative
- Users see intermittent 429s if they exceed quota (may be confusing)
- Cache fallback may return stale data (trade-off: stale data > no data)

### Risks
- **Users bypass rate limits**: Mitigate with per-user token buckets (advanced feature, Phase 3)

---

## ADR-009: Tool Wrapper Pattern (MCP vs. Direct)

**Status**: Accepted

**Context**: Each tool is implemented twice:
1. `research_uae_legislation(...)` — Python function (core logic)
2. `tool_wrapper_legislation(...)` — MCP-compatible wrapper

Why? MCP requires `tool()` decorator + TextContent return type. Options:
- Option A: Single tool function (no wrapper, but ties business logic to MCP format)
- Option B: Dual implementation (wrapper calls core, more code but cleaner separation)

**Decision**: Dual implementation (wrapper pattern)
- Core tool in loom_legal/tools/: Pure Python, returns dict, testable standalone
- Wrapper in loom_legal/server.py: MCP-decorated, calls core, returns TextContent

**Consequences**:

### Positive
- Core logic decoupled from MCP transport layer
- Tools can be called directly from Python (import and use)
- Easier testing (mock tool returns dict, not TextContent)
- Follows existing Loom pattern (github.py has research_github + tool_github)

### Negative
- Extra 20 lines of boilerplate per tool (26 tools × 2-3 lines = 50+ extra lines)

### Risks
- **Wrapper bugs**: Mitigate by keeping wrapper simple (just call core + format output)

---

## ADR-010: Error Handling & Graceful Degradation

**Status**: Accepted

**Context**: Government APIs are sometimes unstable. What happens if moj.gov.ae is down?
- Option A: Return error to user (honest, but unhelpful)
- Option B: Return cached result even if stale (helpful, but misleading)
- Option C: Hybrid (return cached result + flag as `cached_stale=True`)

**Decision**: Hybrid with fallback chain
1. Try fresh API call
2. API error + cache expired → backoff + retry (max 3 times)
3. Still failing + cache available → return cache + `cached_stale=True` + warning
4. No cache + error → return error

```python
result = {
    "results": [...],
    "cached": True,
    "cached_stale": True,
    "warning": "Source API unavailable; returning cached results from 2026-05-01 (6 days old)"
}
```

**Consequences**:

### Positive
- Maximizes availability (graceful degradation)
- Users understand data freshness
- Better UX than returning error

### Negative
- Users may act on stale data (e.g., expired law)
- Adds complexity (fallback chain logic)

### Risks
- **User acts on stale law**: Mitigate with strong warning + timestamp + recommendation to verify

---

## ARCHITECTURAL DECISION MATRIX

### Design Decisions at a Glance

| Decision | Choice | Tradeoff | Risk Mitigation |
|----------|--------|----------|-----------------|
| Plugin vs. Core | Plugin (separate repo) | Independence vs. coupling | Semantic versioning, compatibility matrix |
| Data Access | Source clients | DRY, rate limiting | Complexity |
| Caching | Hybrid (L1+L2) | Efficiency vs. coherence | Versioned cache keys |
| Arabic Support | UTF-8 + transliteration | Completeness vs. size | Standard transliteration (DIN 31635) |
| NLP | AraLegal-BERT | Accuracy vs. model size | Optional dependency |
| Jurisdiction | Explicit scope + guidance | Clarity vs. complexity | Conflict resolution docs |
| PII | Masked by default | Privacy vs. utility | Configurable + audit logging |
| Rate Limiting | Per-source limits | Respect APIs vs. UX | Backoff + cache fallback |
| Tool Pattern | Dual (core + wrapper) | Separation vs. boilerplate | Simple wrapper pattern |
| Error Handling | Graceful degradation | Availability vs. staleness | Warnings + timestamps |

---

## DESIGN PATTERNS USED

### 1. **Source Client Pattern**
Each data source (uae_legislation.gov.ae, moj.gov.ae, etc.) has dedicated client:
```python
# loom_legal/sources/uae_legislation.py
class UAELegislationClient:
    def __init__(self, cache: CacheStore, rate_limiter: RateLimiter):
        self.cache = cache
        self.rate_limiter = rate_limiter
    
    async def search(self, query: str) -> list[dict]:
        # Rate limit check
        # Cache check
        # API call
        # Cache result
        # Return
```

### 2. **Repository Pattern**
Source clients act as repositories (abstract data access):
```python
# In tool implementation:
legislation_repo = UAELegislationClient(...)
laws = await legislation_repo.search(query)
# Tool logic is independent of source

# Easy to swap: new source? New client, tool unchanged
```

### 3. **Fallback Chain Pattern**
Graceful degradation:
```python
def get_with_fallback(primary, secondary, cache):
    try:
        return await primary()
    except TimeoutError:
        try:
            return await secondary()
        except:
            return cache.get(key)  # Fallback to stale cache
```

### 4. **Parameter Object Pattern**
All tool parameters in Pydantic models (validation at entry point):
```python
params = UAELegislationParams(query="...", language="en")
# Invalid params rejected before tool execution
```

---

## IMPLEMENTATION CHECKLIST FOR KIMI/DEEPSEEK

### Phase 1 Infrastructure
- [ ] Create pyproject.toml with entry_points
- [ ] Implement loom_legal/params.py (all 26 tool parameter models)
- [ ] Implement loom_legal/validators.py (query validation, URL checks)
- [ ] Implement loom_legal/cache.py (SHA-256 + TTL)
- [ ] Implement loom_legal/errors.py (exception hierarchy)
- [ ] Implement loom_legal/config.py (API keys, TTLs, defaults)
- [ ] Implement loom_legal/sources/base.py (RateLimiter, retry decorator)
- [ ] Write infrastructure unit tests (90%+ coverage)
- [ ] Verify entry point registration mechanism (manual test: import entry point)

### Phase 2 Data Sources
- [ ] Implement loom_legal/sources/uae_legislation.py
- [ ] Implement loom_legal/sources/dubai_law.py
- [ ] Implement loom_legal/sources/mofa.py
- [ ] Implement loom_legal/sources/difc.py
- [ ] Implement loom_legal/sources/adgm.py
- [ ] Implement loom_legal/sources/bayanat.py
- [ ] Implement loom_legal/sources/court_decisions.py
- [ ] Test each source with mocked HTTP responses
- [ ] Verify rate limiting + retry logic

### Phase 2 Tools (20 tools, parallelizable)
- [ ] research_uae_legislation + test
- [ ] research_federal_law + test
- [ ] research_uae_law_amendment + test
- [ ] research_cabinet_resolution + test
- [ ] research_dubai_law + test
- [ ] research_dubai_decree + test
- [ ] research_dubai_municipality_regulation + test
- [ ] research_court_decision + test
- [ ] research_labor_dispute_decision + test
- [ ] research_commercial_contract_precedent + test
- [ ] research_difc_law + test
- [ ] research_difc_company + test
- [ ] research_adgm_law + test
- [ ] research_adgm_registry + test
- [ ] research_commercial_law + test
- [ ] research_commercial_contract + test
- [ ] research_uae_trademark_law + test
- [ ] research_uae_labor_law + test
- [ ] research_labor_dispute_resolution + test
- [ ] research_uae_criminal_law + test
- [ ] research_criminal_case_decision + test
- [ ] research_personal_status_law + test
- [ ] research_aml_compliance + test
- [ ] research_jurisdiction_compare + test

### Phase 3 NLP + Advanced
- [ ] Download + test AraLegal-BERT model
- [ ] Implement loom_legal/nlp/entity_extract.py (NER)
- [ ] Implement loom_legal/nlp/classifier.py (legal doc classification)
- [ ] Implement research_legal_nlp_classify + test
- [ ] Implement research_legal_entity_extract + test
- [ ] Implement Arabic transliteration (loom_legal/utils/arabic.py)
- [ ] E2E integration tests
- [ ] Documentation (API reference, examples, troubleshooting)

