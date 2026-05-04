# Compliance Certification Timeline & Roadmap

**Master Plan:** Achieve SOC2 Type II, ISO 27001, and EU AI Act conformity by end of 2026  
**Overall Duration:** 8 months (May - December 2026)  
**Parallel Execution:** All three frameworks assessed concurrently (cost savings, control overlap)

---

## Phase Overview

```
MAY 2026     Preparation & Auditor Selection
  │
JUNE 2026    Gap Remediation (Critical controls)
  │
JULY 2026    Gap Remediation (High-priority controls) + Audits Begin
  │
AUG-SEP 2026 Main Audit Fieldwork + Control Testing
  │
OCT 2026     Report Drafting & Findings Review
  │
NOV 2026     Final Remediation & Certification
  │
DEC 2026     Certificates Issued & Post-Audit Activities
```

---

## Detailed Timeline

### MONTH 1: MAY 2026 — Preparation & Auditor Selection

#### Week 1 (May 1-7)

**SOC2 Audit Prep:**
- [ ] Finalize SOC2 RFP (DONE: RFP_SOC2_AUDIT.md created)
- [ ] Identify 3-5 audit firms (Vanta, Drata, Secureframe, Big 4)
- [ ] Send RFP to shortlisted auditors
- [ ] Expected cost: $15K-$50K

**ISO 27001 Audit Prep:**
- [ ] Finalize ISO 27001 RFP (DONE: RFP_ISO27001.md created)
- [ ] Identify accredited certification bodies (UKAS auditors)
- [ ] Send RFP to 3-5 bodies
- [ ] Expected cost: $25K-$40K

**EU AI Act Prep:**
- [ ] Finalize EU AI Act RFP (DONE: RFP_EU_AI_ACT.md created)
- [ ] Identify Notified Bodies or qualified assessment providers
- [ ] Send RFP to 2-3 providers
- [ ] Expected cost: €20K-€40K

**Documentation Baseline:**
- [ ] Complete CURRENT_CONTROLS.md (DONE)
- [ ] Complete GAP_ANALYSIS.md (DONE)
- [ ] Review existing architecture docs (CLAUDE.md)

**Effort:** 20 hours (admin + communication)

---

#### Week 2 (May 8-14)

**Auditor Selection:**
- [ ] Receive proposals from SOC2 auditors (deadline May 10)
- [ ] Receive proposals from ISO 27001 auditors (deadline May 10)
- [ ] Receive proposals from EU AI Act providers (deadline May 10)
- [ ] Review proposals (scoring: cost, experience, timeline, geography)
- [ ] Select preferred vendors
- [ ] Negotiate contracts and SLAs

**Kickoff Meetings:**
- [ ] SOC2 auditor kickoff meeting (video, 2 hours)
  - Confirm observation period dates (April 2026 - September 2026)
  - Review system architecture
  - Discuss testing approach and timeline
- [ ] ISO 27001 certification body kickoff (video, 2 hours)
  - Confirm Stage 1 and Stage 2 timeline
  - Review ISMS scope
  - Discuss initial gap assessment
- [ ] EU AI Act provider kickoff (video, 2 hours)
  - Confirm assessment approach
  - Discuss technical file requirements
  - Clarify conformity statement scope

**Contract & Engagement:**
- [ ] Sign SOC2 audit engagement letter
- [ ] Sign ISO 27001 certification contract
- [ ] Sign EU AI Act conformity assessment agreement
- [ ] Deposit payments (typically 50% upfront)

**Effort:** 25 hours (meetings + negotiation + contract review)

---

#### Week 3-4 (May 15-31)

**Gap Remediation Planning:**
- [ ] Create detailed remediation project plan (Gantt chart)
- [ ] Prioritize critical gaps (encryption, change mgmt, incident response)
- [ ] Allocate development time
- [ ] Set milestones and sign-off gates

**Initial Documentation:**
- [ ] Draft information security policy (for ISO 27001)
- [ ] Draft ISMS scope statement
- [ ] Start data classification matrix
- [ ] Begin risk register (ISO 27001 + EU AI Act)

