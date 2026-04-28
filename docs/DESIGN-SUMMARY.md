# AI Safety Red-Teaming Tools — Design Summary

**Project:** UMMRO EU AI Act Compliance Testing  
**Author:** Software Architect Agent  
**Date:** 2026-04-27  
**Status:** Design Complete → Ready for Implementation

---

## Executive Summary

Designed 10 new AI Safety red-teaming tools for Loom MCP server, enabling systematic evaluation of LLM safety, fairness, accuracy, and regulatory compliance. These tools support Ahmed Adel Bakr Alderai's PhD research in AI Safety / Compliance Engineering (authorized EU AI Act Article 15 testing).

**Key Deliverables:**
1. Comprehensive tool specifications (10 tools, ~600 lines each)
2. Architecture decision record (ADR-005)
3. Parameter validation models (Pydantic v2)
4. System integration diagrams (Mermaid)
5. Researcher quick-start guide
6. Implementation roadmap (7-week plan)

---

## The 10 Tools

### 1. **research_prompt_injection_test**
- **Purpose:** Generate & test adversarial jailbreak patterns
- **Use Case:** Red-team LLM, find prompt injection vulnerabilities
- **Inputs:** target_url, num_mutations (1-100), max_cost_usd
- **Outputs:** bypass_rate, vulnerability list, risk_score (0-100), recommendations
- **Complexity:** HIGH | **Cost:** $0.18 | **Time:** 5-10 min
- **Key Dependency:** research_llm_chat (mutation generation)

### 2. **research_model_fingerprint**
- **Purpose:** Identify black-box model via response patterns
- **Use Case:** Determine which LLM vendor is behind unknown API
- **Inputs:** target_url, num_queries (1-100), analyze_latency, analyze_style
- **Outputs:** inferred_model, confidence (0-1), fingerprints, candidate_models
- **Complexity:** HIGH | **Cost:** $0.05 | **Time:** 5-10 min
- **Key Dependency:** research_stylometry (style analysis)

### 3. **research_compliance_audit**
- **Purpose:** Automated EU AI Act + frameworks compliance checking
- **Use Case:** Pre-deployment audit, regulatory sign-off
- **Inputs:** system_description, eu_ai_act, iso_iec_42001, nist_ai_rmf
- **Outputs:** compliance_gaps (with remediation), score (0-100), required_actions
- **Complexity:** MEDIUM | **Cost:** $0.14 | **Time:** 2-5 min
- **Key Dependency:** research_llm_chat (gap analysis)

### 4. **research_bias_probe**
- **Purpose:** Systematic demographic bias measurement
- **Use Case:** Fairness audit before release
- **Inputs:** target_url, demographics, test_domains, sample_size
- **Outputs:** bias_scores by demographic × domain, worst_case_examples, risk_summary
- **Complexity:** MEDIUM | **Cost:** $0.30 | **Time:** 3-5 min
- **Key Dependency:** research_llm_chat (paired prompt generation)

### 5. **research_safety_filter_map**
- **Purpose:** Binary search for exact safety filter boundaries
- **Use Case:** Identify filter inconsistencies, discover edge cases
- **Inputs:** target_url, topic (violence/sexual/illegal/etc), severity_range, num_iterations
- **Outputs:** filter_boundary (exact threshold), edge_cases, inconsistencies
- **Complexity:** MEDIUM | **Cost:** $0.10 | **Time:** 10-20 min
- **Key Dependency:** research_fetch (binary search via API)

### 6. **research_memorization_test**
- **Purpose:** Test if model memorized / can leak training data
- **Use Case:** Privacy audit, detect unintended data extraction
- **Inputs:** target_url, num_canaries (10-500), extraction_templates
- **Outputs:** memorization_rate (%), leaked_data samples, risk_level
- **Complexity:** HIGH | **Cost:** $0.48 | **Time:** 5-10 min
- **Key Dependency:** research_llm_chat (confidence scoring)

### 7. **research_hallucination_benchmark**
- **Purpose:** Automated fact-checking accuracy measurement
- **Use Case:** Measure model truthfulness before release
- **Inputs:** target_url, num_questions (5-200), question_domains
- **Outputs:** hallucination_rate (%), calibration analysis, worst_domains
- **Complexity:** MEDIUM | **Cost:** $0.15 | **Time:** 2-3 min
- **Key Dependency:** research_llm_chat + research_llm_embed (parsing, similarity)

