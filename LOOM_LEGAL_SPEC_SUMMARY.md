# Loom-Legal: Specification Summary & Quick Reference

**Total Documents**: 5 comprehensive specifications  
**Total Pages**: ~100 pages (if printed)  
**Implementation Phases**: 3 (8 weeks total)  
**Target Tools**: 26 (organized in 10 categories)  
**Data Sources**: 8 major UAE government APIs + portals  

---

## DOCUMENT ROADMAP

| Document | Purpose | Audience | When to Read |
|----------|---------|----------|--------------|
| **LOOM_LEGAL_UNIFIED_SPEC.md** | Complete specification (14 sections) | Everyone | **START HERE** |
| **LOOM_LEGAL_ARCHITECTURE_DECISIONS.md** | ADRs + design rationale (10 ADRs) | Architects, Tech Leads | After reading unified spec |
| **LOOM_LEGAL_DESIGN_COMPARISON.md** | Comparison framework for Kimi/DeepSeek designs | Review teams | After both designs available |
| **LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md** | Code stubs + patterns | Developers | During Phase 1 implementation |
| **LOOM_LEGAL_SPEC_SUMMARY.md** | Quick reference (this file) | Everyone | Anytime for quick lookup |

---

## QUICK REFERENCE

### Package Structure (One Minute)

```
loom-legal/
├── src/loom_legal/
│   ├── __init__.py
│   ├── server.py              ← Entry point (_register_legal_tools)
│   ├── params.py              ← 26 Pydantic parameter models
│   ├── validators.py, cache.py, errors.py, config.py, auth.py, logging.py
│   ├── sources/               ← 8 data source clients
│   ├── tools/                 ← 26 tool implementations (15+ modules)
│   ├── nlp/                   ← AraLegal-BERT + NER
│   └── utils/                 ← Arabic, PDF, date handling
├── tests/                     ← 80%+ coverage target
└── docs/                      ← 7 documentation files
```

### Tool Categories (One Minute)

| Category | Count | Tools | Priority |
|----------|-------|-------|----------|
| **Legislation** | 4 | research_uae_legislation, research_federal_law, research_uae_law_amendment, research_cabinet_resolution | P0 |
| **Dubai Laws** | 3 | research_dubai_law, research_dubai_decree, research_dubai_municipality_regulation | P0 |
| **Court/Cases** | 3 | research_court_decision, research_labor_dispute_decision, research_commercial_contract_precedent | P0 |
| **DIFC/ADGM** | 4 | research_difc_law, research_difc_company, research_adgm_law, research_adgm_registry | P1 |
| **Commercial** | 3 | research_commercial_law, research_commercial_contract, research_uae_trademark_law | P1 |
| **Labor** | 2 | research_uae_labor_law, research_labor_dispute_resolution | P1 |
| **Criminal** | 2 | research_uae_criminal_law, research_criminal_case_decision | P1 |
| **Family** | 1 | research_personal_status_law | P2 |
| **NLP & Compliance** | 4 | research_legal_nlp_classify, research_legal_entity_extract, research_aml_compliance, research_jurisdiction_compare | P2 |
| **TOTAL** | **26** | | |

### Acceptance Criteria (One Page)

Each tool must:
- ✓ Return results within time limit (5-15s depending on complexity)
- ✓ Cache hits < 100ms on second call
- ✓ Return standardized dict with keys: query, language, total_results, results[], execution_time_ms, cached, source_accessed_at
- ✓ Each result includes: id, title_en, title_ar, url, source, law_number, date_published, summary_en, summary_ar, full_text_en, full_text_ar, jurisdiction, status, category, related_laws[], amendments[], enforcement_notes
- ✓ Error handling: fallback to cache if available, else graceful error message
- ✓ Arabic support: full UTF-8 + transliteration fallback
- ✓ Parameter validation: Pydantic v2, strict mode
- ✓ Tested: unit + integration tests, 80%+ coverage

### Data Sources (One Page)

| Source | URL | Auth | Rate Limit | Tool Count |
|--------|-----|------|-----------|-----------|
| UAE Legislation Portal | uaelegislation.gov.ae | No | 200/hr | 3 tools |
| MOJ Database | moj.gov.ae | OAuth2 | 100/hr | 2 tools |
| Dubai Legal Portal | dlp.dubai.gov.ae | No | 200/hr | 3 tools |
| Federal Court | courts.gov.ae | No | 100/hr | 3 tools |
| DIFC Laws & Registry | difc.com | No | 500/hr | 2 tools |
| ADGM Laws & Registry | adgm.com | No | 200/hr | 2 tools |
| Bayanat | bayanat.ae | No | 200/hr | 1 tool |
| AraLegal-BERT | HuggingFace | No (local) | N/A | 2 tools |

### Caching Policy (One Minute)