**Infrastructure Prep:**
- [ ] Review current Hetzner security (SLA, certifications)
- [ ] Request Hetzner SOC2/ISO 27001 report (if available)
- [ ] Document current TLS configuration
- [ ] Verify API key authentication working correctly

**Effort:** 30 hours (planning + documentation start)

**MONTH 1 TOTAL: 75 hours (~2 weeks FTE)**

---

### MONTH 2: JUNE 2026 — Gap Remediation (Critical Controls)

#### Week 1-2 (June 1-14)

**SOC2: Encryption at Rest**
- [ ] Implement mandatory SQLCipher for all SQLite databases
- [ ] Test encrypted database creation and access
- [ ] Document encryption key generation and management
- [ ] Create backup/restore procedure for encrypted databases
- [ ] Update configuration (USE_SQLCIPHER=true by default)
- [ ] Update documentation (API keys, encryption options)
- [ ] Effort: 2-3 days

**SOC2: Formal Change Management**
- [ ] Create change request (CR) template
- [ ] Establish CR approval process (even for solo dev, for audit purposes)
- [ ] Document pre-deployment checklist (testing, review, verification)
- [ ] Create change log (git + CR record)
- [ ] Define rollback procedures
- [ ] Effort: 3-5 days

**ISO 27001: Information Security Policy**
- [ ] Expand draft policy to cover all 14 ISO 27001 domains
- [ ] Include risk management approach
- [ ] Document responsibilities and accountability
- [ ] Get management approval (developer signature)
- [ ] Publish and communicate policy
- [ ] Effort: 2-3 days

**Effort Week 1-2:** 30 hours

---

#### Week 3 (June 15-21)

**SOC2: Incident Response Playbook**
- [ ] Define incident severity levels (Critical/High/Medium/Low)
- [ ] Create incident detection procedures
- [ ] Document incident response workflow (detect → assess → contain → remediate → review)
- [ ] Define escalation procedures and contacts
- [ ] Create post-incident review template
- [ ] Create incident log template
- [ ] Effort: 3-5 days

**ISO 27001: ISMS Scope Statement**
- [ ] Finalize formal ISMS scope definition
- [ ] Document inclusions and exclusions (with justification)
- [ ] Create system boundary diagram
- [ ] Document shared responsibilities (Hetzner, providers)
- [ ] Get management approval
- [ ] Effort: 1-2 days

**ISO 27001: Risk Assessment Methodology**
- [ ] Define risk assessment framework (ISO 31000 aligned)
- [ ] Create probability and impact scales
- [ ] Create risk matrix (probability × impact)
- [ ] Document risk appetite and acceptance criteria
- [ ] Define risk treatment options (mitigate/accept/avoid/transfer)
- [ ] Effort: 2-3 days

**Effort Week 3:** 25 hours

---

#### Week 4 (June 22-30)

**SOC2: Vendor Risk Assessment**
- [ ] Create vendor risk assessment questionnaire
- [ ] Document Hetzner security controls and SLA
- [ ] Assess other critical vendors (NVIDIA NIM, Groq, etc.)
- [ ] Create vendor inventory with risk levels
- [ ] Establish vendor review schedule (annual)
- [ ] Effort: 2-3 days

**EU AI Act: Risk Management Plan**
- [ ] Identify AI-specific risks (jailbreak discovery, bias, hallucination, etc.)
- [ ] Assess probability and impact for each risk
- [ ] Document mitigation measures
- [ ] Plan effectiveness measurement
- [ ] Document residual risk levels
- [ ] Create risk monitoring procedure
- [ ] Effort: 3-5 days

**Data Classification**
- [ ] Define data classification scheme (Public/Internal/Confidential/Secret)
- [ ] Classify all data types (code, config, logs, cache, sessions, audit)
- [ ] Document retention and disposal procedures
- [ ] Map to encryption and access control requirements
- [ ] Effort: 2-3 days

**Effort Week 4:** 30 hours

**MONTH 2 TOTAL: 85 hours (~2.1 weeks FTE)**

