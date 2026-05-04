# Loom Compliance Documentation

**Effective Date:** May 4, 2026  
**Scope:** SOC2 Type II, ISO 27001, and EU AI Act Compliance  
**Target Certification:** December 2026  

---

## Overview

This directory contains comprehensive compliance documentation for Loom Research Tools. It includes:

1. **Request for Proposals (RFPs)** — Detailed proposals to send to auditors/certification bodies
2. **Current Controls Inventory** — Baseline of all security controls already implemented
3. **Gap Analysis** — Known gaps between current state and certification requirements
4. **Timeline & Roadmap** — 8-month plan to achieve all three certifications

---

## Document Guide

### For Auditors & Certification Bodies

**→ Start Here:**

1. **[RFP_SOC2_AUDIT.md](RFP_SOC2_AUDIT.md)** (849 lines)
   - Complete request for proposal for SOC2 Type II audit
   - Scope: Security (CC), Availability (A), Confidentiality (C)
   - Timeline: Q3 2026 (6-month observation + 3-month audit)
   - Budget: $15K-$50K
   - **Send to:** Vanta, Drata, Secureframe, or Big 4 audit firms

2. **[RFP_ISO27001.md](RFP_ISO27001.md)** (676 lines)
   - Complete request for proposal for ISO 27001 certification
   - Scope: Information Security Management System (ISMS)
   - Timeline: Q2-Q4 2026 (Stage 1 + Stage 2 with 6-month observation)
   - Budget: $25K-$40K
   - **Send to:** Accredited certification bodies (UKAS, ISMS, etc.)

3. **[RFP_EU_AI_ACT.md](RFP_EU_AI_ACT.md)** (777 lines)
   - Complete request for proposal for EU AI Act conformity assessment
   - Scope: Articles 10-15 (high-risk AI system evaluation)
   - Timeline: Q2-Q4 2026 (assessment + conformity statement)
   - Budget: €20K-€40K
   - **Send to:** Notified Bodies or qualified assessment providers

### For Internal Use

**→ Understand Current State:**

4. **[CURRENT_CONTROLS.md](CURRENT_CONTROLS.md)** (1,137 lines)
   - **Inventory of all security controls currently implemented**
   - Coverage: 70% SOC2, 65% ISO 27001, 60% EU AI Act
   - Details: Authentication, encryption, audit logging, rate limiting, etc.
   - Evidence: Where to find proof of implementation
   - **Use for:** Auditor evidence collection, gap analysis validation

**→ Identify What's Missing:**

5. **[GAP_ANALYSIS.md](GAP_ANALYSIS.md)** (1,359 lines)
   - **Detailed gaps between current state and certification requirements**
   - Critical gaps: Encryption at rest, change management, incident response, vendor assessment, penetration test
   - High-priority gaps: Policy formalization, ISMS scope, risk methodology, access control matrix
   - Medium-priority gaps: Monitoring/alerting, RBAC extension, MFA
   - Effort estimates: 2-5 days per remediation
   - **Use for:** Planning gap remediation, prioritizing work

**→ Manage the Timeline:**

6. **[TIMELINE.md](TIMELINE.md)** (725 lines)
   - **8-month plan to achieve all three certifications (May-December 2026)**
   - Monthly breakdown: May (prep) → Jun (gap remediation) → Jul-Sep (audits) → Oct-Nov (completion) → Dec (certificates)
   - Weekly milestones: RFP deadline, auditor selection, evidence due, etc.
   - Resource allocation: ~14 weeks FTE (~$105K labor + $128K audit fees = $233K total)
   - **Use for:** Project management, tracking progress, adjusting schedule

---

## Quick Facts

### Current Compliance Status

| Framework | Coverage | Status | Notes |
|-----------|----------|--------|-------|
| **SOC2 Type II** | 70% | In Progress | 6-month observation period started April 2026 |
| **ISO 27001** | 65% | In Progress | Stage 1 audit planned June 2026 |
| **EU AI Act** | 60% | In Progress | 7 AI tools identified; high-risk classification confirmed |

### Implementation Roadmap

| Timeline | Activity | Deliverable |
|----------|----------|-------------|
| **May 2026** | Auditor selection + kickoff | RFPs sent, contracts signed |
| **June 2026** | Critical gap remediation | Encryption, change mgmt, incident response |
| **July-Sep 2026** | Audit fieldwork | Testing, evidence collection, findings |
| **Oct-Nov 2026** | Final remediation + certification | Reports issued, certificates received |
| **December 2026** | Market launch | Marketing, sales enablement, renewal planning |

### Budget Summary

