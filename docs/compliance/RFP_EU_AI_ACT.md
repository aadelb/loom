# Request for Proposal (RFP) for EU AI Act Compliance & Conformity Assessment

**Date of Issue:** May 4, 2026  
**Target Conformity Assessment:** Q4 2026 (October - December)  
**Assessment Timeline:** 4 months (August - November 2026)

---

## 1. Executive Summary

Loom Research Tools is seeking a **Designated Notified Body (DNB)** or qualified third-party conformity assessment provider to evaluate our AI system for compliance with the **European Union AI Act (2024/1689)**.

We require support for:
- **Article 43 Conformity Assessment:** Third-party evaluation of high-risk AI system against Article 6 classification
- **Documentation Review:** Compliance with Articles 10-15 (transparency, risk management, human oversight)
- **Conformity Report:** Assessment of high-risk AI system across all applicable requirements
- **EU AI Act Technical File:** Documentation package for regulatory submission

This is a **high-risk AI system** under Article 6 (biometric identification, critical infrastructure monitoring, dual-use intelligence gathering).

---

## 2. About Loom & AI System Scope

### 2.1 Organization Profile

- **Name:** Loom Research Tools
- **Owner:** Ahmed Adel Bakr Alderai
- **Classification:** Solo developer / Independent contractor
- **EU AI Act Status:** Controller of high-risk AI system (mixed AI/human-in-the-loop research tool)

### 2.2 AI System Description

**System Name:** Loom MCP Research Server v2.0  
**Category:** High-risk AI system under Article 6  
**Deployment:** EU-based (Hetzner, Germany)  
**Access:** API-based via Bearer token authentication  
**Users:** Security researchers, compliance teams, AI safety researchers, law enforcement (potential)

**AI Capabilities:**

1. **Model Profiling Tool** (ai_safety.py)
   - Fingerprint large language models (GPT-4, Claude, Gemini, etc.)
   - Identify model capabilities and behavior patterns
   - Detect capability obfuscation or hidden behaviors
   - **Risk:** Could enable adversarial attacks on AI systems

2. **Bias & Fairness Probing** (ai_safety.py)
   - Test AI models for demographic bias (gender, race, religion, disability)
   - Probe for fairness issues in hiring, lending, criminal justice domains
   - Measure bias amplification across model generations
   - **Risk:** Dual-use - can identify or amplify bias

3. **Prompt Injection Testing** (ai_safety.py)
   - Test AI systems for prompt injection vulnerabilities
   - Evaluate jailbreak effectiveness against safety filters
   - Map model vulnerability surface
   - **Risk:** Enables attacks on deployed AI systems

4. **Safety Filter Mapping** (ai_safety.py)
   - Reverse-engineer AI safety mechanisms
   - Identify filter bypass techniques
   - Document safety control weaknesses
   - **Risk:** Publicly exposes safety vulnerabilities

5. **Adversarial Robustness Assessment** (ai_safety_extended.py)
   - Test AI adversarial resistance to perturbed inputs
   - Evaluate model stability under distribution shift
   - Measure robustness degradation with attack intensity
   - **Risk:** Can reduce AI system resilience

6. **Hallucination Benchmarking** (ai_safety_extended.py)
   - Benchmark AI hallucination rates across domains
   - Identify knowledge gaps and false confidence areas
   - Test factuality across generations
   - **Risk:** Can reveal unreliability of AI outputs

7. **Compliance Checking Tool** (ai_safety.py)
   - Audit AI system for EU AI Act compliance
   - Check transparency documentation
   - Verify risk management implementation
   - **Risk:** System itself is subject to assessment

**Broader System Context:**

Loom exposes 220+ research and intelligence tools, of which 7 are AI-specific. The system is used for:
- **Legitimate Purposes:** Security research, compliance testing, AI safety evaluation, threat intelligence
- **Dual-Use Concerns:** Could be misused for adversarial attacks on AI systems, privacy violations, or disinformation
- **Intelligence Gathering:** Darkweb monitoring, leak scanning, biometric fingerprinting (21+ darkweb/OSINT tools)

---

## 3. Regulatory Scope & Risk Classification

### 3.1 Article 6 High-Risk Classification

**Loom is classified as high-risk under Article 6 because:**

