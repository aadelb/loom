# AI Safety Tools Implementation Checklist

**For:** Implementation Team, Project Manager  
**Created:** 2026-04-27  
**Target Completion:** Week 8 (2026-06-22)

---

## Phase 1: Foundation (Weeks 1-2)

### Planning & Setup
- [ ] Team kick-off meeting (discuss design, Q&A)
- [ ] Assign lead developer (primary implementer)
- [ ] Assign QA lead (testing coordinator)
- [ ] Create project board (GitHub Projects or Jira)
- [ ] Set up branch naming: `feature/safety-tools-*`

### Code Setup
- [ ] Create `src/loom/tools/safety.py` (empty module)
- [ ] Add docstring + imports section
- [ ] Copy parameter models from `docs/safety-params.py` → `src/loom/params.py`
- [ ] Create test file `tests/test_tools/test_safety.py`
- [ ] Create conftest fixture for mock API (if needed)

### Tool 1: Prompt Injection Test
- [ ] Implement function signature + docstring
- [ ] Implement parameter validation
- [ ] Implement hard-coded JAILBREAK_VECTORS
- [ ] Implement `_detect_jailbreak_success()` helper
- [ ] Implement `_classify_vector_technique()` helper
- [ ] Implement jailbreak mutation generation (via LLM)
- [ ] Implement API testing loop
- [ ] Write 5+ unit tests
- [ ] Write 2+ integration tests
- [ ] Test with mock API endpoint
- [ ] Manual testing with real endpoint (if available)
- [ ] Cost tracking validation
- [ ] Error handling verification
- [ ] Code review (architecture + security)
- [ ] Merge PR

### Tool 2: Model Fingerprint
- [ ] Implement function signature + docstring
- [ ] Implement parameter validation
- [ ] Implement KNOWN_FINGERPRINTS database
- [ ] Implement latency analysis
- [ ] Implement stylometry integration (use existing tool)
- [ ] Implement safety filter fingerprinting
- [ ] Implement model comparison + scoring
- [ ] Write 5+ unit tests
- [ ] Write 2+ integration tests
- [ ] Manual testing with multiple models (if available)
- [ ] Confidence score validation
- [ ] Code review + merge

### Tool 3: Compliance Audit
- [ ] Implement function signature + docstring
- [ ] Implement parameter validation
- [ ] Implement EU_AI_ACT_REQUIREMENTS database (85+ articles)
- [ ] Implement LLM-based gap analysis
- [ ] Implement compliance scoring (0-100)
- [ ] Implement remediation action generation
- [ ] Implement framework validation (at least one checked)
- [ ] Write 5+ unit tests
- [ ] Write 2+ integration tests
- [ ] Manual testing with sample systems
- [ ] Verify requirements completeness (with expert review)
- [ ] Code review + merge

### Phase 1 Validation
- [ ] All 3 tools implemented
- [ ] Parameter models added to params.py
- [ ] 80%+ test coverage for Phase 1 tools
- [ ] No ruff/mypy errors
- [ ] No bandit security issues
- [ ] Register tools in server.py (test them)
- [ ] Journey test passes (all 3 tools)
- [ ] Documentation updated (docstrings complete)
- [ ] Team demo (show working tools)

**Go/No-Go Decision:** Can proceed to Phase 2?

---

## Phase 2: Fairness & Robustness (Weeks 3-4)

### Tool 4: Bias Probe
- [ ] Implement function signature + docstring
- [ ] Implement parameter validation
- [ ] Implement PROTECTED_DEMOGRAPHICS database
- [ ] Implement paired prompt generation (via LLM)
- [ ] Implement concurrent API testing
- [ ] Implement bias score computation (statistical test)
- [ ] Implement worst-case example identification
- [ ] Implement risk summary generation
- [ ] Write 5+ unit tests (including bias math validation)
- [ ] Write 2+ integration tests
- [ ] Manual bias testing with sample system
- [ ] **Manual validation by domain expert** (check for false positives)
- [ ] Verify paired prompts are truly equivalent
- [ ] Code review + merge

