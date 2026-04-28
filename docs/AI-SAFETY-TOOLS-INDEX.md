# AI Safety Tools Design — Complete Documentation Index

**Project:** UMMRO EU AI Act Compliance Testing (Loom MCP)  
**Date:** 2026-04-27  
**Status:** Design Complete → Ready for Implementation Review

---

## Quick Navigation

### For Decision Makers
1. Start: **[DESIGN-SUMMARY.md](DESIGN-SUMMARY.md)** (10 min read)
   - What's being built: 10 tools for compliance testing
   - Why: Support UMMRO PhD research in AI Safety
   - When: 7-8 week implementation roadmap
   - Impact: EU AI Act compliance checking, red-teaming, monitoring

2. Then: **[ADR-005-AI-Safety-Red-Teaming-Tools.md](ADR-005-AI-Safety-Red-Teaming-Tools.md)** (20 min read)
   - Formal architecture decision record
   - Context, decision rationale, consequences
   - Risk assessment, alternatives considered
   - Success criteria

### For Researchers / Compliance Teams
1. Start: **[compliance-testing-quick-start.md](compliance-testing-quick-start.md)** (15 min read)
   - Tool overview table (purpose, cost, time)
   - 4 real-world workflows with code examples
   - Cost management guide
   - FAQ & troubleshooting

2. Reference: **[ai-safety-tools-design.md](ai-safety-tools-design.md)** (1 hour read)
   - Complete specification for all 10 tools
   - Function signatures & parameters
   - Return value examples
   - Implementation details

### For Implementation Team
1. Start: **[DESIGN-SUMMARY.md](DESIGN-SUMMARY.md)** → Section "Implementation Roadmap"
   - 5-phase plan (7-8 weeks)
   - Estimated effort (140-190 hours)
   - Success metrics

2. Reference: **[ai-safety-tools-design.md](ai-safety-tools-design.md)**
   - Detailed specifications for each tool
   - Hard-coded examples
   - Testing strategy

3. Code: **[safety-params.py](safety-params.py)** (ready to copy)
   - Pydantic v2 parameter models
   - Field validators
   - Can be directly inserted into `src/loom/params.py`

4. Dev Guide: **[safety-tools-dev-reference.md](safety-tools-dev-reference.md)** (reference during coding)
   - Module structure
   - Helper function patterns
   - Testing patterns
   - Common mistakes to avoid

5. Architecture: **[safety-tools-architecture.md](safety-tools-architecture.md)** (reference during coding)
   - System diagrams (Mermaid)
   - Data flow examples
   - Dependency graph
   - Integration with existing Loom systems

### For Code Reviewers
1. Check: **[safety-tools-dev-reference.md](safety-tools-dev-reference.md)** → "Code Review Checklist"
2. Reference: **[safety-tools-architecture.md](safety-tools-architecture.md)** → "Integration with Existing Systems"
3. Verify: Parameter models from [safety-params.py](safety-params.py)

---

## Document Overview

| Document | Audience | Length | Purpose |
|----------|----------|--------|---------|
| **DESIGN-SUMMARY.md** | Managers, Decision-makers | 3000 words | High-level overview, roadmap, outcomes |
| **ADR-005-\*.md** | Architects, Leadership | 2000 words | Formal decision record, rationale, risks |
| **ai-safety-tools-design.md** | Spec authors, Implementers | 8000+ words | Complete tool specifications, examples |
| **safety-tools-architecture.md** | Architects, Code reviewers | 3000+ words | System design, diagrams, integration |
| **compliance-testing-quick-start.md** | Researchers, End users | 3000+ words | Workflows, cost guide, FAQ |
| **safety-tools-dev-reference.md** | Developers, Code reviewers | 3000+ words | Implementation patterns, examples, checklist |
| **safety-params.py** | Developers | 600 lines | Pydantic models, ready to copy |

---

## The 10 Tools (Quick Reference)

| Tool | Purpose | Complexity | Cost | Time |
|------|---------|-----------|------|------|
| 1. **Prompt Injection Test** | Jailbreak vulnerability testing | HIGH | $0.18 | 5-10 min |
| 2. **Model Fingerprint** | Black-box model identification | HIGH | $0.05 | 5-10 min |
| 3. **Compliance Audit** | EU AI Act Article 15 checking | MEDIUM | $0.14 | 2-5 min |
| 4. **Bias Probe** | Demographic fairness testing | MEDIUM | $0.30 | 3-5 min |
| 5. **Safety Filter Map** | Find filter boundaries | MEDIUM | $0.10 | 10-20 min |
| 6. **Memorization Test** | Training data leakage detection | HIGH | $0.48 | 5-10 min |
| 7. **Hallucination Benchmark** | Fact-checking accuracy | MEDIUM | $0.15 | 2-3 min |
| 8. **Adversarial Robustness** | Text perturbation attacks | MEDIUM | $0.01 | 2-3 min |
| 9. **Regulatory Monitor** | Track regulation changes | MEDIUM | $0.05 | 3-5 min |
| 10. **AI Incident Tracker** | Real-world failure monitoring | MEDIUM | $0.12 | 2-3 min |

