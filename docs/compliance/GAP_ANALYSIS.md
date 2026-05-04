# Gap Analysis: Loom vs. SOC2 Type II / ISO 27001 / EU AI Act Requirements

**Analysis Date:** May 4, 2026  
**Scope:** Compliance readiness for three frameworks  
**Overall Maturity:** 65% (documented processes; awaiting formal audit validation)

---

## Executive Summary

**Current State:**
- 70% of SOC2 Type II controls implemented
- 65% of ISO 27001 controls implemented  
- 60% of EU AI Act requirements implemented

**Critical Gaps (Must close before audit):**
1. Encryption at rest (optional, not mandatory)
2. Formal change management approval process
3. Incident response playbook (procedures exist, not formalized)
4. Vendor risk assessment documentation
5. External security assessment (pen test)
6. Data classification policy

**Timeline to Certification:** 6-8 months (May 2026 - December 2026)

---

## 1. SOC2 Type II Gaps

### 1.1 Critical Gaps (Pre-Audit Remediation Required)

#### Gap 1: Encryption at Rest (Optional, Not Mandatory)

**Current State:**
- SQLite databases use optional SQLCipher encryption (feature flag: `USE_SQLCIPHER=true`)
- Cache files stored in `~/.cache/loom/` with file permissions (644) but no encryption
- Audit logs in `~/.loom/audit/` HMAC-signed but not encrypted

**SOC2 Requirement:**
- CC7.2: Systems are protected against unauthorized access via encryption

**Risk:** If server is physically stolen or filesystem is compromised, data could be exposed.

**Remediation:**
```
Timeline: Q2 2026 (2 weeks)
Effort: 1-2 days

Steps:
1. Make SQLCipher mandatory (set USE_SQLCIPHER=true by default)
2. Enable filesystem encryption (dm-crypt on Hetzner, or encrypt at application level)
3. Document encryption key lifecycle (generation, rotation, retirement)
4. Test encrypted database restore
```

**Evidence to Collect:**
- SQLCipher configuration in code
- Encryption key management documentation
- Successful backup/restore with encrypted database

---

#### Gap 2: Manual Change Management (No Formal Approval Process)

**Current State:**
- All changes via git commits
- No formal change request (CR) document
- No pre-deployment approval checklist
- Solo developer = self-approval only

**SOC2 Requirement:**
- CC7.3: Changes to systems are reviewed, approved, tested, and implemented

**Risk:** No formal audit trail of change approvals; changes could be undocumented.

**Remediation:**
```
Timeline: Q2 2026 (1-2 weeks)
Effort: 3-5 days

Steps:
1. Create change request template (CHANGE_REQUEST.md)
2. Require CR for production deployments
3. Document approval checklist (testing, review, verification)
4. Maintain change log (git + CR document)
5. Define rollback procedures
```

**Change Request Template:**
```markdown
# Change Request [CR-001]

## Summary
[Brief description of change]

## Type
- [ ] Configuration
- [ ] Code
- [ ] Infrastructure
- [ ] Documentation

## Risk Level
- [ ] Low
- [ ] Medium
- [ ] High

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] No new security warnings (mypy, ruff)

## Approval
- [ ] Developer (self): Ahmed Adel
- [ ] Date: YYYY-MM-DD

## Deployment
- [ ] Backup taken
- [ ] Rollback plan documented
- [ ] Deployment executed
- [ ] Verification successful

## Post-Deployment
- [ ] Audit logs checked
- [ ] Error monitoring checked
- [ ] Performance metrics normal
- [ ] Incident reports: None
```

**Evidence to Collect:**
- Completed change requests (past 3 months)
- Git log with change summaries
- Testing results (pytest output)
- Deployment logs

---

#### Gap 3: No Formal Incident Response Playbook

**Current State:**
- Circuit breaker and timeout protections in place
- Error handling and logging implemented
- Rate limit anomaly detection available
- No formalized incident response steps or escalation procedures

**SOC2 Requirement:**
- CC8.1: Incidents are detected and reported

**Risk:** Incident response is ad hoc; no formal triage or communication process.

**Remediation:**
```
Timeline: Q2 2026 (1-2 weeks)
Effort: 3-5 days

Steps:
1. Define incident severity levels (Critical/High/Medium/Low)
2. Create incident detection procedures (monitoring, alerting)
3. Document incident response workflow
4. Define escalation (who to notify, when)
5. Create post-incident review template (RCA)
```

**Incident Severity Matrix:**
```
CRITICAL (page on-call immediately):
- Service unavailable (0-5% uptime)
- Data loss or corruption
- Security breach confirmed
- Revenue-impacting outage

HIGH (respond within 1 hour):
- Degraded performance (50-90% uptime)
- Rate limiting triggered
- Error rate spike (>10%)
- Potential security issue

MEDIUM (respond within 4 hours):
- Minor errors (<5% of requests fail)
- Configuration drift detected
- Cache miss causing slowdown

LOW (routine review):
- Informational alerts
- Performance optimization opportunities
- Non-critical warnings
```