| Criterion | Applicability | Justification |
|-----------|---------------|---------------|
| **Biometric Identification (Art. 6.1a)** | Partial | Includes tools for fingerprinting humans (browser fingerprinting, facial recognition metadata extraction) |
| **Critical Infrastructure (Art. 6.1b)** | Yes | Tools probe and test critical AI systems (LLMs powering critical services) |
| **Law Enforcement (Art. 6.1c)** | Yes | Designed for law enforcement threat intelligence gathering; darkweb monitoring |
| **Justice & Democratic Process (Art. 6.1d)** | Partial | Could influence electoral security via disinformation detection/generation tools |
| **Migration, Asylum, Border (Art. 6.1e)** | Limited | Not directly applicable; borderline inclusion of identity tools |
| **Employment & Education (Art. 6.1f)** | Yes | Career intelligence tools (job signal detection, resume analysis, deception job scanning) |
| **Dual-Use Concern (Recital 6)** | High | Mix of attack/defense tools with high dual-use potential |

**Determination:** **HIGH-RISK under Article 6** → Subject to full conformity assessment and technical file documentation.

### 3.2 Applicable Articles & Requirements

**Mandatory Compliance (Articles 10-15):**

| Article | Requirement | Loom Status | Target Implementation |
|---------|-------------|------------|----------------------|
| **10: Risk Management** | Document risk management system (Art. 10.1-10.4) | Partial | Formalize Q2 2026 |
| **11: Data Quality & Governance** | Ensure data quality; document governance | Partial | Expand Q2 2026 |
| **12: Documentation & Records** | Technical file for conformity assessment | In progress | Complete by Q3 2026 |
| **13: Transparency Requirements** | Provide notices to users about AI system | Planned | Implement Q2 2026 |
| **14: Human Oversight** | Design for human oversight; don't allow full autonomy | Implemented | Document Q2 2026 |
| **15: Accuracy, Robustness, Cybersecurity** | Test for robustness, accuracy, cybersecurity | Partial | Expand Q2 2026 |

**Prohibited Practices (Article 5):**
- Loom does NOT use social scoring
- Loom does NOT subliminal manipulation or exploitation
- Loom DOES offer transparency + user choice (not prohibited)

---

## 4. Current AI Compliance Controls

### 4.1 Implemented Controls

**A. Risk Management (Article 10)**

| Control | Status | Details |
|---------|--------|---------|
| Risk identification | Partial | Informal risk matrix; needs formalization |
| Risk assessment | Partial | Documented in CLAUDE.md; threats identified (dual-use) |
| Risk mitigation | Implemented | Rate limiting, access control, audit logging |
| Residual risk evaluation | Partial | Not formally documented |
| Risk monitoring | Partial | Manual review; no automated monitoring |
| Risk documentation | Partial | Scattered across code comments and docs |

**B. Data Quality & Governance (Article 11)**

| Control | Status | Details |
|---------|--------|---------|
| Data sourcing | Documented | Multi-provider (Exa, Tavily, GitHub, etc.) |
| Data quality procedures | None | Need to establish baseline quality metrics |
| Data bias assessment | Partial | Some tools test for bias; system bias not assessed |
| Data retention | Documented | 30-day cache retention; audit logs retained |
| Data traceability | Implemented | Content-hash cache allows data source tracking |

**C. Transparency & Documentation (Article 12-13)**

| Control | Status | Details |
|---------|--------|---------|
| Technical file | In progress | 80% complete; needs auditor review |
| User instructions | Implemented | GitHub README + docs/tools-reference.md |
| Transparency notices | Planned | Add API response header "X-Powered-By-AI" |
| Model card | Partial | Tool-level documentation; system-level card needed |
| Limitations & risks | Documented | In CLAUDE.md; needs formal publication |

**D. Human Oversight (Article 14)**

| Control | Status | Details |
|---------|--------|---------|
| Design for oversight | Implemented | All tool calls require explicit user action; no autonomous decisions |
| Explainability | Partial | Tools provide output; explanations sometimes implicit |
| Human override | Implemented | Users can reject AI outputs; no forced compliance |
| Audit trail | Implemented | HMAC-signed audit logs with user accountability |

**E. Accuracy, Robustness & Security (Article 15)**

| Control | Status | Details |
|---------|--------|---------|
| Accuracy testing | Partial | Some tools have ground truth; not systematic |
| Adversarial robustness | Not tested | Need adversarial attack testing |
| Cybersecurity measures | Implemented | TLS, input validation, SSRF prevention, rate limiting |
| Security updates | Manual | Git-based; no automated patching |
| Vulnerability disclosure | Planned | Need responsible disclosure policy |