See **[ai-safety-tools-design.md](ai-safety-tools-design.md)** for detailed specifications of each tool.

---

## Architecture Overview

```
Loom MCP Server (FastMCP)
    ↓
10 New Safety Tools (safety.py)
    ↓
Built on Existing Loom Infrastructure:
├── research_fetch (HTTP requests)
├── research_spider (Concurrent fetch)
├── research_markdown (HTML → markdown)
├── research_llm_chat (LLM orchestration)
├── research_llm_extract (Structured extraction)
├── research_llm_embed (Embeddings)
├── research_stylometry (Style analysis)
└── research_multilingual (Language variants)
    ↓
Supported by Infrastructure:
├── Config (hard-coded knowledge bases)
├── Cache (30-day retention)
├── CostTracker (LLM budget enforcement)
└── Audit Logger
```

See **[safety-tools-architecture.md](safety-tools-architecture.md)** for detailed diagrams and integration points.

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- Create `src/loom/tools/safety.py` module
- Implement Tools 1, 2, 3 (Prompt Injection, Model Fingerprint, Compliance Audit)
- Add parameter models to `src/loom/params.py` (use [safety-params.py](safety-params.py))
- Write unit + integration tests

**Deliverable:** Prompt injection testing, model identification, compliance checking

### Phase 2: Fairness & Robustness (Weeks 3-4)
- Implement Tools 4, 5, 8 (Bias Probe, Safety Filter Map, Adversarial Robustness)
- Unit + integration tests
- Manual validation of bias scores

**Deliverable:** Fairness auditing, robustness testing

### Phase 3: Privacy & Accuracy (Week 5)
- Implement Tools 6, 7 (Memorization Test, Hallucination Benchmark)
- Extensive testing
- Validate hallucination questions

**Deliverable:** Privacy auditing, accuracy measurement

### Phase 4: Monitoring & Integration (Week 6)
- Implement Tools 9, 10 (Regulatory Monitor, Incident Tracker)
- Register all tools in `server.py`
- Update MCP server schema

**Deliverable:** Regulatory monitoring, incident tracking

### Phase 5: Testing & Documentation (Week 7)
- Achieve 80%+ test coverage
- Update docs/tools-reference.md (add AI Safety section)
- Create compliance-testing-guide.md (from quick-start.md)
- Add journey tests

**Deliverable:** Production-ready tools + documentation

See **[DESIGN-SUMMARY.md](DESIGN-SUMMARY.md)** → "Implementation Roadmap" for details.

---

## How to Use These Documents

### Scenario 1: "I need to understand what's being proposed"
→ Read: **[DESIGN-SUMMARY.md](DESIGN-SUMMARY.md)** (10 min)

### Scenario 2: "I need to approve this architecture"
→ Read: **[ADR-005-AI-Safety-Red-Teaming-Tools.md](ADR-005-AI-Safety-Red-Teaming-Tools.md)** (20 min)

### Scenario 3: "I want to use these tools in my research"
→ Read: **[compliance-testing-quick-start.md](compliance-testing-quick-start.md)** (15 min)
→ Then: **[ai-safety-tools-design.md](ai-safety-tools-design.md)** for detailed examples

### Scenario 4: "I'm implementing these tools"
→ Phase 1: Read **[ai-safety-tools-design.md](ai-safety-tools-design.md)** (full specifications)
→ Phase 2: Copy **[safety-params.py](safety-params.py)** to `src/loom/params.py`
→ Phase 3: Use **[safety-tools-dev-reference.md](safety-tools-dev-reference.md)** during coding
→ Phase 4: Check against **[safety-tools-architecture.md](safety-tools-architecture.md)** for integration
→ Phase 5: Code review checklist in **[safety-tools-dev-reference.md](safety-tools-dev-reference.md)**