**Incident Response Workflow:**
```
1. DETECT: Error rate spike, rate limit hit, circuit breaker open
2. CLASSIFY: Assign severity (Critical/High/Medium/Low)
3. ACKNOWLEDGE: Developer notified (email, alert)
4. ASSESS: Determine impact and root cause (preliminary)
5. CONTAIN: Stop bleeding (circuit breaker, rate limit, manual shutdown)
6. COMMUNICATE: Notify stakeholders (if customer-impacting)
7. REMEDIATE: Fix root cause (code patch, config change, etc.)
8. VERIFY: Test fix, deploy, monitor
9. REVIEW: Post-incident RCA (within 24 hours)
10. DOCUMENT: Update runbooks with lessons learned
```

**Evidence to Collect:**
- Incident response playbook (document)
- Sample incident logs (redacted)
- Post-incident review template
- Examples of resolved incidents

---

#### Gap 4: Vendor Risk Assessment Missing

**Current State:**
- Hetzner SLA reviewed (99.5% availability)
- Other provider APIs documented (Exa, Tavily, etc.)
- No formal vendor risk assessment questionnaire
- No vendor security reviews documented

**SOC2 Requirement:**
- CC9.1: Relationships with suppliers and partners are clearly defined

**Risk:** Vendor failure could impact Loom; no contractual security requirements.

**Remediation:**
```
Timeline: Q2 2026 (1-2 weeks)
Effort: 2-3 days

Steps:
1. Create vendor risk assessment questionnaire
2. Document Hetzner security controls + SLA
3. Review other critical vendors (LLM providers, search providers)
4. Maintain vendor inventory with risk level
5. Establish vendor review schedule (annual)
```

**Vendor Assessment Questionnaire:**
```
VENDOR RISK ASSESSMENT

Vendor Name: [e.g., Hetzner, Exa]
Category: [Compute, Search, LLM, etc.]
Criticality: [Critical, Important, Optional]
Risk Level: [High, Medium, Low]

INFORMATION SECURITY:
[ ] Vendor provides SOC2/ISO 27001 certification
[ ] Vendor has documented security controls
[ ] Vendor conducts regular security testing
[ ] Vendor has incident response plan
[ ] Vendor discloses known vulnerabilities

DATA PROTECTION:
[ ] Data encrypted in transit (TLS 1.2+)
[ ] Data encrypted at rest (if stored)
[ ] Data retention policy documented
[ ] GDPR/privacy compliance confirmed
[ ] DPA available (if needed)

AVAILABILITY:
[ ] SLA documented (uptime target)
[ ] Backup and disaster recovery plan
[ ] RTO/RPO defined
[ ] Support escalation procedure

FINANCIAL:
[ ] Vendor financially stable (credit check)
[ ] Pricing sustainable
[ ] No hidden fees
```

**Vendor Inventory:**
```
CRITICAL VENDORS (would impact service if down):
- Hetzner (compute/storage): SOC2 Type II certified, 99.5% SLA
- NVIDIA NIM (LLM fallback): No SLA, best-effort
- Groq (primary LLM): API availability tracked

IMPORTANT VENDORS:
- Exa (search): Semantic search, alternative available
- Tavily (search): Alternative Firecrawl
- GitHub (source code): Private repo, mirrored backup available

OPTIONAL VENDORS:
- Stripe (billing): Only if subscription feature enabled
- Joplin (notes): Optional integration
```

**Evidence to Collect:**
- Vendor risk assessment questionnaire (completed)
- Hetzner SOC2 report (or certification)
- Vendor SLA documentation (with effective dates)
- Vendor contact information (security team, escalation)

---

#### Gap 5: No External Security Assessment (Penetration Test)

**Current State:**
- Code review and testing implemented
- Security checklist before commits
- No third-party penetration test

**SOC2 Requirement:**
- CC6.1: An organization's system is protected against unauthorized access

**Risk:** Hidden vulnerabilities could exist; no external validation of security controls.

**Remediation:**
```
Timeline: Q2 2026 (4-6 weeks)
Effort: 1 week (for management), 2 weeks (vendor work)

Steps:
1. Identify penetration testing vendor
2. Define scope (application, infrastructure, API)
3. Schedule testing (2-3 days)
4. Review findings
5. Remediate vulnerabilities
6. Obtain final report
```

**Penetration Test Scope:**
```
IN SCOPE:
- MCP server (port 8787)
- API authentication and authorization
- Input validation (SSRF, injection)
- Rate limiting bypass attempts
- Session management
- Error handling and information leakage
- Encryption mechanisms (TLS, at-rest if enabled)
- Audit logging system

OUT OF SCOPE:
- Third-party providers (Hetzner, Exa, etc.)
- Physical security
- Social engineering
- Denial of service attacks (unless testing circuit breaker)
```

**Expected Findings & Remediation:**
```
CRITICAL (must fix immediately):
- Unauthenticated access to tools (unlikely, but test)
- SQL injection / command injection (unlikely, Pydantic validates all input)
- Unencrypted sensitive data transmission (unlikely, TLS enforced)

HIGH (must fix before production):
- Weak authentication (test bearer token brute-force)
- Broken authorization (test tier enforcement)
- Sensitive information in logs (test PII scrubbing)

MEDIUM (should fix):
- Cache poisoning attacks
- Timing-based information leakage
- Error message information disclosure

LOW (nice-to-have):
- Performance optimizations
- Defense-in-depth recommendations
- Security hardening suggestions
```

**Evidence to Collect:**
- Penetration test report (from vendor)
- Remediation plan for findings
- Evidence of fixes applied
- Final verification report

---

### 1.2 High-Priority Gaps (During SOC2 Observation)

