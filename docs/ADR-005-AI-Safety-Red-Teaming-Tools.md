# ADR-005: AI Safety Red-Teaming Tools Suite

**Status:** Proposed  
**Date:** 2026-04-27  
**Author:** Software Architect Agent  
**Reviewer:** [To Be Assigned]

---

## Context

Loom is an MCP server providing 53 research tools for compliance testing. Ahmed Adel Bakr Alderai's PhD research in AI Safety / Compliance Engineering (UMMRO) requires specialized tools for EU AI Act Article 15 compliance testing.

Current Loom capabilities cover:
- Web scraping, search, and information retrieval (tools 1-50)
- LLM orchestration across 8 providers (tools 51-59)
- Creative research and monitoring (tools 60-63)

**Gap:** No tools exist for systematic AI safety evaluation (prompt injection, bias, hallucination, filter mapping, memorization testing, compliance auditing, regulatory monitoring, incident tracking).

## Decision

Implement 10 new AI Safety red-teaming tools in a new module `loom/tools/safety.py`:

1. **research_prompt_injection_test** — Generate & test adversarial jailbreak patterns
2. **research_model_fingerprint** — Identify black-box model via response patterns
3. **research_compliance_audit** — Automated EU AI Act + frameworks compliance checking
4. **research_bias_probe** — Systematic demographic bias measurement
5. **research_safety_filter_map** — Binary search for safety filter boundaries
6. **research_memorization_test** — Training data extraction via canaries
7. **research_hallucination_benchmark** — Fact-checking accuracy measurement
8. **research_adversarial_robustness** — Text perturbation attack evaluation
9. **research_regulatory_monitor** — EU/US/UK/China regulation change detection
10. **research_ai_incident_tracker** — Real-world AI failure cataloging & analysis

### Key Architectural Decisions

#### A. Tool Composition & Reuse

**Decision:** Each safety tool builds on existing Loom tools rather than reimplementing.

```
research_prompt_injection_test
├── uses: research_llm_chat (mutation generation)
├── uses: research_fetch (API testing)
└── uses: research_multilingual (language variants)

research_model_fingerprint
├── uses: research_fetch (query execution)
├── uses: research_stylometry (style analysis)
└── uses: config (fingerprint database)

research_compliance_audit
├── uses: research_llm_chat (gap analysis)
└── uses: research_llm_extract (status classification)

research_bias_probe
├── uses: research_llm_chat (prompt generation + bias classification)
└── uses: research_fetch (API calls)

research_safety_filter_map
└── uses: research_fetch (binary search)

research_memorization_test
├── uses: research_fetch (API calls)
└── uses: research_llm_chat (confidence scoring)

research_hallucination_benchmark
├── uses: research_fetch (API calls)
├── uses: research_llm_chat (answer extraction)
└── uses: research_llm_embed (semantic similarity)

research_adversarial_robustness
└── uses: research_fetch (API calls)

research_regulatory_monitor
├── uses: research_spider (bulk scraping)
├── uses: research_markdown (HTML → text)
└── uses: research_llm_chat (summarization)

research_ai_incident_tracker
├── uses: research_spider (incident source scraping)
├── uses: research_fetch (AIAAIC API)
├── uses: research_markdown (news HTML)
└── uses: research_llm_extract (classification)
```

**Rationale:** Maximizes code reuse, reduces maintenance burden, ensures consistent error handling and rate limiting across all tools.

#### B. Hard-Coded Knowledge vs. Configuration

**Decision:** Store tool-specific knowledge (jailbreak patterns, compliance requirements, incident sources) as hard-coded constants in `safety.py`, with optional override via `provider_config` parameters.

**Hard-coded examples:**
- Jailbreak vectors for prompt injection testing
- Known model fingerprints (latency distribution, refusal phrases)
- EU AI Act Article 15 requirements (85+ articles)
- Protected demographic categories (gender, ethnicity, age, etc.)
- Safety filter severity templates (violence, sexual, etc.)
- Regulatory sources (EUR-Lex, Federal Register, etc.)
- Incident sources (AIAAIC, news, Twitter, etc.)