---

### MONTH 3: JULY 2026 — Gap Remediation (High-Priority) + Audit Kickoff

#### Week 1-2 (July 1-14)

**Remaining Gap Remediation:**

**SOC2/ISO 27001: Access Control Matrix**
- [ ] Create RACI matrix (Responsible, Accountable, Consulted, Informed)
- [ ] Document user roles and permissions
- [ ] Establish provisioning/deprovisioning procedures
- [ ] Schedule quarterly access reviews
- [ ] Effort: 2-3 days

**ISO 27001: Encryption Key Lifecycle**
- [ ] Document key generation procedures (API key, AUDIT_SECRET, DB password)
- [ ] Document key storage requirements (env vars, file permissions)
- [ ] Document key rotation schedule (every 12 months)
- [ ] Document key retirement and destruction
- [ ] Implement key versioning for audit signing key
- [ ] Effort: 2-3 days

**ISO 27001: Incident Response Playbook** (if not completed in June)
- [ ] Finalize incident severity matrix
- [ ] Document response workflow
- [ ] Create incident log template
- [ ] Schedule incident response training/drills
- [ ] Effort: 2-3 days

**Effort Week 1-2:** 25 hours

---

#### Week 3-4 (July 15-31)

**Evidence Compilation for Auditors:**

**For all three audits:**
- [ ] Organize source code (GitHub link provided)
- [ ] Prepare audit logs (sanitized samples, PII-redacted)
- [ ] Prepare configuration examples (API keys redacted)
- [ ] Compile policy and procedure documents
- [ ] Prepare test results (pytest coverage, mypy output)
- [ ] Prepare infrastructure documentation (Hetzner setup)
- [ ] Create system architecture diagrams
- [ ] Prepare data inventory and classification matrix
- [ ] Prepare vendor risk assessments
- [ ] Prepare risk registers (all three frameworks)

**SOC2 Specific:**
- [ ] Prepare control mapping (SOC2 CC/A/C to Loom controls)
- [ ] Prepare monitoring and alerting documentation
- [ ] Prepare backup and recovery procedures

**ISO 27001 Specific:**
- [ ] Prepare ISMS scope statement
- [ ] Prepare information security policy
- [ ] Prepare risk assessment methodology
- [ ] Prepare initial risk register

**EU AI Act Specific:**
- [ ] Prepare AI system description (7 tools)
- [ ] Prepare risk management plan (AI-specific)
- [ ] Prepare data quality procedures
- [ ] Prepare human oversight documentation
- [ ] Prepare model card (draft)

**Auditor Kickoff Meetings (If not done in May):**
- [ ] SOC2 auditor: Confirm testing approach and evidence requirements
- [ ] ISO 27001 auditor: Confirm Stage 1 assessment timeline
- [ ] EU AI Act provider: Confirm technical file requirements

**Effort Week 3-4:** 35 hours

**MONTH 3 TOTAL: 60 hours (~1.5 weeks FTE)**

---

### MONTH 4: AUGUST 2026 — Main Audit Fieldwork (SOC2 & ISO 27001) + EU AI Act Submission

#### Week 1-2 (August 1-14)

**SOC2 Type II Fieldwork:**
- [ ] Evidence submission (all documents, logs, configurations)
- [ ] ISO 27001 Stage 1 assessment (gap assessment, preliminary findings)
- [ ] EU AI Act technical file submission (first draft)

**Activities:**
- [ ] Developer interviews with SOC2 auditor (2-4 hours)
- [ ] System demonstration (MCP server, authentication, logging)
- [ ] Log review (sample of audit logs)
- [ ] Control testing (authentication, rate limiting, encryption)
- [ ] Access control verification
- [ ] Change management verification

**ISO 27001 Stage 1 Audit:**
- [ ] Auditor document review (policies, procedures)
- [ ] ISMS scope and boundaries verification
- [ ] Risk assessment methodology review
- [ ] Current control assessment
- [ ] Gap analysis (ISO 27001 Annex A controls)
- [ ] Preliminary findings (critical/high/medium/low)