#### Gap 6: Data Classification Policy

**Current State:**
- Data informally classified (public/internal/confidential/secret)
- No formal data classification scheme
- No retention or disposal procedures documented

**SOC2 Requirement:**
- CC6.2: Data is classified based on sensitivity

**Remediation:**
```
Timeline: Q2 2026 (1 week)
Effort: 2-3 days

Steps:
1. Define classification levels (Public/Internal/Confidential/Secret)
2. Assign classification to each data type (code, config, logs, cache, sessions)
3. Document retention and disposal procedures
4. Map to encryption and access control requirements
```

**Data Classification Matrix:**

| Data Type | Classification | Encryption | Retention | Disposal |
|-----------|-----------------|------------|-----------|----------|
| Source code (GitHub) | Public | N/A | Permanent | Archive to S3 on deletion |
| API documentation | Public | N/A | Permanent | N/A |
| Tool outputs (cache) | Internal | Optional | 30 days | Auto-delete after 30 days |
| Audit logs | Confidential | Optional (HMAC signed) | 90+ days | Encrypted archive after 90 days |
| Configuration (API keys) | Secret | Mandatory (env var) | Until rotation | Secure destroy on rotation |
| Session data | Internal | Optional (SQLCipher) | Session lifetime | Auto-delete on session close |
| User API key | Secret | Mandatory (env var) | Indefinite | Secure destroy on key revocation |

**Evidence to Collect:**
- Data classification policy document
- Data inventory (all data types and their classification)
- Retention and disposal schedule
- Encryption status by classification

---

#### Gap 7: No Tested Disaster Recovery Procedure

**Current State:**
- Daily Hetzner snapshots available
- Code in GitHub
- Backup procedure documented but not tested

**SOC2 Requirement:**
- A2.1: Infrastructure, data, and information systems are recovered in a timely manner

**Remediation:**
```
Timeline: Q3 2026 (2 days per test)
Effort: 1 day setup, 0.5 days per quarterly test

Steps:
1. Document recovery procedure (step-by-step)
2. Conduct quarterly DR test
3. Measure actual RTO/RPO
4. Document results and lessons learned
5. Update procedure based on test results
```

**DR Test Procedure:**
```
QUARTERLY DISASTER RECOVERY TEST

Objective: Verify we can restore full Loom system from backups

Test Steps:
1. Provision new Hetzner instance (mimic production)
2. Restore system from latest snapshot
3. Verify all data integrity (audit logs, cache, sessions)
4. Restart loom-server service
5. Run smoke tests (test all major tools)
6. Measure restore time (RTO)
7. Verify data freshness (RPO)
8. Clean up test instance

Success Criteria:
- RTO: < 15 minutes
- RPO: < 1 hour (all critical data recovered)
- All tools functional
- Audit logs intact and verifiable

Documentation:
- Test date and duration
- Issues encountered
- Remediation steps taken
- Approved for next production update? Yes/No
```

**Evidence to Collect:**
- DR test results (quarterly)
- Recovery runbook (documented procedure)
- Time measurements (RTO/RPO)
- Issues and resolutions

---

### 1.3 Medium-Priority Gaps (Post-Certification)

#### Gap 8: Monitoring & Alerting Not Fully Implemented

**Current State:**
- Error logging implemented
- Rate limiting tracking available
- No Prometheus metrics or Slack alerting

**SOC2 Requirement:**
- CC7.2: Monitoring systems detect anomalies

**Remediation:**
```
Timeline: Q3 2026
Effort: 3-5 days

Steps:
1. Deploy Prometheus for metrics collection
2. Define key metrics (latency, throughput, error rate, rate limit hits)
3. Configure alerting thresholds
4. Set up Slack integration for alerts
5. Create monitoring dashboard
```

**Key Metrics to Monitor:**
```
Performance:
- Request latency (p50, p95, p99)
- Throughput (requests/second)
- Tool execution time

Errors:
- Error rate (% of requests failing)
- Error type distribution
- Tool-specific error rates

Rate Limiting:
- Rate limit hits (by tier)
- Spike detection (sudden increase)

Availability:
- Uptime (target: 99.5%)
- Downtime incidents
- Circuit breaker state
```

**Alert Thresholds:**
```
CRITICAL:
- Service unavailable (0 requests for 5 minutes)
- Error rate > 50%
- Circuit breaker OPEN for > 10 minutes

HIGH:
- Error rate > 10%
- Latency p99 > 30 seconds
- Rate limit threshold exceeded

MEDIUM:
- Latency p95 > 10 seconds
- Cache hit rate < 30%
- Unusual tool usage pattern
```

---

## 2. ISO 27001 Gaps

### 2.1 Critical Gaps (Stage 1 Audit - Must Address Before Stage 2)

#### Gap 1: Information Security Policy (Draft Only)

**Current State:**
- Draft policy in CLAUDE.md
- Not formally approved by management (solo developer)
- Doesn't cover all 14 ISO 27001 domains

**ISO 27001 Requirement:**
- A.5.1: The organization shall establish an information security policy

**Remediation:**
```
Timeline: May 2026 (1-2 weeks)
Effort: 3-5 days

Steps:
1. Expand draft policy to cover all 14 domains
2. Include risk management approach and risk appetite
3. Document accountability and responsibilities
4. Get management approval (developer signature)
5. Publish and communicate to stakeholders
```