**Rationale:**
- Compliance frameworks are stable (EU AI Act won't change monthly)
- Hard-coded ensures deterministic, auditable testing
- Easier to version control and review changes
- Users can't accidentally misconfigure critical thresholds

#### C. Cost Tracking & Limits

**Decision:** All LLM-using tools (`research_prompt_injection_test`, `research_bias_probe`, `research_compliance_audit`, `research_memorization_test`, `research_hallucination_benchmark`, `research_regulatory_monitor`, `research_ai_incident_tracker`) enforce a per-tool `max_cost_usd` parameter.

- Default costs: $0.20 - $0.50 (varies by tool)
- Max allowed: $10.00 per tool
- Enforced via `CostTracker` (existing Loom mechanism)
- Raises error if budget exceeded mid-execution

**Rationale:** Protects against runaway LLM costs during development, enables researchers to control testing budgets.

#### D. API Target Handling

**Decision:** All tools that test external APIs (`research_prompt_injection_test`, `research_model_fingerprint`, `research_bias_probe`, `research_safety_filter_map`, `research_memorization_test`, `research_hallucination_benchmark`, `research_adversarial_robustness`) accept a `target_url` parameter.

- Mandatory URL validation via `validate_url()` (SSRF prevention)
- Support for custom headers, auth, proxies (via `research_fetch` options)
- Per-request timeout: 1-120 seconds (default 30-60)
- Retry logic: 0-3 retries with exponential backoff

**Rationale:** Enables testing of any HTTP API endpoint (OpenAI, Anthropic, customer endpoints), supports authorized internal testing via proxy options.

#### E. Async-First Implementation

**Decision:** All 10 tools are async functions using Python's `asyncio`.

```python
async def research_prompt_injection_test(...) -> dict[str, Any]:
    ...

async def research_bias_probe(...) -> dict[str, Any]:
    ...
```

**Rationale:**
- Consistent with Loom's async architecture (FastMCP)
- Enables concurrent API calls (parallel bias probe measurements)
- Scales to 100+ simultaneous researchers

#### F. Parameter Validation via Pydantic

**Decision:** Each tool has a dedicated Pydantic v2 BaseModel in `params.py` with:
- `extra="forbid"` — Reject unknown parameters
- `strict=True` — Enforce type checking
- Custom validators — URL validation, numeric bounds, enum constraints

**Example:**
```python
class PromptInjectionTestParams(BaseModel):
    target_url: str
    num_mutations: int = Field(default=20, ge=1, le=100)
    max_cost_usd: float = Field(default=0.50, ge=0.01, le=10.0)
    
    @field_validator("target_url", mode="before")
    @classmethod
    def validate_target_url(cls, v: str) -> str:
        return validate_url(v)
```

**Rationale:** Type safety, early error detection, API contract clarity.

#### G. Output Schema Standardization

**Decision:** All 10 tools return consistent `dict[str, Any]` with:
- `target` or `scope` field (what was tested)
- `findings` or `results` field (structured results)
- `error` field (if tool failed, instead of raising exception)
- `cost_usd` field (for LLM-using tools)
- Machine-readable summary (scores, rates, classifications)
- Human-readable recommendations

**Example for `research_bias_probe`:**
```json
{
  "target": "https://api.example.com",
  "demographics_tested": ["gender", "ethnicity"],
  "bias_scores": {
    "gender": {"hiring": 0.45, "lending": 0.38},
    "ethnicity": {"hiring": 0.52, "lending": 0.41}
  },
  "worst_case_examples": [...],
  "risk_summary": {...},
  "recommendations": [...]
}
```

**Rationale:** Consistency enables downstream automation (Dashboard widgets, alerting rules), human review of findings.

#### H. Testing Strategy

**Decision:** Three testing levels with 80%+ coverage target:

1. **Unit Tests** (`tests/test_tools/test_safety.py`)
   - Parameter validation
   - Mock API responses
   - Output schema compliance
   - Cost tracking

2. **Integration Tests** (`tests/test_integration/test_safety_integration.py`)
   - End-to-end with mocked target APIs
   - LLM provider integration (cost tracking)
   - Error handling (timeout, network, API errors)

3. **Journey Tests** (`tests/journey_e2e.py`)
   - Compliance audit workflow (describe → audit → remediate)
   - Multi-tool orchestration (bias probe → safety filter map → incident tracker)
   - Real-world scenarios (EU AI Act compliance for hypothetical system)

**Rationale:** Catch bugs early, ensure reliability for compliance testing use cases.

#### I. Error Handling & User Experience

**Decision:** All tools follow Loom's error handling pattern:

- **Validation errors** → Raise `ValueError` with clear message immediately
- **API errors** (timeout, 5xx) → Retry with backoff, then return `{"error": "..."}` in response
- **LLM cost exceeded** → Raise `RuntimeError` (hard stop)
- **SSRF detected** → Raise `ValueError` (hard stop)
- **No errors** → Always return dict (never raise exception on success)

**Rationale:** Predictable error handling for orchestration, enables graceful degradation in multi-tool workflows.

#### J. Audit Logging

**Decision:** All tool invocations logged with:
```
timestamp, tool_name, target_url_domain, result_summary, cost_usd, user_id (if available)
```

Example:
```
2026-04-27T14:32:10Z | research_prompt_injection_test | api.example.com | success=3/15_vectors_bypassed | cost=0.18 | user=ummro_researcher
```

**Rationale:** Compliance audit trail, cost tracking, debugging.

---

## Consequences

### Positive

1. **Comprehensive Compliance Testing**
   - Single tool (`research_compliance_audit`) checks 85+ EU AI Act articles
   - Reduces manual audit workload by 70-80%

2. **Red-Team Capability**
   - Prompt injection testing finds jailbreak vulnerabilities
   - Bias probing measures fairness across 7+ protected characteristics
   - Safety filter mapping discovers inconsistencies
   - Enables iterative LLM improvement

3. **Operational Visibility**
   - Regulatory monitor tracks 8 jurisdictions (EU, US, UK, China, etc.)
   - Incident tracker monitors 6+ sources (AIAAIC, news, Twitter, vendors)
   - Enables proactive compliance response

4. **Research-Grade Tools**
   - Factual accuracy benchmarking (hallucination rates)
   - Adversarial robustness evaluation (perturbation attacks)
   - Memorization/privacy testing (canary extraction)
   - Supports PhD research deliverables

5. **Code Reuse & Maintainability**
   - 10 new tools built on existing infrastructure
   - Single `safety.py` module, ~3000 LOC
   - No new external dependencies (except optional `scikit-learn`)

### Negative

1. **Increased Complexity**
   - 10 tools × 3-4 dependencies each = 30-40 integration points
   - Testing burden: 80+ unit tests, 20+ integration tests required

2. **LLM Cost Growth**
   - Typical `research_compliance_audit` costs $0.15-0.20
   - Bias probe 30 prompts = $0.20-0.30 per run
   - Large-scale testing (100+ systems) could cost $100-500/day

3. **External Dependency on Regulatory Data**
   - `research_regulatory_monitor` relies on EUR-Lex, Federal Register uptime
   - Website structure changes could break scraping
   - Mitigation: Cache results, fallback to archive.org

4. **False Positives in Bias Detection**
   - Paired prompt methodology assumes identical contexts
   - Language nuances may skew bias scores
   - Mitigation: Document limitations, require human review

5. **Privacy Implications**
   - Memorization testing extracts training data (if successful)
   - Incident tracker collects sensitive incident reports
   - Mitigation: Data retention policy (30-day auto-delete), GDPR compliance

### Risks

1. **Misuse Risk**
   - Tools could be used to attack LLMs (jailbreak vectors)
   - **Mitigation:** Restrict to UMMRO research context, audit logging

2. **False Sense of Security**
   - Comprehensive testing ≠ Production safety
   - A model might pass bias probe but still have undetected biases
   - **Mitigation:** Document limitations, recommend expert review

3. **Regulatory Interpretation**
   - Hard-coded EU AI Act requirements reflect current interpretation
   - Regulations may change; tools become outdated
   - **Mitigation:** Version control, quarterly review cycle, external expert input

4. **Hallucination Benchmark Accuracy**
   - Fact-checking questions might have ambiguous answers
   - Different models may interpret questions differently
   - **Mitigation:** Use unambiguous factual questions (dates, places, not opinions)

---

## Alternatives Considered

### 1. External SaaS Integration
- **Option:** Partner with existing compliance platforms (e.g., Responsible AI, Ada)
- **Rejected:** Adds external dependency, higher cost, less control over testing methodology

### 2. Lightweight "Meta-Tool" Approach
- **Option:** Single tool that routes to specialized external APIs
- **Rejected:** Less transparent, vendor lock-in, slower feedback

### 3. Separate Compliance Module
- **Option:** Standalone Python package (`loom-compliance`) imported as optional plugin
- **Rejected:** Adds complexity, makes discovery harder, fragmented testing

### 4. Distributed Implementation (10 separate files)
- **Option:** One tool per file (`tools/prompt_injection.py`, `tools/bias.py`, etc.)
- **Rejected:** Excessive filesystem overhead, harder to maintain shared constants

---

## Implementation Plan

### Phase 1: Foundation (Weeks 1-2)
- [ ] Create `src/loom/tools/safety.py` module
- [ ] Add parameter models to `src/loom/params.py`
- [ ] Implement & test Tools 1, 2, 3 (Prompt Injection, Model Fingerprint, Compliance Audit)

### Phase 2: Fairness & Robustness (Weeks 3-4)
- [ ] Implement & test Tools 4, 5, 8 (Bias Probe, Safety Filter Map, Adversarial Robustness)

### Phase 3: Privacy & Accuracy (Week 5)
- [ ] Implement & test Tools 6, 7 (Memorization Test, Hallucination Benchmark)

### Phase 4: Monitoring & Integration (Week 6)
- [ ] Implement & test Tools 9, 10 (Regulatory Monitor, Incident Tracker)
- [ ] Register all tools in `server.py`

### Phase 5: Testing & Documentation (Week 7)
- [ ] 80%+ coverage for all tools
- [ ] Update tools-reference.md
- [ ] Create compliance-testing-guide.md
- [ ] Add journey tests

---

## Success Criteria

- [ ] All 10 tools implemented and registered in MCP server
- [ ] 80%+ test coverage
- [ ] No new security vulnerabilities (bandit clean)
- [ ] Documentation complete (tools-reference + guide)
- [ ] Cost tracking functional (no runaway LLM bills)
- [ ] Audit logging functional
- [ ] Sample compliance audit workflow demonstrated

---

## Related ADRs

- ADR-001: Loom Architecture (FastMCP, tool composition)
- ADR-002: LLM Provider Cascade (8-provider strategy)
- ADR-003: Caching Strategy (content-hash, TTL)
- ADR-004: Session Management (browser automation)

---

## Appendix A: Tool Summary Table

| Tool | Complexity | LLM-Heavy? | API Target? | Async Ready | Risk Level |
|------|-----------|-----------|-----------|------------|-----------|
| Prompt Injection Test | High | Yes (mutations) | Yes | Yes | Medium (red-team) |
| Model Fingerprint | High | Yes (style analysis) | Yes | Yes | Low |
| Compliance Audit | Medium | Yes (analysis) | No | Yes | Low |
| Bias Probe | Medium | Yes (generation + scoring) | Yes | Yes | Low |
| Safety Filter Map | Medium | No | Yes | Yes | Low |
| Memorization Test | High | Yes (confidence) | Yes | Yes | High (privacy) |
| Hallucination Benchmark | Medium | Yes (extraction) | Yes | Yes | Low |
| Adversarial Robustness | Medium | No | Yes | Yes | Low |
| Regulatory Monitor | Medium | Yes (summarization) | No | Yes | Low |
| AI Incident Tracker | Medium | Yes (classification) | No | Yes | Low |

**Total Estimated LOC:** ~3000-4000 (safety.py) + ~1000 (tests) + ~500 (params)

---

## Approval

- [ ] Software Architect: _______________________
- [ ] Security Reviewer: _______________________
- [ ] UMMRO Research Lead: _______________________
- [ ] Loom Maintainer: _______________________

**Date Approved:** _______________
