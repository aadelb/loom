# Request for Proposal (RFP) for ISO 27001 Certification

**Date of Issue:** May 4, 2026  
**Target Certification Date:** Q4 2026 (October - December)  
**Implementation Timeline:** 6 months (May - November 2026)

---

## 1. Executive Summary

Loom Research Tools is seeking an accredited ISO 27001 certification body to assist with designing, implementing, and certifying our Information Security Management System (ISMS). ISO 27001 will complement our concurrent SOC2 Type II audit and demonstrate systematic, comprehensive information security governance to customers, regulators, and stakeholders.

We require support for:
- **Stage 1 Audit (May - July 2026):** ISMS design review, gap assessment, remediation planning
- **Stage 2 Audit (August - November 2026):** 6-month observation period with continuous control testing
- **Certification (December 2026):** Final attestation and certificate issuance

---

## 2. About Loom Research Tools (Organization Context)

### Organization Profile
- **Legal Name:** Loom Research Tools
- **Principal/Owner:** Ahmed Adel Bakr Alderai (solo developer)
- **Organizational Type:** Sole proprietorship / Independent contractor
- **Employees:** 1 (founder)
- **Location:** EU-based; Hetzner infrastructure (Germany/Germany)
- **Industry:** Software/SaaS - Research Intelligence Platform
- **Annual Revenue:** ~$0-$50K (early stage)
- **Customer Base:** Security researchers, compliance teams, AI safety researchers

### System Scope (What We Want to Certify)

**In Scope:**
- Loom MCP Research Server (all 220+ tools)
- API key authentication layer
- Audit logging infrastructure (JSONL + HMAC-SHA256)
- Cache management system
- Session management (persistent browser sessions)
- Rate limiting and tier enforcement
- Configuration management
- Hetzner infrastructure (shared responsibility)

**Out of Scope:**
- Third-party research providers (Exa, Tavily, Firecrawl, etc.) - note: we verify SLAs
- Customer applications using our API
- Pre-acquisition information security of authors/contributors
- Cryptographic algorithm design (we use standard SHA-256, TLS 1.2+, HMAC-SHA256)

---

## 3. Current State of Information Security

### 3.1 Existing Security Controls

**A. Organization & Personnel**

| Control | Status | Details |
|---------|--------|---------|
| Information Security Policy | Draft | Framework policy in place; needs formalization |
| Roles & Responsibilities | Documented | Solo developer = all roles (can be improved) |
| Access Control Matrix | Partial | API key authentication only; no RBAC yet |
| Security Awareness Training | Manual | Annual self-training (solo developer) |
| Contractor/Vendor Management | Partial | Hetzner SLA reviewed; other vendors noted |

**B. Asset Management**

| Control | Status | Details |
|---------|--------|---------|
| Asset Inventory | Partial | GitHub repo (code), Hetzner server (compute), config files |
| Asset Classification | None | All treated as confidential (can be refined) |
| Data Classification | None | Documented informally; needs formal policy |
| Ownership & Responsibility | Documented | All assets owned by Ahmed Adel |

**C. Access Control**

| Control | Status | Details |
|---------|--------|---------|
| Authentication | Implemented | Bearer token (API key) + environment variables |
| Authorization | Partial | Tier-based (free/pro/enterprise) feature flags |
| Access Rights Management | Manual | Git-based change approval (solo) |
| Segregation of Duties | Limited | Solo developer = limited segregation |
| Password Management | N/A | No password-based authentication |

**D. Cryptography**

| Control | Status | Details |
|---------|--------|---------|
| Cryptographic Controls Policy | None | Documented informally |
| Encryption in Transit | Implemented | TLS 1.2+ for all external calls |
| Encryption at Rest | Partial | Optional SQLCipher; not mandatory |
| Key Management | Partial | Environment variables; no key lifecycle policy |
| Certificate Management | Implemented | Hetzner manages TLS certificates |

**E. Physical & Environmental Security**