**Policy Structure:**
```
INFORMATION SECURITY POLICY

1. EXECUTIVE SUMMARY
   - Organization name and scope
   - Security vision and mission

2. ORGANIZATIONAL CONTEXT
   - Organizational structure
   - Relevant stakeholders
   - Legal and regulatory context (GDPR, EU AI Act, SOC2, ISO 27001)

3. SECURITY GOVERNANCE
   - Organizational roles and responsibilities
   - Security responsibilities of management and staff
   - Resource allocation for security

4. RISK MANAGEMENT
   - Risk management approach (ISO 31000 aligned)
   - Risk appetite and acceptance criteria
   - Risk assessment and treatment process

5. INFORMATION CLASSIFICATION
   - Data classification scheme (Public/Internal/Confidential/Secret)
   - Classification assignment criteria
   - Handling procedures per classification

6. ACCESS CONTROL
   - Authentication methods (API keys, future: OAuth2, MFA)
   - Authorization model (tier-based, feature flags)
   - Access rights management and review

7. CRYPTOGRAPHY
   - Encryption in transit (TLS 1.2+)
   - Encryption at rest (SQLCipher)
   - Key management lifecycle

8. INCIDENT MANAGEMENT
   - Incident detection and reporting
   - Incident classification and response
   - Incident communication and escalation

9. BUSINESS CONTINUITY
   - Business continuity objectives (RTO/RPO)
   - Backup and recovery procedures
   - Testing and validation

10. COMPLIANCE
    - Legal and regulatory requirements (GDPR, EU AI Act)
    - Compliance monitoring
    - Audit and review

11. SUPPLIER MANAGEMENT
    - Vendor selection criteria
    - Vendor security assessments
    - Vendor agreement and SLAs

12. SECURITY AWARENESS
    - Security training and awareness
    - Incident reporting procedures
    - Security communication

13. APPROVAL AND IMPLEMENTATION
    - Policy approval (management signature + date)
    - Effective date
    - Review frequency (annual)
    - Revision history
```

**Evidence to Collect:**
- Approved information security policy document
- Management signature/approval
- Policy distribution record
- Acknowledgment from personnel

---

#### Gap 2: ISMS Scope Not Formally Documented

**Current State:**
- System scope informally defined (Loom MCP server, 220+ tools)
- No formal scope statement with inclusions/exclusions
- No documented business justification

**ISO 27001 Requirement:**
- A.4.3: Determine the scope of the ISMS

**Remediation:**
```
Timeline: May 2026 (3-5 days)
Effort: 1-2 days

Steps:
1. Formally define ISMS boundaries
2. Document what's included (in-scope) and excluded (out-of-scope)
3. Justify exclusions
4. Document shared responsibilities (e.g., Hetzner)
5. Get management approval
```

**ISMS Scope Statement Template:**
```
ISMS SCOPE STATEMENT

Organization: Loom Research Tools
Scope Definition Date: May 2026
Approval Date: [TBD]

EXECUTIVE SUMMARY:
The ISMS covers all information and systems within Loom Research Tools' direct control, 
including the MCP server, API, audit logging, cache, and session management systems.

IN SCOPE:
- Loom MCP Research Server (Python application)
- API key authentication layer
- All 220+ MCP tools
- Audit logging system (HMAC-signed)
- Cache management (content-hash)
- Session management (persistent browser sessions)
- Configuration management
- GitHub source code repository
- Developer workstation (for code development)

OUT OF SCOPE:
- Third-party search/scraping providers (Exa, Tavily, etc.) - their own responsibility
- Third-party LLM providers (Groq, NVIDIA NIM, etc.) - their own responsibility
- Hetzner data center infrastructure - Hetzner's responsibility (though we audit SLAs)
- Customer applications using Loom API - customer's responsibility
- Pre-acquisition security of external contributors - not applicable (solo developer)

SHARED RESPONSIBILITY:
- Hetzner provides: Network TLS, DDoS mitigation, data center physical security
- Loom provides: Application-level encryption, authentication, audit logging

RATIONALE FOR EXCLUSIONS:
- Third-party providers: Out of scope as they control their own security
- Data center: Physical security is Hetzner's responsibility (shared responsibility model)
- Customer applications: Customers responsible for securing their own systems

ISMS PERIMETER DIAGRAM:
[Include network diagram showing boundaries]

APPROVAL:
Approved by: Ahmed Adel Bakr Alderai (Organization Management)
Approval Date: [TBD]
Effective Date: [TBD]
Review Frequency: Annually or upon significant organizational change
```

**Evidence to Collect:**
- ISMS scope statement (approved document)
- System architecture diagram (showing boundaries)
- Management approval signature
- Justification for exclusions

---

#### Gap 3: Risk Assessment Methodology Not Established

**Current State:**
- Risk register in CLAUDE.md (informal)
- No structured risk assessment framework
- No documented probability/impact matrix

**ISO 27001 Requirement:**
- A.6.1.3: Risk assessment methodology

**Remediation:**
```
Timeline: June 2026 (1 week)
Effort: 2-3 days

Steps:
1. Select risk assessment framework (ISO 31000 aligned)
2. Define probability and impact scales
3. Create risk matrix (probability × impact = overall risk)
4. Document risk appetite (acceptance criteria)
5. Perform formal risk assessment (asset/threat/vulnerability/impact)
```