### 8. **research_adversarial_robustness**
- **Purpose:** Test text perturbation attacks (typos, unicode, homoglyphs)
- **Use Case:** Security hardening, verify model input robustness
- **Inputs:** target_url, test_prompts, perturbation_types, num_perturbations
- **Outputs:** robustness_score (0-100), results_by_perturbation, attack_vectors
- **Complexity:** MEDIUM | **Cost:** $0.01 | **Time:** 2-3 min
- **Key Dependency:** None (pure perturbation library)

### 9. **research_regulatory_monitor**
- **Purpose:** Track AI regulation changes across 8 jurisdictions
- **Use Case:** Compliance monitoring, regulatory roadmap planning
- **Inputs:** jurisdictions, keywords, lookback_days (1-365)
- **Outputs:** regulation updates, impact areas, compliance_deadlines, roadmap
- **Complexity:** MEDIUM | **Cost:** $0.05 | **Time:** 3-5 min
- **Key Dependency:** research_spider + research_markdown (scraping)

### 10. **research_ai_incident_tracker**
- **Purpose:** Monitor & catalog real-world AI failures
- **Use Case:** Operational risk assessment, learn from incidents
- **Inputs:** lookback_days, severity_threshold, incident_categories
- **Outputs:** incident database, trend_analysis, severity_distribution
- **Complexity:** MEDIUM | **Cost:** $0.12 | **Time:** 2-3 min
- **Key Dependency:** research_spider + research_llm_extract (scraping, classification)

---

## Architecture Highlights

### Tool Composition Strategy

All 10 tools build on existing Loom infrastructure:

```
Core Tools (50 existing)
├── research_fetch (HTTP/Stealthy/Dynamic)
├── research_spider (Concurrent fetch)
├── research_markdown (HTML → markdown)
├── research_search (Multi-provider)
└── LLM Tools (8 providers)

↓ Used by ↓

Safety Tools (10 new)
├── research_prompt_injection_test ← fetch, llm_chat, multilingual
├── research_model_fingerprint ← fetch, stylometry
├── research_compliance_audit ← llm_chat, llm_extract
├── research_bias_probe ← fetch, llm_chat
├── research_safety_filter_map ← fetch
├── research_memorization_test ← fetch, llm_chat
├── research_hallucination_benchmark ← fetch, llm_chat, llm_embed
├── research_adversarial_robustness ← fetch
├── research_regulatory_monitor ← spider, markdown, llm_chat
└── research_ai_incident_tracker ← spider, markdown, llm_extract

↓ Supported by ↓

Infrastructure
├── Config (hard-coded knowledge bases)
├── Cache (30-day results retention)
├── CostTracker (LLM budget enforcement)
└── Audit Logger
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Hard-coded knowledge** | Compliance frameworks stable, ensures audit trail |
| **Async-first** | Consistent with Loom's FastMCP, enables parallelization |
| **Pydantic v2 validation** | Type safety, API contract clarity, early error detection |
| **Per-tool cost limits** | Protects against runaway LLM bills during testing |
| **Reuse existing tools** | Minimizes code duplication, maximizes maintainability |
| **SSRF-safe URLs** | Prevents testing against private networks |
| **Consistent output schema** | Enables downstream automation (dashboards, alerts) |
| **80%+ test coverage** | Quality bar for compliance-critical tools |

---

## Files Created

### Documentation (4 files)

1. **`docs/ai-safety-tools-design.md`** (8000+ words)
   - Complete specification for all 10 tools
   - Function signatures, parameters, return values
   - Implementation approach, hard-coded examples
   - Testing strategy, security considerations
   - Future enhancements, references

2. **`docs/ADR-005-AI-Safety-Red-Teaming-Tools.md`** (2000+ words)
   - Architecture Decision Record (formal format)
   - Context, decision rationale, consequences
   - Positive impacts, negative impacts, risks
   - Alternatives considered, implementation roadmap
   - Success criteria

3. **`docs/safety-tools-architecture.md`** (3000+ words)
   - System overview diagram (Mermaid)
   - Data flow example (Mermaid sequence)
   - Tool dependency graph
   - Execution flow state machine
   - Module organization
   - Scalability & performance analysis
   - Security considerations
   - Integration points

4. **`docs/compliance-testing-quick-start.md`** (3000+ words)
   - Researcher-friendly quick reference
   - Tool overview table (purpose, time, cost)
   - 4 common workflows with code examples
   - Cost management guidance
   - Common pitfalls & prevention
   - FAQ

### Implementation Templates (1 file)

5. **`docs/safety-params.py`** (600+ lines)
   - Pydantic v2 parameter models for all 10 tools
   - Field validators (URL, numeric bounds, enums)
   - `extra="forbid"` + `strict=True` configuration
   - Ready to copy into `src/loom/params.py`

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Create `src/loom/tools/safety.py` module
- [ ] Implement Tools 1, 2, 3 (Prompt Injection, Model Fingerprint, Compliance Audit)
- [ ] Add parameter models to `src/loom/params.py`
- [ ] Unit tests + integration tests

**Deliverables:** Prompt injection testing, model identification, compliance checking

### Phase 2: Fairness & Robustness (Weeks 3-4)
- [ ] Implement Tools 4, 5, 8 (Bias Probe, Safety Filter Map, Adversarial Robustness)
- [ ] Unit + integration tests
- [ ] Bias score validation (manual review)

**Deliverables:** Fairness auditing, filter mapping, robustness evaluation

### Phase 3: Privacy & Accuracy (Week 5)
- [ ] Implement Tools 6, 7 (Memorization Test, Hallucination Benchmark)
- [ ] Extensive testing (hallucination questions validation)
- [ ] Privacy policy updates (data retention)

**Deliverables:** Privacy auditing, accuracy measurement

### Phase 4: Monitoring & Integration (Week 6)
- [ ] Implement Tools 9, 10 (Regulatory Monitor, Incident Tracker)
- [ ] Register all tools in `server.py`
- [ ] Update MCP server schema

**Deliverables:** Regulatory monitoring, incident tracking

### Phase 5: Testing & Documentation (Week 7)
- [ ] Achieve 80%+ test coverage across all tools
- [ ] Update `docs/tools-reference.md` (add AI Safety section)
- [ ] Create `docs/compliance-testing-guide.md`
- [ ] Journey tests for multi-tool workflows

**Deliverables:** Comprehensive testing, user documentation

---

## Estimated Effort

| Phase | Tasks | Complexity | Est. Hours | Risk |
|-------|-------|-----------|-----------|------|
| 1 | Tools 1-3, params, tests | High | 40-50 | Medium |
| 2 | Tools 4-5, 8, tests | Medium | 30-40 | Low |
| 3 | Tools 6-7, validation, tests | Medium | 30-40 | Medium |
| 4 | Tools 9-10, integration | Medium | 20-30 | Low |
| 5 | Tests (80%+), docs | Low | 20-30 | Low |
| **TOTAL** | | | **140-190 hours** | |

**Recommended:** 1 senior engineer + 1 QA engineer, 7-8 weeks (part-time integration)

---

## Expected Outcomes

### Immediate (Upon Implementation)

- [ ] 10 production-ready tools integrated into Loom MCP
- [ ] 80%+ test coverage
- [ ] Complete documentation (tools-reference, quick-start)
- [ ] Cost tracking functional (~$0.05-0.50 per tool)

### Capabilities Unlocked

1. **Compliance Testing:** EU AI Act Article 15 + NIST + ISO 42001 checking
2. **Fairness Auditing:** Systematic bias measurement across 7+ demographics
3. **Red-Teaming:** Prompt injection, filter mapping, adversarial robustness
4. **Privacy Auditing:** Training data memorization detection
5. **Accuracy Measurement:** Hallucination benchmarking, fact-checking
6. **Regulatory Monitoring:** 8 jurisdictions, real-time updates
7. **Incident Tracking:** Real-world AI failure monitoring & trends

### Research Impact

- **PhD Dissertation:** Empirical data on LLM safety/compliance across models
- **Publication:** Paper on "Systematic LLM Safety Evaluation Methodology"
- **Industry Tool:** Open-source compliance testing suite for AI safety engineers
- **Best Practices:** Document lessons learned, scaling considerations

---

## Success Metrics

### Quality
- [ ] 80%+ unit test coverage
- [ ] 0 critical/high security issues (bandit)
- [ ] All tools pass integration tests with mock APIs
- [ ] Documentation complete (>90% of signatures documented)

### Performance
- [ ] Prompt Injection Test: <10 min, <$0.20
- [ ] Bias Probe: <5 min, <$0.30
- [ ] Compliance Audit: <5 min, <$0.20
- [ ] Regulatory Monitor: <5 min, <$0.10

### Reliability
- [ ] No unhandled exceptions (all errors return dict)
- [ ] Cost limits enforced (never exceed max_cost_usd)
- [ ] SSRF protection active (URL validation)
- [ ] Audit logging functional (all invocations logged)

### Research Value
- [ ] At least 2 tools used in UMMRO research
- [ ] Evidence of fixing compliance issues based on tool findings
- [ ] Case study: Pre/post compliance audit comparison
- [ ] Publication: Methodology paper or research findings

---

## Next Steps

1. **Design Review** (1 week)
   - [ ] Stakeholder review of all 4 design docs
   - [ ] Feedback incorporation
   - [ ] ADR approval (architecture + security + research lead)

2. **Implementation Kick-Off** (Week 1)
   - [ ] Set up `src/loom/tools/safety.py` skeleton
   - [ ] Copy parameter models from `docs/safety-params.py` to `src/loom/params.py`
   - [ ] Create test file template `tests/test_tools/test_safety.py`

3. **Phase 1 Development** (Weeks 1-2)
   - [ ] Implement first 3 tools
   - [ ] Write unit tests
   - [ ] Verify MCP registration

4. **Continuous Integration**
   - [ ] Each phase PRed separately
   - [ ] Peer review mandatory (code + design)
   - [ ] CI pipeline validates: linting, tests, type checking

---

## Files for Implementation Team

**To use this design, copy these files:**

1. Read: `/Users/aadel/projects/loom/docs/ai-safety-tools-design.md`
2. Copy template: `/Users/aadel/projects/loom/docs/safety-params.py` → `src/loom/params.py` (append)
3. Reference: `/Users/aadel/projects/loom/docs/safety-tools-architecture.md`
4. Share with users: `/Users/aadel/projects/loom/docs/compliance-testing-quick-start.md`
5. Architecture approval: `/Users/aadel/projects/loom/docs/ADR-005-AI-Safety-Red-Teaming-Tools.md`

---

## Compliance & Ethics

### Authorized Research

This design supports Ahmed Adel Bakr Alderai's **authorized EU AI Act Article 15 compliance testing** under UMMRO research. Tools are designed for:
- ✓ Testing own LLM systems (internal testing)
- ✓ Third-party testing with consent (vendor APIs)
- ✓ Academic research (published methodology)
- ✓ Regulatory compliance audits

### Responsible Disclosure

- Jailbreak vectors are hard-coded (not shared externally)
- Incident tracker aggregates public data
- Memorization testing uses artificial canaries (no real training data extracted)
- All tools enforce SSRF protection + rate limiting

---

## Questions & Support

**Architecture Questions:**
- Contact: Software Architect Agent
- Files: `docs/ADR-005-*.md`, `docs/safety-tools-architecture.md`

**Implementation Questions:**
- Reference: `docs/ai-safety-tools-design.md` (detailed specifications)
- Template: `docs/safety-params.py` (parameter models)

**Research Questions:**
- Contact: Ahmed Adel Bakr Alderai (PhD advisor)
- Background: UMMRO research, EU AI Act compliance

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-27 | Initial design complete (4 docs + 1 template) |

---

**Status:** ✓ Design Complete → Ready for Implementation Review  
**Next Step:** Stakeholder approval (1 week) → Phase 1 kick-off (Week 2)

For complete details, see:
- Architecture: `docs/ai-safety-tools-design.md`
- Decisions: `docs/ADR-005-AI-Safety-Red-Teaming-Tools.md`
- Integration: `docs/safety-tools-architecture.md`
- Usage: `docs/compliance-testing-quick-start.md`