**EU AI Act Assessment Begins:**
- [ ] Auditor review of technical file (completeness check)
- [ ] Clarification questions submitted
- [ ] Evidence gap identification
- [ ] Testing plan development

**Effort:** 30 hours

---

#### Week 3-4 (August 15-31)

**SOC2 Testing Continuation:**
- [ ] Detailed control testing (each CC, A, C criterion)
- [ ] Testing evidence collection:
  - Authentication: Token generation, failed auth attempts
  - Rate limiting: Verification of per-user limits
  - Encryption: TLS certificate verification, SQLCipher database verification
  - Audit logging: Log integrity verification (HMAC validation)
  - Change management: Git log review, CR documentation
  - Incident response: Test scenario execution
- [ ] Management interviews (effectiveness of controls)

**ISO 27001 Stage 1 Completion:**
- [ ] Finalize gap assessment report
- [ ] Risk assessment review and finalization
- [ ] Stage 1 report issued (findings + remediation roadmap)
- [ ] Identify critical findings for immediate remediation
- [ ] Create Stage 2 action plan

**EU AI Act Assessment Continuation:**
- [ ] Provide responses to clarification questions
- [ ] Submit additional evidence (test results, risk registers)
- [ ] Schedule system demonstration (if on-site visit required)

**Monthly Audit Status Calls:**
- [ ] SOC2: Weekly status call with auditor
- [ ] ISO 27001: Weekly status call with certification body
- [ ] EU AI Act: Bi-weekly status call with provider

**Effort:** 35 hours

**MONTH 4 TOTAL: 65 hours (~1.6 weeks FTE)**

---

### MONTH 5: SEPTEMBER 2026 — SOC2 Observation Continuation + ISO 27001 Stage 1 Remediation

#### Week 1-2 (September 1-14)

**SOC2 Testing Finalization:**
- [ ] Complete all control testing (CC, A, C)
- [ ] Risk testing (does system actually handle identified risks?)
- [ ] Resilience testing (circuit breaker, timeouts, error handling)
- [ ] Recovery testing (backup restoration, RTO/RPO verification)
- [ ] Anomaly detection testing (rate limit spike, error rate spike)

**ISO 27001 Stage 1 Remediation:**
- [ ] Address critical findings (non-conformities)
  - Critical example: Risk register incomplete
  - Remediation: Complete risk assessment for all identified assets
  - Timeline: 2 weeks
- [ ] Address high findings (conformity gaps)
  - High example: Access control matrix missing
  - Remediation: Create and document access matrix
  - Timeline: 1 week
- [ ] Update risk register with mitigation effectiveness

**EU AI Act Assessment Continuation:**
- [ ] Provide final responses to outstanding questions
- [ ] Submit test results (if adversarial testing conducted)
- [ ] Finalize technical file sections

**First Quarterly DR Test (Optional, but recommended):**
- [ ] Execute disaster recovery test (1 day)
- [ ] Document RTO and RPO
- [ ] Verify recovery procedure
- [ ] Identify gaps or issues

**Effort:** 40 hours

---

#### Week 3-4 (September 15-30)

**SOC2 Report Drafting:**
- [ ] Auditor drafts preliminary SOC2 Type II report
- [ ] Report includes:
  - Summary of scope and testing approach
  - Assessment of each control (CC, A, C)
  - Control effectiveness conclusions
  - Any exceptions or limitations
  - Auditor attestation statement

**ISO 27001 Stage 2 Begins:**
- [ ] Stage 2 observation period starts (6-month period: September 2026 - February 2027)
- [ ] However, we target certification by end of 2026 (compressed timeline)
- [ ] Monthly evidence collection begins (backups, incident logs, access reviews)
- [ ] Implement all Stage 1 remediation items

**EU AI Act Assessment Finalization:**
- [ ] Auditor completes assessment (field work)
- [ ] Draft conformity assessment report issued for review
- [ ] Feedback on findings and recommendations

**Effort:** 35 hours

**MONTH 5 TOTAL: 75 hours (~1.9 weeks FTE)**

