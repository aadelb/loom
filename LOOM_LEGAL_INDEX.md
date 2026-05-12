# Loom-Legal: Complete Specification Index

**Status**: Complete unified specification (all 5 documents)  
**Date**: 2026-05-07  
**Audience**: Kimi, DeepSeek, Claude (code review), Ahmed (oversight)  
**Total Content**: ~100 pages when printed  

---

## DOCUMENT OVERVIEW

### 1. LOOM_LEGAL_UNIFIED_SPEC.md (50 pages)
**Start here for complete understanding of the system.**

| Section | Content | Pages |
|---------|---------|-------|
| 1. Executive Summary | Overview, design principles | 1 |
| 2. Package Structure | Directory layout, pyproject.toml, entry_points | 3 |
| 3. Plugin Discovery | How Loom finds + registers loom-legal tools | 2 |
| 4. Tool Specifications | Complete signatures for all 26 tools (alphabetically organized) | 18 |
| 5. Data Sources | Matrix of 8 sources (URL, auth, rate limit, API method) | 1 |
| 6. Caching Strategy | Architecture, TTL policy, eviction, implementation | 2 |
| 7. Arabic Language | UTF-8, transliteration, date conversion, NLP | 2 |
| 8. Parameter Validation | Pydantic v2 models, examples | 2 |
| 9. Error Handling | Exception hierarchy, retry logic, fallback chain | 2 |
| 10. Implementation Roadmap | Phase 1/2/3, deliverables, acceptance criteria | 2 |
| 11. Dependencies | Core + optional (NLP), versions | 1 |
| 12. Security | API keys, PII masking, rate limiting, validation | 1 |
| 13. Test Strategy | Unit/integration/E2E, coverage target, execution | 1 |
| 14. Acceptance Criteria | Summary table for all 26 tools | 1 |

**Use this for**: Implementation blueprint, tool specifications, data flow understanding

---

### 2. LOOM_LEGAL_ARCHITECTURE_DECISIONS.md (20 pages)
**Read after unified spec to understand WHY decisions were made.**

| Section | Content | Pages |
|---------|---------|-------|
| ADR-001 | Plugin Package vs. Core Integration | 1 |
| ADR-002 | Data Source Architecture (Clients vs. Direct HTTP) | 1 |
| ADR-003 | Caching Strategy (Per-Tool vs. Per-Source) | 1 |
| ADR-004 | Arabic Language Support (UTF-8 vs. Transliteration) | 1 |
| ADR-005 | NLP Model Strategy (AraLegal-BERT vs. Off-the-Shelf) | 1 |
| ADR-006 | Jurisdiction Precedence & Conflict Resolution | 1 |
| ADR-007 | PII Handling & Privacy | 1 |
| ADR-008 | Rate Limiting & Quota Management | 1 |
| ADR-009 | Tool Wrapper Pattern (MCP vs. Direct) | 1 |
| ADR-010 | Error Handling & Graceful Degradation | 1 |
| DECISION MATRIX | All decisions at a glance (trade-offs, risks) | 1 |
| DESIGN PATTERNS | 4 key patterns (source client, repository, fallback chain, parameter object) | 2 |
| IMPLEMENTATION CHECKLIST | Phase 1/2/3 tasks for Kimi/DeepSeek | 3 |

**Use this for**: Understanding design rationale, risk mitigation, implementation decisions

---

### 3. LOOM_LEGAL_DESIGN_COMPARISON.md (15 pages)
**Use this to compare Kimi + DeepSeek designs against unified spec.**

| Section | Content | Pages |
|---------|---------|-------|
| COMPARISON MATRIX | 13 comparison tables (architecture, structure, tools, sources, caching, params, errors, Arabic, phases, deps, tests, security, docs) | 10 |
| RESOLUTION CHECKLIST | High/medium/low priority conflicts + sign-off criteria | 3 |
| NOTES FOR REVIEWERS | Pass/flag/escalate decision tree | 1 |
| NEXT STEPS | Timeline for reconciliation (day-by-day) | 1 |