**Risk Assessment Methodology:**

```
RISK ASSESSMENT METHODOLOGY

Framework: ISO 31000 (Risk Management) aligned
Assessment Approach: Qualitative (supported by quantitative metrics where available)

PROBABILITY SCALE (Annual):
5 = Almost Certain (>80% chance annually)
4 = Likely (50-80%)
3 = Possible (20-50%)
2 = Unlikely (5-20%)
1 = Remote (<5%)

IMPACT SCALE:
5 = Catastrophic (Loss of service > 1 month, major data loss, legal liability)
4 = Critical (Service down 1-7 days, significant data exposure, regulatory fine)
3 = Major (Service down 1-24 hours, partial data exposure, customer impact)
2 = Moderate (Service degradation < 1 hour, minimal data exposure, limited impact)
1 = Minor (Operational inconvenience, no data exposure, no external impact)

RISK MATRIX:
┌─────────────────────────────────────────┐
│ RISK MATRIX (Probability × Impact)      │
├─────┬──────┬──────┬──────┬──────┬───────┤
│ P\I │  1   │  2   │  3   │  4   │  5    │
├─────┼──────┼──────┼──────┼──────┼───────┤
│  5  │ MED  │ HIGH │ HIGH │ CRIT │ CRIT  │
│  4  │ LOW  │ MED  │ HIGH │ HIGH │ CRIT  │
│  3  │ LOW  │ MED  │ MED  │ HIGH │ HIGH  │
│  2  │ LOW  │ LOW  │ MED  │ MED  │ HIGH  │
│  1  │ LOW  │ LOW  │ LOW  │ MED  │ MED   │
└─────┴──────┴──────┴──────┴──────┴───────┘

RISK ACCEPTANCE CRITERIA:
CRITICAL: Unacceptable; must remediate immediately
HIGH: Unacceptable without mitigation; develop treatment plan
MEDIUM: Acceptable with mitigation; monitor regularly
LOW: Acceptable; monitor periodically

RISK TREATMENT OPTIONS:
1. Mitigate: Reduce risk to acceptable level (implement controls)
2. Accept: Accept residual risk (documented approval)
3. Avoid: Stop the activity (eliminate risk)
4. Transfer: Move risk to third party (e.g., insurance, SLA)
```

**Sample Risk Assessment:**

```
RISK REGISTER (SAMPLE ENTRIES)

Risk 1: Unauthorized Access to API
- Asset: MCP Server
- Threat: Brute force attack on API key
- Vulnerability: Weak key entropy (if default key used)
- Probability: 3 (Possible; depends on key complexity)
- Impact: 4 (Critical; full system access)
- Inherent Risk: HIGH (3 × 4 = 12)

Mitigations:
- Strong API key generation (minimum 32 characters, random)
- Rate limiting (10 req/min free tier, 60 pro, 300 enterprise)
- Audit logging (all auth attempts)
- Residual Risk: MEDIUM (after mitigations: 2 × 4 = 8)
- Owner: Ahmed Adel
- Review Date: Q3 2026

Risk 2: Data Loss (Cache)
- Asset: Research cache (~/.cache/loom/)
- Threat: Accidental deletion or storage failure
- Vulnerability: No replicated backups
- Probability: 2 (Unlikely; Hetzner has redundancy)
- Impact: 2 (Moderate; cache is non-critical, re-fetchable)
- Inherent Risk: LOW (2 × 2 = 4)

Mitigations:
- Daily Hetzner snapshots
- Content-hash cache (re-fetch if needed)
- Quarterly DR testing
- Residual Risk: LOW (2 × 1 = 2)
- Owner: Ahmed Adel
- Review Date: Q3 2026

Risk 3: Service Unavailability (Rate Limiting DDoS)
- Asset: MCP Server availability
- Threat: Attacker uses rate limiting to block legitimate users
- Vulnerability: Rate limiter doesn't distinguish attack traffic
- Probability: 3 (Possible; low effort attack)
- Impact: 3 (Major; service degraded)
- Inherent Risk: MEDIUM (3 × 3 = 9)

Mitigations:
- Circuit breaker (stops cascading failures)
- Hetzner DDoS protection (blocks bulk traffic)
- Monitoring and alerts (detect anomalies)
- Residual Risk: MEDIUM (2 × 3 = 6)
- Owner: Ahmed Adel
- Review Date: Q3 2026
```

**Evidence to Collect:**
- Risk assessment methodology document
- Probability/impact matrix (with definitions)
- Risk register (all identified risks with assessment)
- Risk treatment plans (for each risk)
- Management approval of risk appetite

---

#### Gap 4: Incident Response Plan Not Formalized

**Current State:**
- Circuit breaker and timeouts implemented
- Informal response procedures
- No formal incident severity levels or escalation

**ISO 27001 Requirement:**
- A.16.1: Incident handling procedures

**Remediation:**
```
Timeline: July 2026 (1 week)
Effort: 3-5 days

Steps:
1. Define incident severity levels
2. Create incident response workflow
3. Document escalation procedures
4. Create incident log template
5. Schedule quarterly incident response tabletop exercises
```

**See: SOC2 Gap 3 (Incident Response Playbook) for detailed remediation.**

---

#### Gap 5: Backup and Disaster Recovery Testing Not Conducted

**Current State:**
- Daily Hetzner snapshots
- Backup procedure documented
- No tested restoration procedure