---

### MONTH 6: OCTOBER 2026 — Report Review & Final Remediation

#### Week 1-2 (October 1-14)

**SOC2 Report Review:**
- [ ] Receive draft SOC2 Type II report from auditor
- [ ] Review findings (critical/high/medium/low)
- [ ] Prepare response to any exceptions or questions
- [ ] Discuss remediation timeline with auditor
- [ ] Expected: Report is favorable (controls are mostly effective)

**ISO 27001 Stage 2 Continuation:**
- [ ] Monthly evidence collection (evidence package)
  - Audit logs (verified for HMAC signatures)
  - Backup verification (monthly backup test)
  - Incident logs (any incidents in the month)
  - Access reviews (if scheduled)
  - Configuration changes (git log)
- [ ] Risk register updates (quarterly risk assessment due end-Q4)
- [ ] Internal audit planning (October ISO 27001 self-audit)

**EU AI Act Assessment Report:**
- [ ] Receive draft conformity assessment report
- [ ] Review findings and recommendations
- [ ] Prepare responses to questions
- [ ] Plan any additional evidence submission

**Effort:** 30 hours

---

#### Week 3-4 (October 15-31)

**Final Remediation (All Three Frameworks):**
- [ ] SOC2: Address any findings from report (usually low/medium priority)
- [ ] ISO 27001: Prepare for Stage 2 closing (ensure all controls operational)
- [ ] EU AI Act: Address any assessment findings (usually clarifications)

**ISO 27001 Internal Audit:**
- [ ] Conduct self-audit against ISO 27001 (Annex A controls)
- [ ] Document findings
- [ ] Create action plan for any non-conformities
- [ ] Prepare for auditor verification

**Management Reviews (All Frameworks):**
- [ ] SOC2: Management review of control effectiveness
- [ ] ISO 27001: Management review of ISMS (quarterly)
- [ ] EU AI Act: Management review of AI risk management

**Effort:** 35 hours

**MONTH 6 TOTAL: 65 hours (~1.6 weeks FTE)**

---

### MONTH 7: NOVEMBER 2026 — Stage 2 Completion + ISO 27001 Certification + EU AI Act Conformity

#### Week 1-2 (November 1-14)

**SOC2 Type II Report Finalization:**
- [ ] Final sign-off on SOC2 Type II report
- [ ] Attestation letter signed by auditor
- [ ] Receive final SOC2 certificate/report
- [ ] Expected: "System complies with SOC2 Type II security criteria"

**ISO 27001 Stage 2 Completion:**
- [ ] Final month of observation period (September start → December end, but expedited)
- [ ] Auditor conducts final on-site or remote verification
- [ ] Auditor reviews ISMS documentation and control evidence
- [ ] Final internal audit results reviewed
- [ ] Management review conclusion documented

**EU AI Act Conformity Assessment Finalization:**
- [ ] Final assessment report issued
- [ ] Conformity statement provided (if compliant)
- [ ] Expected: "System complies with Articles 10-15"
- [ ] Technical file approved

**Effort:** 25 hours

---

#### Week 3-4 (November 15-30)

**ISO 27001 Certification:**
- [ ] Auditor issues ISO 27001 certification (if all controls effective)
- [ ] Expected: 3-year certificate valid through November 2029
- [ ] First surveillance audit scheduled (typically 12 months after certification)
- [ ] Receive certification documentation

**EU AI Act Conformity Documentation:**
- [ ] Receive final conformity assessment report
- [ ] Conformity statement filed (for regulatory records)
- [ ] EU AI Act technical file finalized

**Post-Audit Activities (Planning):**
- [ ] Plan annual surveillance audits (SOC2 yearly, ISO 27001 yearly)
- [ ] Schedule next internal audits
- [ ] Update ISMS for improvements
- [ ] Plan next risks assessment

**Effort:** 20 hours

**MONTH 7 TOTAL: 45 hours (~1.1 weeks FTE)**

---

### MONTH 8: DECEMBER 2026 — Certificates Issued & Market Launch