**Use this for**: Reconciling Kimi/DeepSeek designs, flagging conflicts, ensuring alignment

---

### 4. LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md (25 pages)
**Reference during implementation—code stubs for every major component.**

| Section | Content | Pages |
|---------|---------|-------|
| 1. pyproject.toml | Complete Poetry configuration with entry_points | 2 |
| 2. Entry Point Registration | loom_legal/server.py + modified loom/server.py | 3 |
| 3. Parameter Models | UAELegislationParams, CourtDecisionParams, NLPClassifyParams examples | 3 |
| 4. Source Client Pattern | base.py (RateLimiter, SourceClient) + uae_legislation.py example | 4 |
| 5. Tool Implementation | research_uae_legislation + _enhance_results pattern | 2 |
| 6. Test Examples | Unit/integration/live test patterns for legislation tool | 3 |
| 7. Integration with Loom | Modified server.py entry + third-party plugin loading | 2 |
| 8. Acceptance Test Template | Complete test for acceptance criteria validation | 1 |

**Use this for**: Copy/paste code stubs, understand patterns, implement faster

---

### 5. LOOM_LEGAL_SPEC_SUMMARY.md (5 pages)
**Quick reference—read this when you need quick answers.**

| Section | Content | Pages |
|---------|---------|-------|
| Document Roadmap | When to read each document | 1 |
| Quick Reference | Package structure, tool categories, acceptance criteria | 1 |
| Quick Acceptance | Tool requirements checklist | 1 |
| Data Sources | Summary table | 1 |
| Implementation Timeline | Phase 1/2/3 at a glance | 1 |
| Key Decisions | Summary of 6 major decisions | 1 |
| Common Questions | 8 FAQs with answers | 1 |
| Success Metrics | Week 8 deliverables + adoption targets | 1 |

**Use this for**: Quick lookups, status updates, 10-minute briefings

---

## READING GUIDE BY ROLE

### For Kimi (Implementation)
1. **Start**: LOOM_LEGAL_SPEC_SUMMARY.md (5 min overview)
2. **Then**: LOOM_LEGAL_UNIFIED_SPEC.md sections 1-3, 8 (30 min for plugin architecture + params)
3. **Deep Dive**: LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md (copy code stubs)
4. **Reference**: LOOM_LEGAL_UNIFIED_SPEC.md section 4 (tool signatures) during coding
5. **Understand Why**: LOOM_LEGAL_ARCHITECTURE_DECISIONS.md ADR-001, ADR-002, ADR-009 (why plugin pattern, source clients, tool wrappers)

**Time**: 2-3 hours total

---