**ISO 27001 Requirement:**
- A.17.1: Business continuity planning and testing

**Remediation:**
```
Timeline: Q3 2026 (quarterly, 1 day per test)
Effort: 1 day setup, 0.5 days per quarterly test

Steps:
1. Document recovery procedure
2. Conduct quarterly DR test
3. Measure actual RTO/RPO
4. Document results
5. Update procedures based on lessons learned
```

**See: SOC2 Gap 7 (Tested DR Procedure) for detailed remediation.**

---

### 2.2 High-Priority Gaps (Stage 1 & 2)

#### Gap 6: Access Control Matrix Not Documented

**Current State:**
- API key authentication implemented
- Tier-based rate limiting in place
- No formal access control matrix

**ISO 27001 Requirement:**
- A.9.2: User access management

**Remediation:**
```
Timeline: June 2026 (1 week)
Effort: 2-3 days

Steps:
1. Create access control matrix (users × resources × permissions)
2. Document provisioning/deprovisioning procedures
3. Schedule quarterly access reviews
4. Document role definitions (if RBAC extended)
```

**Access Control Matrix Template:**

```
ACCESS CONTROL MATRIX

USER / ROLE | API KEY | HEALTH | FREE TOOLS | PRO TOOLS | ADMIN | NOTES
------------|---------|--------|-----------|-----------|-------|-------
Developer (Ahmed) | [key] | ✓ | ✓ | ✓ | ✓ | Full access
Test Account 1 | [key] | ✓ | ✓ | ✗ | ✗ | Free tier
Researcher (Pro) | [key] | ✓ | ✓ | ✓ | ✗ | Pro tier
Enterprise Cust | [key] | ✓ | ✓ | ✓ | ✗ | Enterprise tier

RESOURCE DEFINITIONS:
- Health: /health endpoint (basic availability check)
- Free Tools: 100+ tools (limited rate limit: 10/min, 100/day)
- Pro Tools: All 220+ tools (higher limit: 60/min, 10K/day)
- Admin: Server configuration, audit log access, rate limit override

TIER LIMITS:
Free: 10 req/min, 100 req/day
Pro: 60 req/min, 10K req/day
Enterprise: 300 req/min, unlimited/day
```

**Evidence to Collect:**
- Access control matrix (documented)
- Provisioning/deprovisioning procedures
- Quarterly access review results
- Role definitions (if applicable)

---

#### Gap 7: Encryption Key Lifecycle Policy Missing

**Current State:**
- API keys stored in environment variables
- AUDIT_SECRET key stored in environment
- No formal key lifecycle documentation

**ISO 27001 Requirement:**
- A.10.1: Cryptographic key management

**Remediation:**
```
Timeline: July 2026 (1 week)
Effort: 2-3 days

Steps:
1. Document key generation procedure
2. Document key storage requirements
3. Document key rotation schedule
4. Document key retirement/destruction
5. Implement key versioning (optional, for audit key)
```

**Key Lifecycle Policy:**

```
CRYPTOGRAPHIC KEY MANAGEMENT POLICY

KEY TYPES & LIFECYCLES:

1. API Key (LOOM_API_KEY)
   - Generation: Use OpenSSL: `openssl rand -hex 32`
   - Storage: Environment variable (file permissions 600)
   - Rotation: Every 12 months or upon suspicion of compromise
   - Retirement: Destroy after 12 months + 30-day retention
   - Versioning: Not required (only one active key)

2. Audit Signing Key (LOOM_AUDIT_SECRET)
   - Generation: Use OpenSSL: `openssl rand -hex 64`
   - Storage: Environment variable (file permissions 600)
   - Rotation: Every 12 months
   - Retirement: Archive old key (in case audit log verification needed)
   - Versioning: Maintain key history (v1, v2, etc.) for signature verification

3. Third-Party API Keys (Groq, NVIDIA NIM, DeepSeek, etc.)
   - Generation: Via provider's dashboard
   - Storage: Environment variable (file permissions 600)
   - Rotation: Per provider recommendation (typically 12 months)
   - Retirement: Revoke in provider console, destroy local copy
   - Versioning: Not required

4. SQLCipher Database Password (if enabled)
   - Generation: Use OpenSSL: `openssl rand -hex 32`
   - Storage: Environment variable (file permissions 600)
   - Rotation: Every 12 months
   - Retirement: Re-encrypt database with new key, destroy old key
   - Versioning: Not required (only one password per database)

KEY ROTATION PROCEDURE:

For LOOM_API_KEY:
1. Generate new key: `openssl rand -hex 32`
2. Set new key in .env
3. Test new key works
4. Document old key (last 8 chars) and rotation date
5. Discard old key (shred if available)
6. Update environment on server: update .env, restart service
7. Verify new key works on production

For LOOM_AUDIT_SECRET:
1. Generate new key: `openssl rand -hex 64`
2. Version it as v2 in environment
3. Code update: Support both v1 (old) and v2 (new) for verification
4. Set v2 as primary for all new audit entries
5. Keep v1 for verifying old entries
6. After 90 days (retention period), can delete v1

KEY STORAGE:
- Development: .env.local (git-ignored, never committed)
- Production: /etc/loom/.env (file permissions 600, root owner only)
- Backup: Hetzner secret manager (future enhancement)
- Backup: Not backed up in standard backups (keys stay on live instance)

KEY DESTRUCTION:
- Use `shred -vfz -n 10 <file>` to securely delete
- For environment variables: Set to empty, restart process
- For database passwords: Use ALTER DATABASE command to change
```