---

## 5. Regulatory & Compliance Gap Analysis

### Critical Gaps (Must Close Before Conformity Assessment)

| Gap | Article | Risk | Remediation | Timeline |
|-----|---------|------|-------------|----------|
| **Risk management system not formalized** | 10 | Cannot demonstrate risk mitigation | Document risk register with AI-specific threats (dual-use, model attacks, privacy) | Q2 2026 |
| **Data quality procedures missing** | 11 | No assurance of input quality | Establish data quality baseline; document provider selection criteria | Q2 2026 |
| **Technical file incomplete** | 12 | Audit will reject submission | Complete all sections; auditor review; incorporate findings | Q3 2026 |
| **Transparency notices not provided** | 13 | User deception risk | Add AI disclosure in API responses + CLI output | Q2 2026 |
| **Human oversight not documented** | 14 | Appear to have autonomous AI decisions | Document that all decisions require user action; show examples | Q2 2026 |
| **No security assessment** | 15 | Cannot demonstrate cybersecurity | Conduct penetration test + vulnerability assessment | Q2 2026 |

### High-Priority Gaps (Address During Assessment)

| Gap | Article | Remediation |
|-----|---------|-------------|
| Model card missing system-level info | 12 | Create comprehensive technical file with all model names, versions, performance metrics |
| Bias assessment incomplete | 11 | Document bias testing procedures; report results for core tools (LLM integration, bias probing) |
| Adversarial robustness untested | 15 | Conduct adversarial attack testing; document results and mitigation |
| Responsible disclosure process absent | 15 | Create and publish vulnerability disclosure policy |
| User instructions incomplete for AI tools | 13 | Add specific instructions for 7 AI tools; explain risks and limitations |

---

## 6. EU AI Act Technical File (Article 12)

### 6.1 Required Documentation

We will prepare comprehensive technical file with:

1. **Executive Summary**
   - System overview (name, version, provider, purpose)
   - Risk classification and justification
   - Compliance summary

2. **System Description (Art. 10.1)**
   - Detailed description of AI algorithms and models used
   - Input/output specifications
   - Training data sources and composition
   - Model versions and lineage
   - Integration points with human decision-making

3. **Risk Management Plan (Art. 10.1-10.4)**
   - Identified risks (dual-use attacks, privacy, bias, safety)
   - Risk assessment matrix (probability × impact)
   - Risk mitigation measures and their effectiveness
   - Residual risk documentation
   - Continuous monitoring plan

4. **Data Quality & Governance (Art. 11)**
   - Data sourcing procedures
   - Data quality metrics and validation
   - Bias assessment methodology and results
   - Data retention and deletion policies
   - Data lineage and traceability

5. **Transparency & Documentation (Art. 13)**
   - Information provided to users (clear + accessible)
   - Limitations and accuracy metrics
   - Output quality indicators
   - Intended use cases + misuse warnings
   - Performance across demographic groups

6. **Human Oversight & Control (Art. 14)**
   - System design for human decision-making
   - Override/reject mechanisms
   - Explainability features
   - Audit trail and accountability

7. **Accuracy, Robustness & Cybersecurity (Art. 15)**
   - Accuracy metrics (baseline + testing)
   - Adversarial robustness assessment
   - Cybersecurity testing (penetration test, vulnerability assessment)
   - Security controls (TLS, input validation, rate limiting, audit logging)
   - Software bill of materials (SBOM) with dependency versions

8. **Performance Across Groups (Art. 15.4)**
   - Accuracy disaggregated by demographic group (if applicable)
   - Bias measurement across sensitive attributes
   - Performance differential analysis

9. **Management & Competence (Art. 12.3)**
   - AIML competence of development team (solo developer credentials)
   - Training and qualifications
   - Quality assurance processes

10. **Conformity Declaration (Art. 12.4)**
    - Statement that system complies with Articles 10-15
    - Auditor attestation (from DNB)
    - Validity period and conditions

### 6.2 Existing Documentation

We have partially prepared:
- System architecture documentation (CLAUDE.md)
- Tools reference (docs/tools-reference.md)
- API reference (docs/API_REFERENCE.md)
- Safety tools architecture (docs/safety-tools-architecture.md)
- AI safety tools module (src/loom/tools/ai_safety.py)