| Control | Status | Shared Responsibility |
|---------|--------|----------------------|
| Physical Access Control | Hetzner | Data center badges, biometric access, surveillance |
| Environmental Protection | Hetzner | Power, cooling, fire suppression (gaseous) |
| Equipment Security | Partial | Server logs, no hardware disposal policy |
| Workspace Security | Partial | Solo developer home office; basic physical controls |

**F. Operations & Communications**

| Control | Status | Details |
|---------|--------|---------|
| Change Management | Partial | Git-based; no formal CR process |
| Backup & Recovery | Partial | Daily snapshots; no tested restoration plan |
| Network Security | Implemented | Hetzner firewalls; no local firewall config documented |
| Monitoring & Logging | Implemented | Structured logging + audit logs with HMAC signatures |
| Event Logging | Implemented | Per-tool invocation; 30-day retention |
| Clock Synchronization | Implemented | NTP (system time); logs in ISO 8601 UTC |

**G. Incident Management**

| Control | Status | Details |
|---------|--------|---------|
| Incident Response Plan | Draft | Informal procedures; needs formalization |
| Incident Detection | Partial | Error monitoring + rate limit anomalies |
| Incident Assessment & Decision | Partial | Manual; no formal triage process |
| Incident Response & Escalation | Manual | Email/Slack to developer |
| Post-Incident Review | Informal | Audit logs available; no formal RCA process |

**H. Business Continuity & Disaster Recovery**

| Control | Status | Details |
|---------|--------|---------|
| Business Continuity Planning | Partial | RTO 15 min; documented but not tested |
| Disaster Recovery Plan | Partial | Daily backups; code in GitHub; no tested full restore |
| Testing & Training | None | No formal testing schedule |
| Review & Updates | Manual | Reviewed ad hoc; no annual schedule |

**I. Compliance Management**

| Control | Status | Details |
|---------|--------|---------|
| Legal & Regulatory Compliance | Partial | GDPR-aware (PII scrubbing); no formal audit |
| Data Subject Rights | Documented | Can export/delete audit logs on request |
| Vendor Management | Partial | Hetzner SLA reviewed; others noted but not formally assessed |
| Risk Assessment | Informal | Documented in CLAUDE.md; needs formal risk register |

---

## 4. ISMS Implementation Plan (A.13 - A.14 of ISO 27001)

### 4.1 Stage 1: ISMS Design & Planning (May - July 2026)

**Activities:**

1. **Information Security Policy Formalization**
   - Expand draft policy to cover all 14 ISO 27001 domains
   - Define risk acceptance criteria
   - Board approval (solo developer signature)

2. **Asset Inventory & Classification**
   - Complete asset inventory (code, data, infrastructure, people)
   - Define asset classification scheme (public/internal/confidential/secret)
   - Assign ownership and responsibility

3. **Data Classification Policy**
   - Define data categories (customer data, audit logs, config, research results)
   - Document retention and disposal procedures
   - Map to encryption and access control requirements

4. **Risk Assessment Methodology**
   - Document risk assessment framework (NIST or ISO 31000)
   - Define risk matrix (probability × impact)
   - Establish risk appetite and acceptance levels

5. **Initial Risk Assessment (ISO 27001:2022 Clause 6.1.3)**
   - Identify assets and threats
   - Assess likelihood and impact
   - Calculate risk levels
   - Determine treatment (mitigate/accept/avoid/transfer)

6. **ISMS Scope Definition (Clause 4.3)**
   - Formalize system boundary
   - Document inclusions and exclusions
   - Define stakeholder consultation process

7. **Baseline Control Mapping**
   - Compare current controls to Annex A (14 domains, 93 controls)
   - Identify gaps and overlaps
   - Prioritize remediation

8. **ISMS Documentation Package**
   - Control matrix (current state)
   - Risk register (with risk owner and treatment plan)
   - ISMS procedures manual
   - Access control matrix
   - Change management procedures
   - Incident response playbook

**Deliverable:** Stage 1 Audit Report with gap assessment, remediation roadmap, and certification feasibility statement.

### 4.2 Stage 2: ISMS Implementation & Observation (August - November 2026)

**Activities:**