### For DeepSeek (Implementation)
1. **Start**: LOOM_LEGAL_SPEC_SUMMARY.md (5 min)
2. **Then**: LOOM_LEGAL_UNIFIED_SPEC.md sections 5-7 (data sources, caching, Arabic)
3. **Deep Dive**: LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md sections 4-6 (source clients, tool implementation, tests)
4. **Reference**: LOOM_LEGAL_UNIFIED_SPEC.md section 4 (specific tool you're coding)
5. **Understand Why**: LOOM_LEGAL_ARCHITECTURE_DECISIONS.md ADR-003, ADR-004, ADR-005, ADR-007, ADR-008

**Time**: 2-3 hours total

---

### For Claude (Code Review)
1. **Start**: LOOM_LEGAL_SPEC_SUMMARY.md (5 min)
2. **Then**: LOOM_LEGAL_UNIFIED_SPEC.md sections 1-4, 12-13 (high-level architecture, security, tests)
3. **Reference During Review**: LOOM_LEGAL_ARCHITECTURE_DECISIONS.md (verify decisions were followed)
4. **Flag Issues**: Use LOOM_LEGAL_UNIFIED_SPEC.md acceptance criteria (section 14) to verify each tool
5. **Understand Why**: All ADRs (verify assumptions hold)

**Time**: 1-2 hours total, then referenced during review

---

### For Ahmed (Oversight)
1. **Start**: LOOM_LEGAL_SPEC_SUMMARY.md (10 min)
2. **Then**: LOOM_LEGAL_ARCHITECTURE_DECISIONS.md (understand all decisions)
3. **Deep Dive**: LOOM_LEGAL_DESIGN_COMPARISON.md (when Kimi/DeepSeek designs arrive)
4. **Reference**: LOOM_LEGAL_UNIFIED_SPEC.md (look up specifics as needed)
5. **Monitor**: Use LOOM_LEGAL_SPEC_SUMMARY.md section "Quality Gates" to track progress

**Time**: 2 hours initially, then 30 min/week during implementation

---

## KEY METRICS TO TRACK

### Phase 1 (Weeks 1-2)
- [ ] Entry point registration working
- [ ] 26 parameter models tested (90%+ coverage)
- [ ] Cache infrastructure operational
- [ ] Error handling framework in place

### Phase 2 (Weeks 3-5)
- [ ] 8 source clients implemented
- [ ] 20 core tools returning real data
- [ ] Each tool tested (unit + mocked integration)
- [ ] 80%+ overall coverage
- [ ] Rate limiting verified

### Phase 3 (Weeks 6-8)
- [ ] 6 remaining tools completed (NLP, compliance, jurisdiction)
- [ ] Full documentation written
- [ ] Live API tests passing
- [ ] Security audit completed
- [ ] Performance benchmarks met (<15s per tool, <100ms cache hit)

---

## QUICK LOOKUP REFERENCE

### Tool Specifications
**Find a specific tool signature**: LOOM_LEGAL_UNIFIED_SPEC.md section 4 (organized by category + alphabetically)

### Data Source Details
**How to access a government API**: LOOM_LEGAL_UNIFIED_SPEC.md section 5 (matrix) + section 3 (discovery mechanism)

### Caching Behavior
**When does cache expire?**: LOOM_LEGAL_UNIFIED_SPEC.md section 6 (TTL policy table)

### Arabic Support
**How do we handle Arabic text?**: LOOM_LEGAL_UNIFIED_SPEC.md section 7 + LOOM_LEGAL_ARCHITECTURE_DECISIONS.md ADR-004

### Error Handling
**What happens if source API is down?**: LOOM_LEGAL_UNIFIED_SPEC.md section 9 + LOOM_LEGAL_ARCHITECTURE_DECISIONS.md ADR-010

### Security
**How do we prevent PII leakage?**: LOOM_LEGAL_UNIFIED_SPEC.md section 12 + LOOM_LEGAL_ARCHITECTURE_DECISIONS.md ADR-007

### Implementation Checklist
**What do I need to do in Phase 1?**: LOOM_LEGAL_ARCHITECTURE_DECISIONS.md "Implementation Checklist"

### Code Examples
**Show me how to implement a tool**: LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md section 5

### Common Questions
**I have a question about X**: LOOM_LEGAL_SPEC_SUMMARY.md "Common Questions"

---

## VERSION HISTORY

| Version | Date | Status | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-05-07 | Draft | Initial unified specification (5 documents, 100 pages) |
| 0.2.0 | TBD | Pending Reconciliation | After Kimi/DeepSeek designs reviewed |
| 1.0.0 | TBD | Pending Implementation | After Phase 1 complete + all gates passed |

---

## HOW TO USE THESE DOCUMENTS

### Scenario 1: "I need to implement a tool"
1. Read tool signature from LOOM_LEGAL_UNIFIED_SPEC.md section 4
2. Copy pattern from LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md section 5
3. Implement following the pattern
4. Test using template from LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md section 8

### Scenario 2: "I need to add a data source"
1. Review existing source client from LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md section 4
2. Understand caching from LOOM_LEGAL_UNIFIED_SPEC.md section 6
3. Implement following SourceClient pattern
4. Register rate limiter from data source matrix (LOOM_LEGAL_UNIFIED_SPEC.md section 5)

### Scenario 3: "I found a design conflict between Kimi + DeepSeek"
1. Document the conflict in LOOM_LEGAL_DESIGN_COMPARISON.md comparison matrix
2. Review LOOM_LEGAL_ARCHITECTURE_DECISIONS.md for relevant ADR (check "Consequences" section)
3. If ADR supports one design over other, note it
4. If ambiguous, escalate to Ahmed with trade-off analysis

### Scenario 4: "Code review—is this tool correct?"
1. Check tool signature against LOOM_LEGAL_UNIFIED_SPEC.md section 4
2. Verify parameters match LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md
3. Validate error handling against section 9
4. Confirm caching against section 6 + section 13 (test strategy)
5. Compare against acceptance criteria (section 14)

### Scenario 5: "Performance issue—why is this tool slow?"
1. Check response time target in LOOM_LEGAL_UNIFIED_SPEC.md section 14 (acceptance criteria table)
2. Check data source rate limit in section 5 (might be waiting for rate limit token)
3. Review error handling chain in section 9 (might be retrying on failure)
4. Check cache TTL in section 6 (might have expired)
5. Profile code + file performance issue

---

## SUCCESS CRITERIA (TL;DR)

By end of Week 8 (Phase 3 complete):

**Implementation**:
- ✓ 26 tools implemented, all 80%+ test coverage
- ✓ 8 data sources operational with real APIs
- ✓ Plugin architecture working (pip install registers tools)
- ✓ All acceptance criteria met (response time, cache behavior, error handling)

**Quality**:
- ✓ Zero critical security issues (PII, API keys, SSRF)
- ✓ Full documentation (7 docs, tools reference, troubleshooting)
- ✓ Performance baselines met (<15s per tool, <100ms cache hits)
- ✓ Arabic language support verified (bilingual results for all tools)

**Maintainability**:
- ✓ Code follows patterns from LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md
- ✓ Tests match test strategy from section 13
- ✓ Architecture follows ADRs from LOOM_LEGAL_ARCHITECTURE_DECISIONS.md
- ✓ All decisions documented with rationale

---

## CONTACT

**Questions? Check this table first:**

| Question Type | Document | Section |
|---------------|----------|---------|
| "What are all the tools?" | LOOM_LEGAL_UNIFIED_SPEC.md | 4 |
| "How do I implement a tool?" | LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md | 5 |
| "Why plugin architecture?" | LOOM_LEGAL_ARCHITECTURE_DECISIONS.md | ADR-001 |
| "How does caching work?" | LOOM_LEGAL_UNIFIED_SPEC.md | 6 |
| "What's the timeline?" | LOOM_LEGAL_SPEC_SUMMARY.md | Implementation Timeline |
| "What's the answer to my question?" | LOOM_LEGAL_SPEC_SUMMARY.md | Common Questions |
| "How do I verify my implementation?" | LOOM_LEGAL_UNIFIED_SPEC.md | 14 |

**If not found**: File issue with question + relevant document reference.

---

## FINAL CHECKLIST

Before starting implementation, confirm:

- [ ] Read LOOM_LEGAL_SPEC_SUMMARY.md (5 min)
- [ ] Read LOOM_LEGAL_UNIFIED_SPEC.md sections 1-3 (architecture, plugin discovery)
- [ ] Understand entry_point mechanism from LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md section 2
- [ ] Copy code stubs from LOOM_LEGAL_IMPLEMENTATION_EXAMPLES.md (Python files)
- [ ] Understand tool pattern from section 5
- [ ] Review error handling from LOOM_LEGAL_UNIFIED_SPEC.md section 9
- [ ] Confirm caching strategy from section 6
- [ ] Know acceptance criteria from section 14 (your quality gate)
- [ ] Understand security requirements from section 12

**Ready to code?** Start with Phase 1 tasks from LOOM_LEGAL_ARCHITECTURE_DECISIONS.md "Implementation Checklist".