### Tool 5: Safety Filter Map
- [ ] Implement function signature + docstring
- [ ] Implement parameter validation
- [ ] Implement SEVERITY_TEMPLATES database
- [ ] Implement binary search algorithm
- [ ] Implement consistency testing (repeat queries)
- [ ] Implement edge case detection (synonyms, encoding bypasses)
- [ ] Implement boundary determination + confidence scoring
- [ ] Write 5+ unit tests
- [ ] Write 2+ integration tests
- [ ] Manual testing (verify binary search converges)
- [ ] Test with multiple topics (violence, sexual, etc.)
- [ ] Code review + merge

### Tool 8: Adversarial Robustness
- [ ] Implement function signature + docstring
- [ ] Implement parameter validation
- [ ] Implement PERTURBATION_LIBRARY (typos, unicode, homoglyphs, etc.)
- [ ] Implement perturbation generation functions
- [ ] Implement parallel API testing
- [ ] Implement robustness scoring
- [ ] Implement attack vector ranking
- [ ] Write 5+ unit tests (verify perturbations work)
- [ ] Write 2+ integration tests
- [ ] Manual testing (verify typos are actual typos)
- [ ] Code review + merge

### Phase 2 Validation
- [ ] Tools 4, 5, 8 implemented
- [ ] 80%+ test coverage for Phase 2 tools
- [ ] Manual expert review of bias results (no false positives)
- [ ] No ruff/mypy/bandit errors
- [ ] Register tools in server.py
- [ ] Journey test includes Phase 2 tools
- [ ] Team demo

**Go/No-Go Decision:** Can proceed to Phase 3?

---

## Phase 3: Privacy & Accuracy (Week 5)

### Tool 6: Memorization Test
- [ ] Implement function signature + docstring
- [ ] Implement parameter validation
- [ ] Implement CANARIES database (100+ synthetic phrases)
- [ ] Implement canary extraction template generation
- [ ] Implement fuzzy matching (Levenshtein distance)
- [ ] Implement confidence scoring
- [ ] Implement false-positive detection (random string matching)
- [ ] Write 5+ unit tests
- [ ] Write 2+ integration tests
- [ ] Manual testing (verify canaries are properly detected)
- [ ] Verify false positive rate < 1%
- [ ] Code review + merge

### Tool 7: Hallucination Benchmark
- [ ] Implement function signature + docstring
- [ ] Implement parameter validation
- [ ] Implement FACTUAL_QUESTIONS database (100+ Q&A pairs)
- [ ] Implement answer extraction (via LLM)
- [ ] Implement fuzzy matching for answers
- [ ] Implement hallucination detection
- [ ] Implement confidence calibration analysis
- [ ] Implement worst-domain identification
- [ ] Write 5+ unit tests (including answer parsing)
- [ ] Write 2+ integration tests
- [ ] Manual validation of questions (verify answers are unambiguous)
- [ ] Test with sample LLM
- [ ] **Expert review of question set** (no ambiguous answers)
- [ ] Code review + merge

### Phase 3 Validation
- [ ] Tools 6, 7 implemented
- [ ] 80%+ test coverage for Phase 3 tools
- [ ] Manual expert review of hallucination questions
- [ ] No ruff/mypy/bandit errors
- [ ] Register tools in server.py
- [ ] Journey test includes Phase 3 tools
- [ ] Team demo

**Go/No-Go Decision:** Can proceed to Phase 4?

---

## Phase 4: Monitoring & Integration (Week 6)

### Tool 9: Regulatory Monitor
- [ ] Implement function signature + docstring
- [ ] Implement parameter validation
- [ ] Implement REGULATORY_SOURCES database (5+ jurisdictions)
- [ ] Implement bulk scraping (via spider)
- [ ] Implement HTML parsing (via markdown)
- [ ] Implement LLM-based summarization
- [ ] Implement relevance scoring
- [ ] Implement deadline extraction
- [ ] Implement change detection
- [ ] Implement caching (30-day TTL)
- [ ] Write 5+ unit tests
- [ ] Write 2+ integration tests (use recorded HTML)
- [ ] **Integration test with live sources** (if prod data allowed)
- [ ] Verify 0 false positives in jurisdiction classification
- [ ] Code review + merge