1. **Gap Remediation (August - September)**
   - Implement critical controls (encryption, access control, incident response)
   - Formalize procedures (change management, backup/recovery, audit)
   - Document evidence of control implementation
   - Train on new procedures (self-training for solo developer)

2. **Observation Period (August - November: 6 months)**
   - Continuous operation under documented ISMS
   - Maintain audit logs and evidence files
   - Demonstrate control execution (e.g., monthly backups, incident logs)
   - Monthly self-audit and evidence collection

3. **Internal Audits (October)**
   - Conduct internal audit of ISMS against ISO 27001
   - Document findings and corrective actions
   - Verify remediation of Stage 1 findings

4. **Management Review (November)**
   - Assess ISMS effectiveness and adequacy
   - Review risk register and risk appetite
   - Document management approval for certification

5. **Readiness Review (November)**
   - Pre-audit checklist against ISO 27001 requirements
   - Verify all control evidence is available
   - Ensure documentation is complete and current

**Deliverable:** Stage 2 Audit Report with certification recommendation (if all controls are effective).

### 4.3 Control Annex (ISO 27001:2022 Annex A)

We will implement controls across 14 domains:

| Domain | Target Controls | Current Status |
|--------|-----------------|-----------------|
| **A.5: Organizational Controls** | 6 controls | 50% (policy, roles drafted) |
| **A.6: People Controls** | 7 controls | 30% (training, awareness informal) |
| **A.7: Physical Controls** | 9 controls | 80% (Hetzner responsibility) |
| **A.8: Network & System Controls** | 14 controls | 70% (encryption, access, monitoring) |
| **A.9: Cryptographic Controls** | 4 controls | 60% (TLS, optional SQLCipher) |
| **A.10: Physical & Logical Storage** | 4 controls | 50% (cache, backup, retention) |
| **A.11: Identity & Access Management** | 9 controls | 60% (auth, RBAC partial, segregation limited) |
| **A.12: Cryptographic Key Management** | 3 controls | 40% (env vars; no lifecycle) |
| **A.13: Supplier Relations** | 2 controls | 50% (Hetzner SLA; vendor assessment informal) |
| **A.14: Information Security Incident Management** | 7 controls | 40% (detection, response informal) |
| **A.15: Business Continuity Management** | 4 controls | 50% (backups, no tested restoration) |
| **A.16: Compliance Management** | 5 controls | 60% (GDPR-aware, no audit) |

---

## 5. Gap Analysis: Current vs. ISO 27001 Requirements

### Critical Gaps (Must Address Before Stage 2)

| Control | Gap | Remediation | Timeline |
|---------|-----|-------------|----------|
| **A.5.1: Info Sec Policies** | Draft only; needs board approval | Formalize policy document; owner sign-off | May 2026 |
| **A.5.2: ISMS Scope** | Informal documentation | Document in control procedures manual | May 2026 |
| **A.6.1: Screening** | Not documented | Record solo developer background check | June 2026 |
| **A.6.3: Sec Awareness** | Informal self-training | Establish annual training plan + logs | June 2026 |
| **A.8.5: Encryption** | Optional SQLCipher | Make mandatory by default; document key lifecycle | June 2026 |
| **A.8.3: Monitoring** | Partial logging | Formalize log retention policy (30+ days) | June 2026 |
| **A.11.2: Access Rights** | Manual/informal | Document access matrix; formalize provisioning/deprovisioning | July 2026 |
| **A.13.1: Vendor Mgmt** | SLA informal | Formalize vendor assessment questionnaire; document Hetzner SLA | July 2026 |
| **A.14.1: Incident Response** | Informal procedures | Create incident response playbook; define escalation | July 2026 |
| **A.15.1: Business Continuity** | Untested backups | Conduct quarterly DR test; document results | August 2026 |

### High-Priority Gaps (Address During Stage 1)