Gaps to close:
- Formal technical file (consolidate + expand)
- Risk management plan (AI-specific)
- Data quality procedures
- Transparency notices (user-facing)
- Adversarial testing results
- Performance metrics disaggregated by demographic group

---

## 7. Conformity Assessment Process (Article 43)

### 7.1 DNB Responsibilities

We are seeking a DNB or qualified assessment provider to:

1. **Review Submitted Documentation**
   - Evaluate technical file completeness
   - Verify compliance with Articles 10-15
   - Identify gaps and request supplementary information

2. **Assessment Activities**
   - Review risk management procedures
   - Verify data quality governance
   - Test system transparency (check API responses for AI disclosure)
   - Verify human oversight mechanisms (review audit logs)
   - Assess cybersecurity (review penetration test results)
   - Evaluate model accuracy and robustness

3. **Site Visits & Technical Testing (Optional)**
   - On-site demonstration of system operation
   - Tool testing (run sample AI tools with test inputs)
   - Access to server/infrastructure
   - Interview with developer

4. **Reporting**
   - Assessment report with findings (critical/high/medium/low)
   - Conformity statement (if compliant)
   - Recommended corrective actions
   - Conditions of ongoing compliance

5. **Post-Assessment Monitoring (Optional)**
   - Surveillance audits (annual or as-needed)
   - Incident notification procedures
   - Modification assessment if system changes

### 7.2 Assessment Timeline

| Phase | Dates | Duration | Activities |
|-------|-------|----------|------------|
| **Prep** | Jun 2026 | 1 month | Technical file completion; documentation package preparation |
| **DNB Submission** | Jul 1, 2026 | - | Submit technical file to DNB |
| **Initial Review** | Jul 2026 | 2-3 weeks | DNB reviews completeness; requests clarifications |
| **Supplementary Info** | Aug 2026 | 2-4 weeks | Provide responses to DNB questions; additional testing if needed |
| **Assessment** | Aug-Sep 2026 | 4-6 weeks | On-site/remote testing; detailed assessment |
| **Reporting** | Oct 2026 | 2-3 weeks | Draft report; feedback loop on findings |
| **Final Statement** | Nov 2026 | - | Conformity statement issued (if compliant) |

**Target Completion:** November 30, 2026

---

## 8. Risk Management Plan for AI System

### 8.1 Identified High-Risk Threats

**Dual-Use Attack Vectors:**

| Threat | Likelihood | Impact | Mitigation | Residual Risk |
|--------|------------|--------|-----------|----------------|
| **Adversarial attacks on deployed LLMs** | High | Critical | (1) Rate limiting prevents bulk testing; (2) Transparency disclosure warns users; (3) Audit trail enables incident response | Medium |
| **Jailbreak discovery & publication** | Medium | High | (1) Responsible disclosure policy; (2) Private tool access controls; (3) User authentication required | Medium |
| **Privacy violation via model fingerprinting** | Medium | High | (1) Model fingerprinting legitimate security research; (2) Audit logging; (3) Explicit consent required | Medium |
| **Disinformation amplification** | Low-Medium | High | (1) User responsibility; (2) Transparency about tool capabilities; (3) No automatic content generation | Medium |
| **Darkweb misuse** | Medium | High | (1) Terms of service prohibit illegal uses; (2) Rate limiting; (3) User authentication + audit logging | Medium-High |

**System Safety Risks:**

| Threat | Likelihood | Impact | Mitigation | Residual Risk |
|--------|------------|--------|-----------|----------------|
| **Bias amplification via career/hiring tools** | Medium | High | (1) Bias probing tool identifies issues; (2) Documentation of tool limitations; (3) User responsibility warning | Medium |
| **Model collapse or instability** | Low | Medium | (1) Tested across multiple model versions; (2) Graceful error handling; (3) Circuit breaker prevents cascades | Low |
| **Hallucination leading to false confidence** | Medium | Medium | (1) Hallucination benchmarking tool measures rates; (2) Output disclaimers; (3) User interpretation responsibility | Medium |

### 8.2 Mitigation Measures

**Preventive Controls:**
1. Rate limiting (free/pro/enterprise tiers) - prevents bulk adversarial attacks
2. API key authentication - user accountability
3. Access control - tiered feature access based on customer tier
4. Input validation (SSRF prevention, parameter validation)
5. Audit logging (HMAC-signed, tamper-proof)

**Detective Controls:**
1. Error rate monitoring - alerts on unusual patterns
2. Audit log analysis - detect misuse (e.g., repeated jailbreak attempts)
3. Rate limit anomalies - spike detection
4. Incident logging - categorize and track incidents