**Evidence to Collect:**
- Key lifecycle policy document
- Key generation evidence (procedure followed)
- Key rotation log (dates and old key identifiers)
- Audit trail (when keys were rotated)

---

## 3. EU AI Act Gaps

### 3.1 Critical Gaps (Before Conformity Assessment)

#### Gap 1: Risk Management System Not Formalized

**Current State:**
- Informal risk identification (documented in CLAUDE.md)
- No formal risk assessment for AI system
- No documented mitigation measures

**EU AI Act Requirement:**
- Article 10: Risk management system

**Remediation:**
```
Timeline: Q2 2026 (2 weeks)
Effort: 3-5 days

Steps:
1. Identify all AI-specific risks (dual-use, bias, hallucination, safety)
2. Assess likelihood and impact
3. Document mitigation measures
4. Measure mitigation effectiveness
5. Plan continuous monitoring
```

**AI-Specific Risk Assessment:**

```
RISK 1: Jailbreak Discovery & Misuse

Asset: Loom MCP Research Server (AI tools)
Threat: Attacker uses prompt_injection_test tool to find jailbreaks, then uses findings to attack other AI systems
Vulnerability: Tool is public; jailbreak findings could be weaponized
Probability: 3 (Possible; researchers regularly find jailbreaks)
Impact: 4 (Critical; enables attacks on deployed LLMs)
Inherent Risk: HIGH (3 × 4 = 12)

Mitigations:
- Transparency disclosure: Warn users about dual-use potential
- Rate limiting: Prevents bulk jailbreak testing
- Audit logging: Tracks all test attempts
- Responsible disclosure: Users encouraged to report findings to model providers
- Residual Risk: MEDIUM (2 × 4 = 8)

Evidence:
- User documentation (include jailbreak warnings)
- Rate limit configuration (logged)
- Audit logs (sample of tool invocations)

RISK 2: Bias Amplification via Career Tools

Asset: Career intelligence tools (job_signals, career_intel, salary_synthesizer)
Threat: Tool amplifies existing hiring bias, leading to discriminatory outcomes
Vulnerability: Training data may contain historical biases; tool could reinforce them
Probability: 3 (Possible; bias is common in recruitment data)
Impact: 4 (Critical; employment discrimination, legal liability)
Inherent Risk: HIGH (3 × 4 = 12)

Mitigations:
- Documentation: Explain tool limitations and bias risks
- Bias probing tool: Users can test their own systems for bias
- Human oversight: All hiring decisions require human judgment
- User guidance: Recommend human review of tool outputs
- Residual Risk: MEDIUM (2 × 4 = 8)

Evidence:
- Tool documentation (bias warnings)
- Bias probing tool availability
- User instructions (emphasize human judgment)

RISK 3: Model Fingerprinting for Adversarial Targeting

Asset: Model fingerprinting tool
Threat: Attacker fingerprints a competitor's model, then designs targeted adversarial attacks
Vulnerability: Fingerprinting reveals model capabilities and weaknesses
Probability: 2 (Unlikely; requires sophistication)
Impact: 3 (Major; model performance degradation)
Inherent Risk: MEDIUM (2 × 3 = 6)

Mitigations:
- Rate limiting: Prevents bulk model testing
- Authentication: Only authorized researchers can access
- Transparency: Document that tool reveals model capabilities (by design)
- Intended use: Legitimate security research only
- Residual Risk: MEDIUM (1 × 3 = 3)

Evidence:
- Rate limit configuration
- Authentication controls
- Tool documentation
```

---

#### Gap 2: Technical File Incomplete

**Current State:**
- ~80% of technical file draft
- Missing: Formal risk management plan, data quality procedures, human oversight documentation

**EU AI Act Requirement:**
- Article 12: Technical documentation and record-keeping

**Remediation:**
```
Timeline: Q3 2026 (4-6 weeks)
Effort: 1 week to consolidate + audit review

Steps:
1. Consolidate all documentation into single technical file
2. Complete missing sections (risk, data quality, oversight)
3. Add performance metrics and disaggregated accuracy
4. Obtain auditor review and feedback
5. Incorporate findings
```

**Technical File Sections to Complete:**
- Article 10 Risk Management: (draft to finalized)
- Article 11 Data Quality: (create data quality procedures)
- Article 14 Human Oversight: (document design decisions)
- Article 15 Accuracy/Robustness: (add testing results)

---

#### Gap 3: Data Quality Procedures Not Documented

**Current State:**
- Data sources documented (Exa, Tavily, GitHub, etc.)
- No formal data quality assessment
- No bias measurement methodology

**EU AI Act Requirement:**
- Article 11: Data quality and governance

**Remediation:**
```
Timeline: Q2 2026 (2 weeks)
Effort: 3-5 days

Steps:
1. Document data sourcing procedures
2. Define data quality metrics (accuracy, completeness, representativeness)
3. Establish data quality baseline
4. Conduct bias assessment (for demographic-sensitive tools)
5. Document data retention and deletion
```

**Data Quality Framework:**