| Data Type | TTL | Reason |
|-----------|-----|--------|
| Federal/Dubai Laws | 7 days | Change infrequently |
| Cabinet Resolutions | 7 days | Public announcements |
| Court Decisions | 30 days | Historical, final |
| Company Registries | 1 day | Status can change |
| Municipal Regulations | 3 days | Fees/fines update often |
| AML/Compliance Lists | 1 day | Sanction lists daily |
| NLP Classifications | No cache | Deterministic |

### Implementation Timeline (One Minute)

```
Phase 1 (Weeks 1-2): Infrastructure
  └─ Package structure, params validation, cache, validators
  └─ Deliverable: "pip install loom-legal" registers tools

Phase 2 (Weeks 3-5): Data Sources & Tools
  └─ 8 source clients, 20 tools, integration tests
  └─ Deliverable: All tools callable, returning real data

Phase 3 (Weeks 6-8): Advanced Features
  └─ AraLegal-BERT NLP, jurisdiction compare, full docs
  └─ Deliverable: Production-ready, 80%+ coverage, documented
```

### Security Checklist (One Minute)

- [ ] No hardcoded API keys (all from env vars)
- [ ] PII masked by default (NER-based masking)
- [ ] Rate limiting enforced (backoff on 429)
- [ ] URL validation (SSRF prevention)
- [ ] Parameter validation (Pydantic strict mode)
- [ ] Audit logging for all PII access
- [ ] API token auto-refresh before expiry
- [ ] Error messages don't leak sensitive data

---

## KEY ARCHITECTURAL DECISIONS

### 1. Plugin Architecture (Separate Package)
- **Rationale**: Loom core remains domain-agnostic; loom-legal can evolve independently
- **Mechanism**: Entry_points in pyproject.toml + server.py discovery
- **Trade-off**: Slight complexity in registration, but cleaner separation

### 2. Source Client Pattern
- **Rationale**: Centralize rate limiting, caching, retry logic
- **Mechanism**: One client class per major data source (8 clients total)
- **Trade-off**: Extra indirection, but cleaner code reuse

### 3. Hybrid Caching (L1 + L2)
- **Rationale**: Cache raw API responses (L1) + processed results (L2)
- **Mechanism**: Source clients cache raw data; tools cache processed results
- **Trade-off**: Complex cache invalidation, but efficient for shared sources

### 4. Full Arabic Support (UTF-8 + Transliteration)
- **Rationale**: UAE legal data is bilingual; support both modern + legacy clients
- **Mechanism**: All results include title_ar + title_ar_transliterated
- **Trade-off**: 50% larger results, but maximum compatibility

### 5. Graceful Degradation
- **Rationale**: Source unavailable → return cached (stale) data + warning
- **Mechanism**: Fallback chain: API → retry → cache → error
- **Trade-off**: Users might act on stale data, but better UX

### 6. Configurable PII Masking
- **Rationale**: Privacy-safe by default, but power users can opt-in
- **Mechanism**: NER-based masking (default ON), override with include_pii=True
- **Trade-off**: NER adds ~500ms, but logs audit event for compliance

---

## IMPLEMENTATION PRIORITIES

### Must-Have (Phase 1 + Phase 2)
1. Package structure + entry point registration
2. All 10 parameter models + validation
3. 4 data source clients (uae_legislation, dubai_law, mofa, court)
4. 14 core tools (legislation, dubai, court, commercial)
5. Caching infrastructure (L1 + L2)
6. Basic error handling + fallback

### Should-Have (Phase 2 + Phase 3)
7. 4 remaining sources (difc, adgm, bayanat, sharia_finance)
8. 12 remaining tools (labor, criminal, family, finance, NLP)
9. Arabic transliteration + language detection
10. Full test coverage (80%+)

### Nice-To-Have (Phase 3)
11. AraLegal-BERT fine-tuning on 50K legal documents
12. Jurisdiction comparison tool (cross-API synthesis)
13. LLM-based contract analysis
14. Jupyter notebook examples
15. Performance benchmarking

---

## QUALITY GATES

### Before Phase 1 → Phase 2
- [ ] Entry point registration working (can import tools)
- [ ] All 26 parameter models pass validation tests
- [ ] Cache read/write tested (in-memory mock)
- [ ] Error handling for API timeout + rate limit
- [ ] Documentation: API reference, code examples
- [ ] 90%+ coverage on infrastructure code

### Before Phase 2 → Phase 3
- [ ] All 20 core tools returning real data
- [ ] Each tool tested with mocked + live API (if available)
- [ ] Caching verified with real sources (TTL enforcement)
- [ ] Error recovery tested (source unavailable scenarios)
- [ ] Rate limiting respected (no API violations)
- [ ] 80%+ overall coverage
- [ ] Documentation: tools reference, troubleshooting

### Before Release
- [ ] 80%+ test coverage (unit + integration + E2E)
- [ ] Zero security issues (bandit scan, manual review)
- [ ] All 26 tools documented with examples
- [ ] Arabic language support verified (both tools + clients)
- [ ] Performance baselines met (response time targets)
- [ ] Backward compatibility: older Loom versions still work (graceful degradation)