### Tool 10: AI Incident Tracker
- [ ] Implement function signature + docstring
- [ ] Implement parameter validation
- [ ] Implement INCIDENT_SOURCES database (6+ sources)
- [ ] Implement bulk incident scraping
- [ ] Implement incident parsing + deduplication
- [ ] Implement category classification (via LLM)
- [ ] Implement severity classification
- [ ] Implement trend analysis
- [ ] Implement caching (30-day TTL)
- [ ] Write 5+ unit tests
- [ ] Write 2+ integration tests (use recorded responses)
- [ ] **Integration test with live AIAAIC API** (if available)
- [ ] Verify incident dedupe works (no duplicates)
- [ ] Code review + merge

### Server Integration
- [ ] Register all 10 tools in `server.py` (_register_tools function)
- [ ] Test MCP schema includes all tools
- [ ] Test each tool is callable via MCP interface
- [ ] Update server startup logging (include safety tools count)
- [ ] Verify rate limiting applies to all tools

### Phase 4 Validation
- [ ] Tools 9, 10 implemented
- [ ] All 10 tools registered in server
- [ ] 80%+ test coverage for Phase 4 tools
- [ ] No ruff/mypy/bandit errors
- [ ] Journey test includes all 10 tools
- [ ] Team demo (all tools working)

**Go/No-Go Decision:** Can proceed to Phase 5?

---

## Phase 5: Testing & Documentation (Week 7)

### Comprehensive Testing
- [ ] Run full test suite: `pytest tests/test_tools/test_safety.py`
- [ ] Achieve 80%+ coverage: `pytest --cov=src/loom/tools/safety`
- [ ] Zero failing tests
- [ ] Lint clean: `ruff check src/loom/tools/safety.py`
- [ ] Format clean: `ruff format src/loom/tools/safety.py`
- [ ] Type check clean: `mypy src/loom/tools/safety.py`
- [ ] Security scan clean: `bandit src/loom/tools/safety.py`

### Documentation Updates
- [ ] Update `docs/tools-reference.md` (add AI Safety section)
  - [ ] Tool overview table
  - [ ] Tool 1-10 detailed sections
  - [ ] Parameters documented
  - [ ] Return values documented
  - [ ] Code examples for each tool
  - [ ] Cost estimates
  - [ ] Timeout recommendations
- [ ] Create `docs/compliance-testing-guide.md` (from quick-start.md)
  - [ ] Multi-tool workflows
  - [ ] Regulatory monitor setup
  - [ ] Incident tracker setup
  - [ ] Cost management guide
- [ ] Ensure all functions have docstrings
- [ ] Ensure all parameters documented
- [ ] Ensure all return values documented

### Journey Tests
- [ ] Create workflow test: Compliance audit → Bias probe → Remediation
- [ ] Create workflow test: Regulatory monitor → Incident tracker
- [ ] Create workflow test: Prompt injection test → Model fingerprint
- [ ] Add to `tests/journey_e2e.py`
- [ ] All journey tests pass

### Integration Tests
- [ ] Test cost tracking (LLM budget enforced)
- [ ] Test timeout handling (API timeouts caught)
- [ ] Test error handling (all errors return dict, no exceptions raised)
- [ ] Test SSRF protection (invalid URLs rejected)
- [ ] Test cache behavior (results cached, TTL respected)
- [ ] Test rate limiting (parallel requests throttled)

### Code Review & Sign-Off
- [ ] Security review (no hardcoded secrets, SSRF safe, etc.)
- [ ] Architecture review (consistent with ADR-005)
- [ ] Code quality review (no dead code, proper error handling)
- [ ] Performance review (no runaway loops, proper async)
- [ ] Documentation review (all documented, examples clear)
- [ ] All review comments addressed

### Phase 5 Validation
- [ ] 80%+ test coverage (full suite)
- [ ] 0 failing tests
- [ ] 0 lint/type/security issues
- [ ] Documentation complete
- [ ] Journey tests passing
- [ ] Code review approved
- [ ] Ready for production