| Control | Gap | Remediation |
|---------|-----|-------------|
| **A.7.1: Physical Access** | No documentation of controls | Document Hetzner data center security; map to ISO 27001 |
| **A.9.1: Cryptographic Controls** | No policy | Create cryptography policy; document algorithms (TLS 1.2+, SHA-256, HMAC-SHA256) |
| **A.12.1: Key Management** | Ad hoc env vars | Formalize key lifecycle (generation, storage, rotation, retirement) |
| **A.14.2: Incident Classification** | No triage process | Define severity levels; assign incident owner |
| **A.14.3: Containment** | Ad hoc (circuit breaker) | Formalize containment procedures; document rollback process |
| **A.14.4: Post-Incident Review** | Informal | Schedule monthly incident review; document RCA template |

### Medium-Priority Gaps (Address During Stage 2)

| Control | Gap | Timeline |
|---------|-----|----------|
| **A.6.2: Onboarding** | Not documented | Create onboarding checklist for future employees |
| **A.11.3: Removal of Access** | Manual process | Document deprovisioning procedures |
| **A.11.5: Access Review** | Ad hoc | Schedule quarterly access reviews |
| **A.15.2: DR Testing** | Not scheduled | Plan quarterly backup restoration tests |

---

## 6. Proposed Auditor Qualifications

We are seeking a certification body that:

1. **Is Accredited**
   - Holds UKAS, ISMS, or equivalent ISO 27001 accreditation
   - Current scope includes SaaS/software companies
   - Demonstrates annual audit of own quality system

2. **Has Relevant Experience**
   - 10+ years of ISO 27001 certifications
   - Experience with solo founder / small team organizations
   - Understanding of cloud/SaaS infrastructure (Hetzner, AWS, etc.)
   - Familiarity with Python/Linux environments

3. **Offers Flexible Engagement**
   - Remote-capable (video conference + secure file transfer)
   - Clear pricing for Stage 1 and Stage 2
   - Hybrid approach (kickoff in-person, testing remote)
   - Flexible timing for solo developer

4. **Provides Value-Add Services**
   - ISMS implementation guidance (not just auditing)
   - Remediation recommendations with effort estimates
   - Training on ISO 27001 requirements
   - Post-certification consulting (annual maintenance)

---

## 7. Certification Timeline & Milestones

### Phase 1: Stage 1 Pre-Audit (May 2026)

| Date | Activity | Responsibility |
|------|----------|-----------------|
| May 5-10 | Auditor selection and contract signature | Ahmed |
| May 12 | Stage 1 Audit Kickoff Meeting | Ahmed + Auditor |
| May 12-31 | ISMS scope definition; risk assessment methodology review | Ahmed + Auditor |
| June 1-15 | Gap assessment fieldwork (document review, interviews) | Auditor |
| June 16-30 | Gap assessment report delivery; remediation planning | Auditor → Ahmed |

**Deliverable:** Stage 1 Audit Report (20-30 pages) with gap matrix and remediation roadmap.

### Phase 2: Stage 1 Remediation (June - July 2026)

| Date | Activity | Responsibility |
|------|----------|-----------------|
| June 20 - July 31 | Implement critical controls (encryption, incident response, access control) | Ahmed |
| July 1-15 | Formalize ISMS documentation (policies, procedures, matrices) | Ahmed |
| July 16-31 | Prepare evidence of control implementation (logs, screenshots, configs) | Ahmed |

**Deliverable:** Control evidence package ready for Stage 2 observation.

### Phase 3: Stage 2 Observation Period (August - November 2026)

| Date | Activity | Responsibility |
|------|----------|-----------------|
| Aug 1-15 | Stage 2 Audit Kickoff; observation period begins | Ahmed + Auditor |
| Aug 15 - Nov 15 | Continuous ISMS operation under documented controls (6 months) | Ahmed |
| Sept 1, Oct 1, Nov 1 | Monthly evidence collection (backups, audit logs, incident logs) | Ahmed |
| Oct 15-30 | Internal audit against ISO 27001 (self-audit) | Ahmed |
| Nov 1-15 | Management review and certification readiness assessment | Ahmed + Auditor |

**Deliverable:** Evidence of effective control operation over 6-month period.

### Phase 4: Stage 2 Final Audit & Certification (November - December 2026)