**Response Controls:**
1. Circuit breaker - automatic rate limit escalation
2. Incident escalation - developer notification
3. User communication - incident transparency
4. Corrective action - remediate root causes

---

## 9. Documentation & Transparency Requirements

### 9.1 User Notices (Article 13)

We will provide users with:

```
API Response Header (for all requests):
X-Powered-By-AI: Loom Research v2.0 | Contains 7 AI tools | See https://loom.ai/transparency

API Response Body (for AI tool calls):
{
  "tool": "research_prompt_injection_test",
  "ai_disclosure": {
    "type": "Generative AI",
    "model_family": "Language Model",
    "risk_level": "High",
    "description": "Tests AI systems for prompt injection vulnerabilities",
    "limitations": "Results may have false positives/negatives; not exhaustive",
    "recommended_use": "Security research, AI safety evaluation, red-teaming",
    "prohibited_use": "Unauthorized testing of third-party systems; illegal access",
    "human_oversight": "All outputs require human interpretation and judgment"
  }
}

CLI Notice (for loom command-line tool):
$ loom ai-safety --tool prompt_injection_test

WARNING: This tool uses AI-powered testing to identify vulnerabilities.
- Results are for security research only
- Confirm findings with additional testing
- Do not use to attack systems you don't own
- See https://loom.ai/ai-tools for full documentation

Documentation (https://loom.ai/ai-tools):
- Tool-level documentation for each of 7 AI tools
- Instructions, examples, limitations, accuracy metrics
- Responsible use guidelines
- Incident reporting contact
```

### 9.2 Model Card (System-Level)

We will create a comprehensive model card documenting:

1. **Model Details**
   - Loom AI system overview
   - Underlying LLM providers (Groq, NVIDIA NIM, DeepSeek, Gemini, Moonshot, OpenAI, Anthropic)
   - Integration method (multi-provider cascade with fallback)
   - Version and release date

2. **Intended Use**
   - Primary use cases (security research, AI safety evaluation)
   - Appropriate users (security researchers, compliance teams)
   - Recommended precautions (human oversight, additional validation)

3. **Limitations**
   - Known accuracy gaps (e.g., accuracy rates per tool)
   - Conditions of degraded performance
   - Model-specific limitations (hallucinations, biases)
   - Scope limitations (English language tools, specific domains)

4. **Ethical Considerations**
   - Dual-use potential (can be misused for attacks)
   - Bias and fairness concerns
   - Privacy implications (data collection, retention)
   - Societal impact

5. **Factor Data**
   - Training data composition (where available)
   - Data bias assessment results
   - Performance metrics by demographic group (if applicable)

6. **Evaluation Results**
   - Accuracy metrics (per tool)
   - Adversarial robustness assessment
   - Cybersecurity testing results

---

## 10. Conformity Assessment Requirements

### 10.1 Auditor Qualifications

We are seeking a DNB or qualified provider that:

1. **Is Accredited**
   - Holds EU AI Act accreditation (Notified Body status) OR
   - Is recognized as qualified conformity assessment provider
   - Current accreditation in force (check NANDO database)
   - Specializes in high-risk AI systems

2. **Has Relevant Experience**
   - 5+ years of AI/ML system conformity assessment
   - Experience with research/security tools
   - Familiarity with high-risk classification criteria
   - Understanding of dual-use AI concerns

3. **Offers Appropriate Scope**
   - Can assess Articles 10-15 requirements
   - Can provide conformity statement (not just report)
   - Optional: surveillance audits (annual)
   - Optional: incident notification assessment

4. **Can Support Solo Developer**
   - Flexible timeline and engagement model
   - Remote-capable (video conference + secure file transfer)
   - Clear communication with non-lawyer developer
   - Reasonable pricing for smaller organization

### 10.2 Required Auditor Deliverables

1. **Assessment Report**
   - Summary of findings (critical/high/medium/low)
   - Detailed assessment of each Article 10-15 requirement
   - Evidence of assessment activities (document review, testing, interviews)
   - Conclusions