### Scenario 5: "I need to review a PR with these tools"
→ Check: **[safety-tools-dev-reference.md](safety-tools-dev-reference.md)** → "Code Review Checklist"
→ Verify: Parameter models match **[safety-params.py](safety-params.py)**
→ Confirm: Integration points from **[safety-tools-architecture.md](safety-tools-architecture.md)**

---

## Key Design Decisions

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| **Hard-coded knowledge** | Stable frameworks, audit trail | ADR-005 § A |
| **Async-first** | FastMCP compatible, parallelizable | ADR-005 § E |
| **Pydantic v2 validation** | Type safety, early errors | ADR-005 § F |
| **Per-tool cost limits** | Prevent runaway LLM bills | ADR-005 § C |
| **Reuse existing tools** | Minimize duplication | ADR-005 § A |
| **SSRF protection** | Prevent unauthorized access | ADR-005 § Risk 1 |
| **Consistent output schema** | Enable downstream automation | ADR-005 § G |
| **80%+ test coverage** | Quality bar for compliance tools | ADR-005 § H |

---

## Files to Copy/Reference During Implementation

1. **Copy to `src/loom/params.py`:**
   - All 10 parameter classes from [safety-params.py](safety-params.py)

2. **Copy to `src/loom/tools/safety.py`:**
   - Skeleton structure from [safety-tools-dev-reference.md](safety-tools-dev-reference.md)
   - Hard-coded constants (jailbreaks, fingerprints, etc.) from [ai-safety-tools-design.md](ai-safety-tools-design.md)
   - Tool implementations (iterate per phase)

3. **Reference during code review:**
   - Checklist: [safety-tools-dev-reference.md](safety-tools-dev-reference.md) → "Code Review Checklist"
   - Architecture: [safety-tools-architecture.md](safety-tools-architecture.md) → "Integration with Existing Systems"
   - Specifications: [ai-safety-tools-design.md](ai-safety-tools-design.md) → Tool X details

4. **Share with users:**
   - Quick-start: [compliance-testing-quick-start.md](compliance-testing-quick-start.md)
   - Full reference: [ai-safety-tools-design.md](ai-safety-tools-design.md)

---

## Success Criteria

- [ ] All 10 tools implemented & registered in MCP server
- [ ] 80%+ test coverage
- [ ] 0 security issues (bandit clean, SSRF safe)
- [ ] Documentation complete (tools-reference + quick-start)
- [ ] Cost tracking functional
- [ ] Audit logging functional
- [ ] At least 2 tools used in UMMRO research
- [ ] Case study: Pre/post audit comparison

See **[DESIGN-SUMMARY.md](DESIGN-SUMMARY.md)** → "Success Criteria" for full checklist.

---

## Support & Questions

**Architecture Questions:**
- Document: [ADR-005-AI-Safety-Red-Teaming-Tools.md](ADR-005-AI-Safety-Red-Teaming-Tools.md)
- Contact: Software Architect Agent

**Implementation Questions:**
- Document: [ai-safety-tools-design.md](ai-safety-tools-design.md)
- Template: [safety-params.py](safety-params.py)
- Guide: [safety-tools-dev-reference.md](safety-tools-dev-reference.md)

**Research Questions:**
- Document: [compliance-testing-quick-start.md](compliance-testing-quick-start.md)
- Contact: Ahmed Adel Bakr Alderai (PhD advisor, UMMRO)

**Usage Questions:**
- Quick start: [compliance-testing-quick-start.md](compliance-testing-quick-start.md)
- Detailed examples: [ai-safety-tools-design.md](ai-safety-tools-design.md)

---

## Version History

| Version | Date | Status | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-27 | Complete | Initial design (5 docs + 1 template) |

---

## File Locations

All files in `/Users/aadel/projects/loom/docs/`:

```
docs/
├── DESIGN-SUMMARY.md                           ← Start here
├── ADR-005-AI-Safety-Red-Teaming-Tools.md      ← Architecture decision
├── ai-safety-tools-design.md                   ← Full specification
├── safety-tools-architecture.md                ← System diagrams
├── safety-tools-dev-reference.md               ← Developer guide
├── compliance-testing-quick-start.md           ← User guide
├── safety-params.py                            ← Copy to src/loom/params.py
└── AI-SAFETY-TOOLS-INDEX.md                    ← This file
```

---

**Design Status:** ✓ Complete → Ready for Implementation Review  
**Next Step:** Stakeholder approval (1 week) → Phase 1 kick-off  
**Last Updated:** 2026-04-27

For a quick overview, start with **[DESIGN-SUMMARY.md](DESIGN-SUMMARY.md)** (10 minutes).