| Date | Activity | Responsibility |
|------|----------|-----------------|
| Nov 16 - Dec 10 | Stage 2 fieldwork (control testing, evidence verification) | Auditor |
| Dec 11-20 | Corrective action plan (if findings exist) | Ahmed |
| Dec 21-31 | Final report issuance; certification decision | Auditor |

**Deliverable:** ISO 27001 Certification (valid for 3 years with annual surveillance audits).

---

## 8. Estimated Budget

### Budget Range

Based on system complexity and auditor experience:

| Auditor Category | Stage 1 | Stage 2 | Total |
|-----------------|---------|---------|-------|
| **Small Boutique** | $5K-$10K | $8K-$15K | $13K-$25K |
| **Mid-Market (UKAS)** | $10K-$15K | $15K-$25K | $25K-$40K |
| **Big 4** | $15K-$25K | $25K-$50K | $40K-$75K |

**Payment Terms:** Preferred = split: 50% Stage 1 deposit, 50% upon Stage 2 completion.

---

## 9. ISMS Documentation Requirements

### 9.1 Mandatory ISMS Documents

We will prepare/maintain the following (provided to auditor):

1. **Information Security Policy** (A.5.1)
   - Scope, objectives, accountability
   - Risk management approach
   - Board/owner approval

2. **Risk Assessment & Treatment Plan** (A.6.1.3)
   - Risk register with asset, threat, likelihood, impact, treatment
   - Risk acceptance criteria and approval

3. **ISMS Procedures Manual** (A.5.2)
   - Overview of 14 domains + 93 controls
   - Implemented vs. not-applicable decisions with justification
   - Responsibility matrix

4. **Access Control Matrix** (A.11.2)
   - Users, roles, permissions
   - Provisioning and deprovisioning procedures

5. **Cryptography Policy** (A.9)
   - Approved algorithms (TLS 1.2+, SHA-256, AES-256, etc.)
   - Key lifecycle (generation, storage, rotation, retirement)
   - Certificate management

6. **Change Management Procedures** (A.8.5)
   - Change request form
   - Approval gates
   - Testing and rollback procedures
   - Git-based evidence

7. **Incident Response Playbook** (A.14)
   - Detection and classification
   - Escalation and containment procedures
   - Communication plan
   - Post-incident review template

8. **Business Continuity & Disaster Recovery Plan** (A.15)
   - RTO/RPO targets
   - Backup procedures and testing schedule
   - Restoration process
   - Quarterly DR test results

9. **Vendor Risk Assessment Questionnaire** (A.13.1)
   - Hetzner security assessment
   - Third-party provider SLAs (Exa, Tavily, etc.)
   - Contractual security requirements

10. **Internal Audit Report** (A.14.6)
    - Annual audit scope and findings
    - Corrective action tracking

### 9.2 Evidence of Control Implementation

We will collect and organize:

1. **Authentication & Access Control**
   - API key generation and rotation logs
   - Access matrix with approval signatures
   - Failed authentication logs (sample, PII-redacted)

2. **Encryption**
   - TLS certificate details (issuer, validity, algorithm)
   - SQLCipher configuration (if enabled)
   - Key generation and storage evidence

3. **Backup & Recovery**
   - Daily backup logs (timestamps, file sizes)
   - Quarterly DR test results (date, duration, success/failure)
   - Backup restoration procedure (documented step-by-step)

4. **Audit Logging**
   - Sample audit logs (PII-redacted)
   - HMAC signature verification results
   - Log retention policy and implementation

5. **Change Management**
   - Git commit history (demonstrates change tracking)
   - Change request approvals (for critical changes)
   - Test results before production deployment

6. **Incident Response**
   - Incident logs (severity, detection date, containment date, resolution date)
   - Corrective action tracking
   - Post-incident review templates

7. **Risk Assessment**
   - Risk register with current risk levels and treatment status
   - Quarterly risk review results

8. **Training & Awareness**
   - Annual security training logs (solo developer self-certification)
   - Security awareness materials (policy reminders, security alerts)

---

## 10. Expected Audit Findings & Remediation

### 10.1 Likely Stage 1 Findings

**Critical (Major Non-Conformity):**
- ISMS scope not formally documented
- Risk assessment methodology not established
- Information security policy not formally approved