#### Week 1-2 (December 1-14)

**Certification Receipt & Documentation:**
- [ ] Receive physical/digital SOC2 Type II report and certificate
- [ ] Receive ISO 27001 certificate (valid 3 years)
- [ ] Receive EU AI Act conformity statement and report
- [ ] All three certificates ready for customer sharing

**Marketing & Sales Enablement:**
- [ ] Create certification announcement (blog post, social media)
- [ ] Update website: "SOC2 Type II Compliant", "ISO 27001 Certified", "EU AI Act Compliant"
- [ ] Prepare customer-facing collateral
- [ ] Update sales materials and RFP responses

**Post-Audit Improvements:**
- [ ] Review auditor recommendations (medium/low priority improvements)
- [ ] Create improvement backlog
- [ ] Prioritize improvements for 2027

**Effort:** 15 hours

---

#### Week 3-4 (December 15-31)

**Surveillance & Renewal Planning:**
- [ ] Schedule Q1 2027 surveillance audits
- [ ] Plan next annual risk assessment (Q1 2027)
- [ ] Update ISMS documentation with lessons learned
- [ ] Begin planning for next ISO 27001 surveillance (Q4 2027)

**Documentation & Record-Keeping:**
- [ ] Archive all audit reports (compliance records)
- [ ] Maintain control evidence documentation
- [ ] Update policy and procedure documentation based on audit recommendations
- [ ] Establish 7-year record retention for compliance files

**Effort:** 10 hours

**MONTH 8 TOTAL: 25 hours (~0.6 weeks FTE)**

---

## Timeline Summary Table

| Month | Focus | Key Deliverables | FTE Weeks | Auditor Activity |
|-------|-------|------------------|-----------|------------------|
| **May** | Prep & Selection | RFPs, Auditor selection, Contracts signed | 2.0 | Proposal submissions, kickoff calls |
| **Jun** | Gap Remediation (Critical) | Encryption, Change Mgmt, Incident Response, Vendor Assess | 2.1 | Documentation review prep |
| **Jul** | Gap Remediation (High) + Prep | Access Control, Key Mgmt, Evidence compilation | 1.5 | Gap assessment review |
| **Aug** | Main Fieldwork | Evidence submission, Testing, Technical file | 1.6 | SOC2 testing, ISO Stage 1, EU AI Act review |
| **Sep** | Continuation + Obs | DR test, Control testing, Stage 1 remediation | 1.9 | SOC2 finalization, ISO Stage 2 start, EU AI Act review |
| **Oct** | Report Review | Draft reports received, Remediation planning | 1.6 | Report drafting, Stage 2 monitoring |
| **Nov** | Finalization | Stage 1→2 transition, Certifications | 1.1 | Final audit, Certification |
| **Dec** | Market Launch | Certificates received, Marketing, Renewal planning | 0.6 | Post-audit consulting |
| **TOTAL** | | **All three certifications achieved** | **12.4 weeks** | **8 months** |

---

## Key Milestones & Checkpoints

```
✓ May 5: RFPs sent to auditors
✓ May 15: Auditors selected, contracts signed
✓ May 31: Kickoff meetings complete
✓ June 30: Critical gap remediation complete
✓ July 31: High-priority gap remediation complete
✓ August 31: SOC2 testing phase complete, ISO Stage 1 findings received
✓ September 30: SOC2 observation period complete, EU AI Act review ongoing
✓ October 31: Draft reports received (all three frameworks)
✓ November 15: SOC2 Type II report finalized
✓ November 20: ISO 27001 certification issued (if all controls effective)
✓ November 30: EU AI Act conformity statement issued
✓ December 15: Certificates received, marketing launch
✓ December 31: Surveillance audit schedule planned for 2027
```

---

## Budget & Resource Summary

### Audit Costs (External)

| Framework | Phase 1 | Phase 2 | Total | Notes |
|-----------|---------|---------|-------|-------|
| **SOC2 Type II** | $15K | $20K | $35K | Type II includes 6-month observation |
| **ISO 27001** | $12K | $18K | $30K | Stage 1 + Stage 2 (6-month observation) |
| **EU AI Act** | €15K | €15K | €30K | Assessment + conformity statement |
| | | | **$95K + €30K** | **~$128K USD** |