2. **Conformity Statement** (if compliant)
   - Statement that AI system complies with Articles 10-15
   - Scope of compliance (what's included/excluded)
   - Valid conditions (deployment environment, user qualifications, version)
   - Validity period (typically 3-5 years)

3. **Audit Trail**
   - Auditor credentials and accreditation details
   - Assessment methodology and scope
   - List of reviewed documents and tested features
   - Sign-off and date

---

## 11. Budget & Engagement Model

### 11.1 Estimated Cost Range

| Assessment Type | Estimated Cost | Timeline |
|-----------------|-----------------|----------|
| **Document Review Only** | €10K-€15K | 4-6 weeks |
| **Document Review + Testing** | €15K-€25K | 8-12 weeks |
| **Full Assessment + Conformity** | €20K-€40K | 10-14 weeks |

**Recommendation:** Full assessment (~€25K-€35K) to obtain conformity statement for market credibility.

### 11.2 Preferred Engagement Model

- **Hybrid:** Kickoff meeting (video); document review (remote); testing (optional on-site or remote demo)
- **Deliverable-based:** Clear pricing for document review, assessment, and final statement
- **Flexible Timeline:** Can begin May 2026; can accommodate developer's schedule (solo, part-time)

### 11.3 Payment Terms

- Preferred: 50% deposit upon engagement; 50% upon delivery of conformity statement

---

## 12. Post-Assessment Roadmap

### 12.1 Conformity Statement Maintenance

Once assessment is complete:
- **Validity:** 3-5 years (until next significant system change)
- **Condition:** System must operate as described in technical file
- **Notification:** Report material changes to DNB (e.g., new AI models, significant feature additions)

### 12.2 Ongoing Compliance

We commit to:
1. **Continuous Risk Management:** Monitor and update risk register quarterly
2. **Incident Reporting:** Notify DNB of safety incidents within 30 days
3. **User Transparency:** Maintain AI disclosure in API responses and documentation
4. **Audit Trail:** Preserve audit logs for 30+ days
5. **Security Updates:** Apply security patches promptly
6. **User Feedback:** Collect and respond to user reports of AI system issues

### 12.3 Surveillance Audits (Optional)

If requested by DNB:
- Annual surveillance audit (3-5 days)
- Focused assessment on risk management and incident tracking
- Audit fee: ~€5K-€10K/year

### 12.4 Related Regulatory Roadmap

Post-AI Act conformity:
- **SOC2 Type II:** Concurrent audit (May-September 2026)
- **ISO 27001:** Concurrent certification (May-November 2026)
- **GDPR Compliance:** Formal audit (Q1 2027)
- **Sector-Specific Regulations:** If targeting law enforcement/critical infrastructure

---

## 13. Risk & Limitations

### 13.1 Inherent Limitations

**This assessment covers:**
- Compliance with EU AI Act Articles 10-15 (risk management, data quality, transparency, human oversight, accuracy/robustness/security)
- System configuration as of assessment date
- Technical controls and procedures

**This assessment does NOT cover:**
- Criminal misuse by bad actors (scope: legitimate research use)
- Adequacy of legal disclaimers (scope: technical compliance only)
- Liability if system is misused by users
- Third-party provider security (Exa, Tavily, etc.)
- Changes made after conformity statement

### 13.2 Conditions of Validity

Conformity statement is valid only if:
1. System is used as described in technical file
2. System is not substantially modified (new AI models, major features)
3. User qualifications and oversight requirements are met
4. Updates and security patches are applied promptly

---

## 14. Contact Information

**Point of Contact:**

- **Name:** Ahmed Adel Bakr Alderai
- **Title:** Founder/Principal Developer
- **Email:** ahmedalderai22@gmail.com
- **Phone:** +1 (available upon request)
- **GitHub:** @aadel (loom repository)

**Proposal Submission:**

Please send your EU AI Act conformity assessment proposal to: ahmedalderai22@gmail.com

**Proposal Should Include:**

1. DNB credentials (Notified Body status or equivalent accreditation)
2. EU AI Act experience (5+ client assessments, reference list)
3. Proposed assessment approach and timeline
4. Pricing breakdown (document review, testing, conformity statement)
5. Sample assessment report from previous engagement (if permitted)
6. Availability for kickoff meeting (June 2026)

**Proposal Deadline:** May 31, 2026

**Budget Range:** €20K-€40K (all-inclusive for full assessment + conformity statement)

---

## 15. Appendices

### Appendix A: EU AI Act Compliance Checklist

**Article 10: Risk Management System**
- [ ] Document identified risks (dual-use, privacy, bias, safety)
- [ ] Assess likelihood and impact
- [ ] Document mitigation measures for each risk
- [ ] Measure mitigation effectiveness
- [ ] Plan continuous monitoring

**Article 11: Data Quality & Governance**
- [ ] Document data sourcing procedures
- [ ] Define data quality metrics
- [ ] Conduct bias assessment
- [ ] Document data retention and deletion
- [ ] Establish data governance framework

**Article 12: Documentation & Technical File**
- [ ] Create comprehensive technical file
- [ ] Document system architecture and AI components
- [ ] Include risk management plan
- [ ] Include data quality procedures
- [ ] Include human oversight design
- [ ] Include cybersecurity measures

**Article 13: Transparency & User Information**
- [ ] Provide clear information about AI use
- [ ] Disclose limitations and risks
- [ ] Explain how to report issues
- [ ] Provide instructions for safe use
- [ ] Document consent mechanisms

**Article 14: Human Oversight**
- [ ] Design for human decision-making (not autonomous)
- [ ] Enable output rejection/override
- [ ] Provide explainability features
- [ ] Maintain audit trail for accountability
- [ ] Train users on proper oversight

**Article 15: Accuracy, Robustness & Cybersecurity**
- [ ] Measure accuracy (baseline + disaggregated)
- [ ] Test adversarial robustness
- [ ] Conduct cybersecurity assessment (pen test, vulnerability scan)
- [ ] Document security controls
- [ ] Plan security updates

---

### Appendix B: Sample Technical File Structure

```
TECHNICAL FILE - LOOM RESEARCH SERVER AI SYSTEM
(EU AI Act Article 12 Compliance Documentation)

1. EXECUTIVE SUMMARY
   1.1 System Overview
   1.2 Risk Classification Justification
   1.3 Compliance Summary
   1.4 Assessment Recommendation

2. SYSTEM DESCRIPTION (Article 10.1)
   2.1 AI System Purpose & Scope
   2.2 AI Components & Models
   2.3 Data Inputs & Outputs
   2.4 Integration with Human Decision-Making
   2.5 Algorithmic Decision-Making (if applicable)

3. RISK MANAGEMENT PLAN (Article 10)
   3.1 Risk Identification & Assessment
   3.2 Risk Mitigation Measures
   3.3 Residual Risk Evaluation
   3.4 Continuous Monitoring & Review

4. DATA QUALITY & GOVERNANCE (Article 11)
   4.1 Training Data Composition
   4.2 Data Quality Procedures
   4.3 Bias Assessment & Mitigation
   4.4 Data Retention & Deletion Procedures

5. TRANSPARENCY & USER INFORMATION (Article 13)
   5.1 User Notices & Disclosure
   5.2 Instructions for Safe Use
   5.3 Explanation of Limitations
   5.4 Feedback & Incident Reporting Mechanisms

6. HUMAN OVERSIGHT (Article 14)
   6.1 System Design for Human Oversight
   6.2 User Decision-Making Authority
   6.3 Override & Rejection Mechanisms
   6.4 Audit Trail & Accountability

7. ACCURACY, ROBUSTNESS & CYBERSECURITY (Article 15)
   7.1 Accuracy Assessment & Metrics
   7.2 Adversarial Robustness Testing
   7.3 Cybersecurity Assessment
   7.4 Security Controls & Incident Response

8. PERFORMANCE ACROSS DEMOGRAPHIC GROUPS (Article 15.4)
   8.1 Disaggregated Accuracy Metrics
   8.2 Bias Measurement & Results
   8.3 Performance Differential Analysis

9. MANAGEMENT & COMPETENCE (Article 12.3)
   9.1 Team Composition & Qualifications
   9.2 AI/ML Competence Evidence
   9.3 Quality Assurance Processes

10. CONFORMITY DECLARATION (Article 12.4)
    10.1 Statement of Compliance
    10.2 Auditor Assessment
    10.3 Conditions & Validity

ATTACHMENTS:
A. System Architecture Diagram
B. Risk Register (detailed)
C. Data Quality Procedures
D. Accuracy Testing Results
E. Adversarial Testing Report
F. Cybersecurity Assessment (Penetration Test)
G. Model Card (detailed)
H. User Documentation (AI-specific)
I. Incident Response Plan
J. Supporting Evidence (certificates, test results, etc.)
```

---

**End of EU AI Act RFP Document**

---

**Document Version:** 1.0  
**Last Updated:** May 4, 2026  
**Author:** Ahmed Adel Bakr Alderai  
**Classification:** Business-Confidential