**High (Minor Non-Conformity):**
- Encryption key lifecycle not documented
- Incident response playbook not formalized
- Business continuity plan not tested

**Medium (Observation):**
- Solo developer segregation of duties limited
- RBAC framework incomplete
- Monitoring and alerting not fully implemented

### 10.2 Remediation Plan & Timeline

We will address all Stage 1 findings before Stage 2 begins (by end of July 2026):

| Finding | Severity | Remediation | Owner | Deadline |
|---------|----------|-------------|-------|----------|
| ISMS scope not documented | Critical | Create ISMS scope statement + control matrix | Ahmed | May 31 |
| Risk assessment methodology | Critical | Define risk assessment framework (ISO 31000 aligned) | Ahmed | June 15 |
| Information security policy | Critical | Formalize policy document; owner approval | Ahmed | June 30 |
| Encryption key lifecycle | High | Document key generation, storage, rotation, retirement | Ahmed | July 15 |
| Incident response playbook | High | Create incident severity matrix + response procedures | Ahmed | July 30 |
| Business continuity testing | High | Schedule + conduct quarterly DR test | Ahmed | August 31 |
| RBAC framework | Medium | Extend role model beyond tier-based access | Ahmed | July 31 |

---

## 11. Auditor Access & Support

### 11.1 Information Provided to Auditor

- **Source Code:** GitHub repository (loom - public/private as needed)
- **Infrastructure Access:** SSH to Hetzner server (read-only)
- **Database Access:** SQLite audit logs and config (read-only)
- **API Access:** Test Bearer token for tool testing
- **Documentation:** All policies, procedures, and evidence (Google Drive link or secure upload)

### 11.2 On-Site Support

- **Kickoff Meeting:** In-person or video (preferred: video for flexibility)
- **Technical Walkthroughs:** Explanation of architecture, control flow, logging
- **Audit Interviews:** 2-3 hours for Stage 1; 4-6 hours for Stage 2 (solo developer available)
- **Evidence Gathering:** 2-3 business days for requested documentation

### 11.3 Communication & Response Times

- **Primary Contact:** Ahmed Adel (ahmedalderai22@gmail.com, +1 [phone on request])
- **Response Time Target:** 24 hours for questions; 2 business days for documentation
- **Communication Method:** Email, Slack, video conference (Zoom/Teams)
- **Availability:** 9 AM - 5 PM CET, Monday - Friday (flexible for auditor timezone)

---

## 12. Post-Certification Roadmap

### 12.1 Annual Surveillance Audits

After initial certification:
- **Years 2 & 3:** Annual surveillance audits (shorter scope, 2-4 weeks each)
- **Year 4:** Recertification audit (full 3-year recertification cycle)
- **Continuous Monitoring:** Monthly risk reviews and incident tracking

### 12.2 ISMS Improvement Plan

Post-certification enhancements:
- **Q1 2027:** Implement automated CI/CD testing and GitHub Actions
- **Q2 2027:** Deploy Prometheus monitoring and Slack alerting
- **Q3 2027:** Complete OAuth2 integration for multi-user support
- **Q4 2027:** Extend RBAC with formal role definitions

### 12.3 Related Certifications

ISO 27001 will position us for:
- **SOC2 Type II:** Concurrent audit (May - Sep 2026)
- **EU AI Act Conformity Assessment:** Body of Designated Notified Body (late 2026)
- **GDPR Compliance Certification:** Optional (Q1 2027)
- **FedRAMP:** Roadmap for U.S. government sales (2027+)

---

## 13. Contact Information & Proposal Submission

**Point of Contact:**

- **Name:** Ahmed Adel Bakr Alderai
- **Title:** Founder/Principal Developer
- **Email:** ahmedalderai22@gmail.com
- **Phone:** +1 (available upon request)
- **GitHub:** @aadel (loom repository)

**Proposal Submission:**

Please send your ISO 27001 certification proposal to: ahmedalderai22@gmail.com

**Proposal Should Include:**