### Internal Resource Costs

| Activity | Hours | FTE Weeks | Notes |
|----------|-------|-----------|-------|
| Audit prep & coordination | 100 | 2.5 | RFP, selection, kickoff |
| Gap remediation | 150 | 3.75 | Critical + high-priority controls |
| Evidence compilation | 100 | 2.5 | Documentation, logs, tests |
| Auditor interviews & demos | 80 | 2.0 | Testing, verification calls |
| Response to findings | 80 | 2.0 | Clarifications, additional evidence |
| Post-audit activities | 50 | 1.25 | Certificates, marketing, planning |
| **Total** | **560** | **14** | **3.5 months FTE** |

### Total Certification Cost

- **External audit/certification:** ~$128K
- **Internal labor (14 weeks @ $150/hr avg):** ~$105K
- **Total:** ~$233K (for 8-month engagement)

---

## Risk & Contingencies

### Potential Delays

| Risk | Impact | Mitigation | Contingency |
|------|--------|-----------|------------|
| Auditor unavailable | 2-4 week delay | Start with multiple auditor options; contracts specify timeline | Shift to next auditor; extend timeline to Q1 2027 |
| Major findings (unforeseen) | 4-8 week remediation | Thorough gap analysis in May minimizes surprises | Extend observation period; prioritize high-risk controls |
| Technical issues (system down) | 1-2 week delay | Maintain backup system; test recovery | Use Hetzner snapshot; accept minor timeline slip |
| Personnel conflict | 1-2 week delay | Solo developer = minimal scheduling conflicts | Could occur if developer becomes unavailable (mitigate via documentation) |

### High-Confidence Success Factors

1. **Comprehensive gap analysis done upfront** (May 2026) - minimizes surprises
2. **Parallel execution of three frameworks** - shared controls, cost savings
3. **Established controls already in place** - 60-70% implemented, not starting from zero
4. **Clear auditor communication** - weekly calls, monthly status updates
5. **Documented remediation plan** - concrete deadlines and deliverables
6. **Dedicated timeline** - 14 weeks of FTE allocated through December

---

## Post-Certification Roadmap (2027 & Beyond)

### Q1 2027: First Surveillance Audits

- [ ] SOC2 Type II: First annual surveillance audit (2-3 days)
- [ ] ISO 27001: First surveillance audit (2-3 days)
- [ ] EU AI Act: First review (if annual surveillance required)

### Q2 2027: ISMS Improvements

- [ ] Implement Prometheus monitoring
- [ ] Deploy Slack alerting
- [ ] Extend RBAC (formal role definitions)
- [ ] Implement OAuth2 (for multi-user support)

### Q3 2027: Third Certification Pursuit

- [ ] FedRAMP certification (for U.S. government sales)
- [ ] Additional compliance frameworks (HIPAA, PCI-DSS if needed)

### Q4 2027: Recertification Planning

- [ ] Begin planning for ISO 27001 recertification (3-year cycle)
- [ ] Plan SOC2 Type II renewal (annual)

---

## Success Criteria

**Certification Achieved When:**

1. ✓ SOC2 Type II report issued with unqualified attestation
2. ✓ ISO 27001 certificate issued (valid 3 years)
3. ✓ EU AI Act conformity statement issued (compliant with Articles 10-15)
4. ✓ Zero critical findings that prevent certification
5. ✓ All high findings remediated before certification date

**Market Launch Criteria:**

1. ✓ Certificates in hand (physical or digital)
2. ✓ Customer-facing marketing materials updated
3. ✓ Website updated with certification badges
4. ✓ Sales materials include certification compliance statements
5. ✓ Internal documentation updated for ISMS maintenance

---

**End of Timeline Document**

---

**Document Version:** 1.0  
**Last Updated:** May 4, 2026  
**Classification:** Internal Use / Compliance Documentation