```
DATA QUALITY ASSESSMENT

LLM Provider Data (for all 7 AI tools using LLMs):
- Source: Groq, NVIDIA NIM, DeepSeek, Gemini, Moonshot, OpenAI, Anthropic
- Quality Metrics: Model accuracy reported by provider, known limitations
- Bias Assessment: Tested by Loom bias_probing tool (results in docs)
- Retention: No customer data retained; LLM response ephemeral
- Deletion: All LLM responses deleted after use; no storage

Research Cache Data (for scraping/search tools):
- Source: Third-party providers (Exa, Tavily, GitHub, etc.)
- Quality Metrics: Content freshness (from provider), relevance scoring
- Bias Assessment: Limited (content quality dependent on source)
- Retention: 30 days (automatic cleanup)
- Deletion: Automatic via cache clear tool

Audit Log Data:
- Source: All MCP tool invocations (internal)
- Quality Metrics: Complete (all invocations logged), accurate timestamps
- Bias Assessment: Not applicable (audit data)
- Retention: 90+ days (configurable)
- Deletion: Manual or automatic via retention policy

Session Data:
- Source: Browser interactions (Playwright)
- Quality Metrics: Session validity, browser version
- Bias Assessment: Not applicable
- Retention: Session lifetime (typically minutes to hours)
- Deletion: Automatic on session close
```

---

#### Gap 4: No Adversarial Testing Results

**Current State:**
- Conceptual understanding of adversarial attacks
- No formal adversarial robustness testing
- No published attack results

**EU AI Act Requirement:**
- Article 15: Accuracy, robustness, and cybersecurity

**Remediation:**
```
Timeline: Q3 2026 (4-6 weeks)
Effort: 1 week (conduct testing), 1 week (document)

Steps:
1. Identify adversarial attack vectors (jailbreaks, prompt injection, etc.)
2. Conduct adversarial testing against Loom tools
3. Measure robustness (success rate of attacks)
4. Document findings and mitigations
5. Incorporate into technical file
```

**Adversarial Testing Plan:**

```
ADVERSARIAL ROBUSTNESS TESTING

Tool: research_prompt_injection_test
Attack Vector: Bypassing LLM safety filters
Testing Method:
- Run 100+ known jailbreaks against target models
- Measure success rate (% of jailbreaks that succeed)
- Compare baseline model to Loom's filtered variant
- Document filter effectiveness

Expected Results:
- Baseline model: 30-50% jailbreak success rate (typical)
- Loom tool: Should accurately report success rates
- Residual risk: Tool reveals vulnerabilities (by design)

Tool: research_bias_probe
Attack Vector: Finding hidden biases
Testing Method:
- Run bias probes against multiple LLM models
- Measure demographic parity gap (variance across groups)
- Document bias amplification across model generations
- Report correlation with training data bias

Expected Results:
- Baseline model: 5-15% demographic parity gap (typical)
- Loom tool: Should accurately measure and report
- Residual risk: Tool exposes biases (can be weaponized)

Tool: research_llm_summarize (LLM-based)
Attack Vector: Adversarial inputs causing hallucinations
Testing Method:
- Feed adversarial prompts (contradictory, nonsensical)
- Measure hallucination rate (% of outputs containing false info)
- Compare across different input perturbations
- Document model robustness

Expected Results:
- Baseline model: 10-20% hallucination rate on adversarial inputs
- Loom tool: Should handle gracefully (return error or low-confidence)
- Residual risk: Tool may produce unreliable outputs (documented)
```

---

## 4. Summary Table: All Gaps

| Framework | Gap | Severity | Timeline | Effort | Remediation |
|-----------|-----|----------|----------|--------|-------------|
| **SOC2** | Encryption at rest | Critical | Q2 | 2 days | Make SQLCipher mandatory |
| | Change management | Critical | Q2 | 5 days | Formal CR process |
| | Incident response | Critical | Q2 | 5 days | Playbook + procedures |
| | Vendor assessment | Critical | Q2 | 3 days | Risk questionnaire |
| | Penetration test | Critical | Q2 | 5 days (vendor) | External assessment |
| | Data classification | High | Q2 | 3 days | Classification matrix |
| | DR testing | High | Q3 | 1 day/quarter | Quarterly test |
| | Monitoring | Medium | Q3 | 5 days | Prometheus + alerts |
| **ISO 27001** | Information policy | Critical | May | 5 days | Formalize policy |
| | ISMS scope | Critical | May | 2 days | Scope statement |
| | Risk methodology | Critical | Jun | 3 days | Framework definition |
| | Incident response | Critical | Jul | 5 days | Playbook (same as SOC2) |
| | DR testing | Critical | Q3 | 1 day/quarter | Quarterly test |
| | Access matrix | High | Jun | 3 days | RACI + provisioning |
| | Key management | High | Jul | 3 days | Lifecycle policy |
| **EU AI Act** | Risk management | Critical | Q2 | 5 days | AI-specific risk assessment |
| | Technical file | Critical | Q3 | 1 week | Consolidate + audit |
| | Data quality | Critical | Q2 | 5 days | Quality framework |
| | Adversarial testing | Critical | Q3 | 2 weeks | Testing + results |
| | Transparency notices | High | Q2 | 3 days | User disclosures |
| | Performance metrics | High | Q3 | 1 week | Accuracy measurement |

---

**End of Gap Analysis Document**

---

**Document Version:** 1.0  
**Last Updated:** May 4, 2026  
**Classification:** Internal Use / Compliance Documentation