1. Auditor credentials and UKAS/accreditation details
2. Relevant ISO 27001 experience (client list, certifications issued)
3. Proposed Stage 1 and Stage 2 approach and timeline
4. Pricing breakdown (Stage 1, Stage 2, surveillance audits)
5. References (2-3 clients certified in past 2 years)
6. Availability for kickoff meeting (May 12-16, 2026 preferred)

**Proposal Deadline:** May 31, 2026

**Budget Range:** $25K - $40K (all-inclusive for Stage 1, Stage 2, and first surveillance audit)

---

## 14. Appendices

### Appendix A: ISO 27001:2022 Annex A Control Summary

**14 Domains, 93 Controls:**

| Domain | # Controls | Target Implementation | Notes |
|--------|-----------|----------------------|-------|
| A.5: Organizational Controls | 6 | Policy, scope, objectives, responsibility | Policy formalization planned May 2026 |
| A.6: People Controls | 7 | Screening, awareness, training, discipline | Annual self-training for solo dev |
| A.7: Physical Controls | 9 | Data center security, equipment, access | Hetzner responsibility; partial audit |
| A.8: Network & System Controls | 14 | Encryption, authentication, monitoring, logging | 70% implemented; formalization needed |
| A.9: Cryptographic Controls | 4 | Algorithms, certificate, key storage | Policy and lifecycle documentation planned |
| A.10: Physical & Logical Storage | 4 | Cache, backup, retention, removal | Procedures formalized; testing needed |
| A.11: Identity & Access Management | 9 | Authentication, authorization, access rights, review | 60% implemented; RBAC extension planned |
| A.12: Cryptographic Key Management | 3 | Key generation, storage, rotation, retirement | Lifecycle documentation planned |
| A.13: Supplier Relations | 2 | Vendor assessment, agreements | Hetzner assessment planned; others noted |
| A.14: Information Security Incident Management | 7 | Detection, classification, response, post-review | Procedures being formalized |
| A.15: Business Continuity Management | 4 | Continuity planning, DR testing, recovery | DR plan in place; testing needed |
| A.16: Compliance Management | 5 | Legal, regulatory, intellectual property | GDPR-aware; formal compliance audit |

---

### Appendix B: Sample ISMS Scope Statement (Draft)

```
INFORMATION SECURITY MANAGEMENT SYSTEM (ISMS) SCOPE

Organization: Loom Research Tools
Principal: Ahmed Adel Bakr Alderai
Effective Date: May 4, 2026
Certification Target: ISO 27001:2022

IN SCOPE:
- Loom MCP Research Server (all 220+ tools)
- API authentication layer (Bearer token verification)
- Audit logging infrastructure (JSONL + HMAC-SHA256)
- Cache management (content-hash, daily directories)
- Session management (persistent browser sessions)
- Rate limiting (free/pro/enterprise tiers)
- Configuration management (config.json, environment variables)
- Hetzner infrastructure (shared responsibility model)
- GitHub repository (source code)

OUT OF SCOPE:
- Third-party search providers (Exa, Tavily, etc.) - their own security responsibility
- Customer applications using Loom API
- Pre-acquisition information security of external contributors
- Cryptographic algorithm design (we use standard protocols)

EXCLUSIONS & JUSTIFICATIONS:
- Customer data: Not stored by Loom; customers responsible for securing their usage
- Vendor cryptography: Third-party libraries (cryptography, pydantic) trust established via package registry verification

RESPONSIBILITY MAP:
- Management: Ahmed Adel Bakr Alderai (solo)
- Operations: Ahmed Adel (server administration, backups, monitoring)
- Security: Ahmed Adel (policy, incident response, training)
- Compliance: Ahmed Adel (audit logs, risk assessment, vendor management)
- Hetzner: Physical infrastructure, network security, DDoS mitigation

APPROVAL:
Approved by: Ahmed Adel Bakr Alderai
Date: May 4, 2026
Review Frequency: Annual or upon significant organizational change
```

---

**End of ISO 27001 RFP Document**

---

**Document Version:** 1.0  
**Last Updated:** May 4, 2026  
**Author:** Ahmed Adel Bakr Alderai  
**Classification:** Business-Confidential