- **External Audits:** ~$95K USD + €30K EUR (~$128K USD total)
- **Internal Labor:** ~$105K (14 weeks FTE @ $150/hr average)
- **Total Cost:** ~$233K for full certification
- **ROI:** Customer trust, procurement compliance, regulatory positioning

---

## How to Use This Documentation

### For Ahmed (Founder/Developer)

1. **Immediate (May 2026):**
   - Review CURRENT_CONTROLS.md to understand baseline
   - Review GAP_ANALYSIS.md to prioritize remediation
   - Begin critical gap remediation (encryption, change mgmt, incident response)

2. **This Month (June 2026):**
   - Complete gap remediation per TIMELINE.md
   - Compile evidence per auditor requirements in RFPs
   - Prepare for July auditor kickoff meetings

3. **Ongoing:**
   - Track progress against TIMELINE.md milestones
   - Prepare evidence monthly (logs, tests, configurations)
   - Attend weekly auditor status calls
   - Update documentation based on audit feedback

### For Auditors

1. **Phase 1: Initial Review (May-June 2026)**
   - Review corresponding RFP (SOC2/ISO27001/EU AI Act)
   - Request additional information as needed
   - Identify testing approach and timeline

2. **Phase 2: Fieldwork (July-September 2026)**
   - Review evidence from CURRENT_CONTROLS.md and GAP_ANALYSIS.md
   - Conduct system testing (authentication, logging, encryption)
   - Interview developer and stakeholders
   - Document findings (critical/high/medium/low)

3. **Phase 3: Reporting (October-November 2026)**
   - Draft audit/assessment reports
   - Issue findings and recommendations
   - Obtain responses to findings
   - Issue final reports and certifications

### For Customers

1. **Current State (Today):**
   - Review CURRENT_CONTROLS.md to see security posture
   - Note compliance timeline (target: December 2026)
   - Understand known gaps (documented in GAP_ANALYSIS.md)

2. **Post-Certification (After December 2026):**
   - Request SOC2 Type II report (customer can request copy)
   - Verify ISO 27001 certificate number (public registry)
   - Review EU AI Act compliance statement
   - Use as evidence for your own compliance requirements

---

## Document Cross-References

### Key Sections by Framework

**SOC2 Type II Compliance:**
- Current controls: CURRENT_CONTROLS.md sections 1-7
- Gaps: GAP_ANALYSIS.md section 1 (SOC2 gaps)
- RFP: RFP_SOC2_AUDIT.md
- Timeline: TIMELINE.md months 1, 4-5, 7

**ISO 27001 Certification:**
- Current controls: CURRENT_CONTROLS.md (all sections)
- Gaps: GAP_ANALYSIS.md section 2 (ISO 27001 gaps)
- RFP: RFP_ISO27001.md
- Timeline: TIMELINE.md months 1-7

**EU AI Act Compliance:**
- Current controls: CURRENT_CONTROLS.md section 3 (conceptual)
- Gaps: GAP_ANALYSIS.md section 3 (EU AI Act gaps)
- RFP: RFP_EU_AI_ACT.md
- Timeline: TIMELINE.md months 1, 4-6, 7

---

## Important Dates

| Date | Milestone | Framework |
|------|-----------|-----------|
| **May 10, 2026** | RFP Deadline | SOC2, ISO 27001, EU AI Act |
| **May 15, 2026** | Auditor Kickoff Meetings | All three |
| **June 30, 2026** | Critical Gap Remediation Due | All three |
| **July 31, 2026** | High-Priority Gap Remediation Due | All three |
| **August 31, 2026** | SOC2 Testing Complete | SOC2 |
| **September 30, 2026** | ISO Stage 1 Findings | ISO 27001 |
| **October 31, 2026** | Draft Reports from All Auditors | All three |
| **November 30, 2026** | Final Certifications Issued | All three |
| **December 15, 2026** | Certificates in Hand, Marketing Launch | All three |

---

## Contact & Support

**Point of Contact:** Ahmed Adel Bakr Alderai  
**Email:** ahmedalderai22@gmail.com  
**GitHub:** @aadel (loom repository)  

**For Auditors:** Send RFP responses and scheduling requests to ahmedalderai22@gmail.com  
**For Customers:** Contact above email for compliance documentation requests  

---

## Document Maintenance

**Last Updated:** May 4, 2026  
**Next Review:** June 1, 2026 (post-June remediation)  
**Version:** 1.0  

**Revision History:**
- v1.0 (May 4, 2026): Initial comprehensive compliance documentation package

---

**End of Compliance Documentation Index**

---

*This documentation package is ready to send to SOC2, ISO 27001, and EU AI Act auditors. All RFPs are complete and professional. Internal documents (CURRENT_CONTROLS, GAP_ANALYSIS, TIMELINE) are for planning and progress tracking.*