**Go/No-Go Decision:** Production release?

---

## Post-Implementation

### Week 8: Release & Documentation
- [ ] Merge all PRs to main branch
- [ ] Tag release (v1.0)
- [ ] Deploy to Hetzner (if applicable)
- [ ] Create release notes
- [ ] Announce to researchers
- [ ] Schedule training session

### Week 9+: Feedback & Iteration
- [ ] Monitor tool usage (via logs)
- [ ] Collect user feedback
- [ ] Track bug reports
- [ ] Plan next iteration (enhancements)
- [ ] Publish case study / research findings

---

## Metrics to Track

### Quality Metrics
| Metric | Target | Current |
|--------|--------|---------|
| Test Coverage | 80%+ | ___ |
| Failing Tests | 0 | ___ |
| Lint Errors | 0 | ___ |
| Type Errors | 0 | ___ |
| Security Issues | 0 | ___ |

### Performance Metrics
| Tool | Target | Current |
|------|--------|---------|
| Prompt Injection | < 10 min | ___ |
| Bias Probe | < 5 min | ___ |
| Compliance Audit | < 5 min | ___ |
| Regulatory Monitor | < 5 min | ___ |
| Incident Tracker | < 3 min | ___ |

### Cost Metrics
| Tool | Target | Current |
|------|--------|---------|
| Prompt Injection | < $0.20 | ___ |
| Bias Probe | < $0.30 | ___ |
| Compliance Audit | < $0.20 | ___ |
| Memorization Test | < $0.50 | ___ |

---

## Risk Management

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| LLM API costs exceed budget | Medium | High | Enforce max_cost_usd, monitor daily costs |
| Bias probe false positives | Medium | High | Expert review of results, repeat tests |
| Hallucination benchmark ambiguous Q's | Medium | Medium | Expert validation of question set |
| Regulatory monitor scraping breaks | Low | Medium | Cache results, fallback to archive.org |
| SSRF vulnerability | Low | Critical | URL validation, penetration testing |
| Test coverage < 80% | Low | Medium | Early testing, TDD for each tool |

---

## Sign-Off

### Phase 1 (Week 2)
- [ ] Lead Developer: _______________________ Date: _______
- [ ] QA Lead: _______________________ Date: _______
- [ ] Architecture Review: _______________________ Date: _______

### Phase 2 (Week 4)
- [ ] Lead Developer: _______________________ Date: _______
- [ ] QA Lead: _______________________ Date: _______

### Phase 3 (Week 5)
- [ ] Lead Developer: _______________________ Date: _______
- [ ] QA Lead: _______________________ Date: _______

### Phase 4 (Week 6)
- [ ] Lead Developer: _______________________ Date: _______
- [ ] QA Lead: _______________________ Date: _______

### Phase 5 (Week 7)
- [ ] Lead Developer: _______________________ Date: _______
- [ ] QA Lead: _______________________ Date: _______
- [ ] Security Review: _______________________ Date: _______
- [ ] Project Manager: _______________________ Date: _______

### Final Sign-Off (Week 8)
- [ ] Release Manager: _______________________ Date: _______

---

## Communication Checklist

- [ ] Weekly standup: Monday 10 AM
- [ ] Phase completion demos: End of each phase
- [ ] Blocker escalation: Daily if needed
- [ ] Status updates: Weekly email to stakeholders
- [ ] Risk review: Mid-phase (weeks 2, 4, 5, 6)

---

## Key Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| Lead Developer | [Name] | [Email] | [Phone] |
| QA Lead | [Name] | [Email] | [Phone] |
| Architect | Software Architect Agent | - | - |
| Research Lead | Ahmed Adel Bakr Alderai | ahmed@alderai.uk | - |
| Project Manager | [Name] | [Email] | [Phone] |

---

**Document Version:** 1.0  
**Status:** Ready for Planning  
**Last Updated:** 2026-04-27

**To Use:** Print this document, fill in names/dates as you progress through each phase.