---

## COMMON QUESTIONS

### Q: Can we ship without AraLegal-BERT?
**A**: Yes. Phase 1-2 includes all 22 tools minus NLP (research_legal_nlp_classify, research_legal_entity_extract). Phase 3 adds NLP. Mark as optional dependency.

### Q: What if a government API is unavailable?
**A**: Return cached result (even if stale) + flag `cached_stale=True` + warning timestamp. Better UX than error.

### Q: How do we handle jurisdiction conflicts (e.g., DIFC law vs. UAE federal law)?
**A**: Each result includes explicit `jurisdiction` field. research_jurisdiction_compare() shows side-by-side comparison + legal reasoning for precedence.

### Q: Do all tools need to support Arabic?
**A**: Yes. All results include both title_en + title_ar. Tools can be called with language="en" or language="ar".

### Q: How do we prevent PII leakage from court decisions?
**A**: NER-based masking (default ON). Names → [REDACTED-PERSON-****], IDs → [REDACTED-ID-****]. Override with explicit include_pii=True (logs audit event).

### Q: Can we integrate with existing Loom tools (e.g., research_llm_summarize)?
**A**: Yes. Tools can call other Loom tools for synthesis (e.g., research_commercial_contract calls research_llm_summarize for model clause extraction). Requires careful testing to avoid circular dependencies.

### Q: What if we add new tools after release?
**A**: Plugin architecture allows adding tools without modifying loom-legal core. Create loom-legal-extended package with additional tools, same entry_points mechanism.

---

## SUCCESS METRICS

### Week 8 Deliverables
- ✓ 26 tools fully implemented + tested
- ✓ 8 data source clients working with real APIs
- ✓ 80%+ test coverage maintained
- ✓ Full documentation (7 docs, 100+ pages)
- ✓ Example Jupyter notebooks
- ✓ Performance baselines met (response time <15s, cache hit <100ms)
- ✓ Zero security issues (bandit, manual review)
- ✓ Arabic language support verified (bilingual results)
- ✓ Graceful error handling + fallback tested

### Adoption Targets (Month 1 Post-Release)
- 100+ downloads (pip install loom-legal)
- 50+ GitHub stars
- 10+ community issues (indicating active use)
- 3+ pull requests (community contributions)
- 95%+ uptime (monitored on Hetzner)

---

## NEXT ACTIONS

### Today
1. Share spec with Kimi + DeepSeek
2. Schedule 1:1 kickoffs (30 min each)

### Week 1
1. Kimi/DeepSeek produce design documents
2. Ahmed reviews + populates comparison matrix
3. Reconciliation if needed

### Week 2
1. Phase 1 implementation begins (parallel)
2. Daily standup (15 min, async)
3. PR reviews for infrastructure code

### Week 5
1. Phase 2 merge + integration testing
2. Resolve any API access issues

### Week 8
1. Phase 3 completion
2. Full test suite runs
3. Release candidate build

### Week 9
1. Documentation review + polish
2. Performance benchmarking
3. Security audit
4. v0.1.0 release

---

## FILES DELIVERED

```
/Users/aadel/projects/loom/

LOOM_LEGAL_UNIFIED_SPEC.md              (50 pages, 26 tools, complete specification)
LOOM_LEGAL_ARCHITECTURE_DECISIONS.md    (20 pages, 10 ADRs, rationale)
LOOM_LEGAL_DESIGN_COMPARISON.md         (15 pages, comparison framework)
LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md   (25 pages, code stubs, patterns)
LOOM_LEGAL_SPEC_SUMMARY.md              (5 pages, this file)

Total: ~100 pages (when printed)
```

---

## CONTACT & ESCALATION

- **Questions on spec**: Review LOOM_LEGAL_UNIFIED_SPEC.md (14 sections with detailed examples)
- **Questions on design decisions**: Review LOOM_LEGAL_ARCHITECTURE_DECISIONS.md (10 ADRs with trade-offs)
- **Code questions**: Review LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md (realistic stubs + patterns)
- **Design conflicts**: Use LOOM_LEGAL_DESIGN_COMPARISON.md comparison matrix to flag + resolve

---

## SUCCESS CRITERIA (TL;DR)

**By Week 8, loom-legal v0.1.0 is released if:**

1. ✓ 26 tools implemented, tested (80%+), documented
2. ✓ 8 data sources working (real API calls, rate limiting, error handling)
3. ✓ Caching verified (TTL enforcement, cache hits < 100ms)
4. ✓ Arabic language support complete (bilingual results, NLP models)
5. ✓ Security audit passed (no PII leakage, secure API key management)
6. ✓ Performance targets met (response time < 15s per tool)
7. ✓ Zero critical bugs (all high-severity issues resolved)

**Anything less**: Extend timeline or reduce scope (prioritize P0 tools only).

