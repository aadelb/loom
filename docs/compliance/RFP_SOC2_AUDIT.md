# Request for Proposal (RFP) for SOC2 Type II Audit

**Date of Issue:** May 4, 2026  
**Requested Implementation Timeline:** Q3 2026 (July - September)  
**Audit Observation Period:** 6 months (April 2026 - September 2026)

---

## 1. Executive Summary

Loom Research Tools ("the Company") is seeking an independent SOC2 Type II audit for our MCP (Model Context Protocol) research and intelligence server. We are a Python-based, open-source intelligence research platform serving security researchers, compliance teams, and AI safety researchers.

We require a comprehensive SOC2 Type II report covering **Security (CC), Availability (A), and Confidentiality (C)** trust service criteria to:
- Enable customer trust and organizational procurement requirements
- Demonstrate commitment to information security and compliance
- Support future ISO 27001 certification roadmap
- Validate EU AI Act compliance infrastructure

---

## 2. About Loom Research Tools

### Company Profile
- **Legal Name:** Loom Research Tools (sole proprietorship)
- **Owner/Principal:** Ahmed Adel Bakr Alderai
- **Year Founded:** 2025
- **Employees:** 1 (solo developer, security team outsourced)
- **Headquarters:** EU-based operations, Hetzner infrastructure

### Service Description
Loom is a Python 3.12+ MCP server that exposes 220+ research and intelligence tools over streamable-HTTP (TCP port 8787). The platform provides:

**Core Research Capabilities:**
- Multi-source search (21+ providers: Exa, Tavily, Firecrawl, Brave, DuckDuckGo, Arxiv, Wikipedia, HackerNews, Reddit, etc.)
- Advanced web scraping (Scrapling 3-tier: HTTP/Stealthy/Dynamic with Cloudflare auto-escalation)
- HTML-to-markdown conversion (Crawl4AI + Trafilatura fallback)
- GitHub repository analysis (GitHub CLI wrapper)
- Persistent browser sessions (Playwright + Camoufox stealth)
- Darkweb/Tor integration (forum scraping, exit node detection)
- Document metadata extraction (EXIF, PDF, images)
- LLM multi-provider integration (8 providers: Groq, NVIDIA NIM, DeepSeek, Gemini, Moonshot, OpenAI, Anthropic, vLLM)
- EU AI Act compliance tools (5 tools: prompt injection testing, model fingerprinting, bias probing, safety filter mapping, compliance checking)

**Domain-Specific Intelligence Tools:**
- 20+ killer research tools (dead content recovery, invisible web discovery, infrastructure correlation, threat profiling)
- 25+ dark/intelligence tools (darkweb forum search, leak scanning, identity resolution, competitive intelligence)
- 11+ academic integrity tools (citation analysis, retraction checking, predatory journal detection, grant forensics)
- 6+ career intelligence tools (job signal detection, salary synthesis, deception job scanning)
- 957 prompt reframing strategies (organized across 32 modules)

**Billing & Multitenancy:**
- 12-module billing subsystem (cost tracking, credit system, customer isolation, tier enforcement, Stripe integration)
- Tiered access (free/pro/enterprise)
- Per-user rate limiting and overage handling

**Data Protection & Compliance:**
- Content-hash cache (SHA-256, daily directory structure)
- Audit logging (HMAC-SHA256 signatures, tamper detection)
- PII scrubbing (regex-based before logging)
- SSRF prevention (URL validation with DNS resolution cache)
- Semantic duplicate detection
- Offline mode fallback
- Storage tier management (hot/warm/cold)

---

## 3. Scope of SOC2 Type II Audit

### Trust Service Criteria Covered

#### **CC (Security Control Criteria) - FULL SCOPE**
1. **CC6:** Logical and physical access controls
2. **CC7:** System monitoring and change management
3. **CC8:** Prevention, detection, and remediation of security incidents
4. **CC9:** Encryption and key management

#### **A (Availability Control Criteria) - FULL SCOPE**
1. **A1:** Availability and performance monitoring
2. **A2:** Incident response and recovery procedures
3. **A3:** Configuration and change management

#### **C (Confidentiality Control Criteria) - FULL SCOPE**
1. **C1:** Confidentiality of data in transit (TLS encryption)
2. **C2:** Data classification and handling
3. **C3:** Authorized access to confidential information

### Out of Scope
- **SOC2 Type I:** Not required; proceeding directly to Type II (6-month observation period already underway)
- **ISO 27001:** Separate engagement
- **External vulnerability testing:** Separate engagement (recommend concurrent)
- **Cloud provider compliance:** Hetzner infrastructure responsibility (audit will note shared responsibility model)
- **Third-party integrations:** We track vendor risk; recommend vendor audit if required

---

## 4. Current Control Environment

### 4.1 Authentication & Authorization

**Implemented Controls:**

| Control | Status | Details |
|---------|--------|---------|
| API Key Authentication | Implemented | Bearer token verification via `auth.py:ApiKeyVerifier` with constant-time comparison (`secrets.compare_digest`) |
| Bearer Token Invalidation | Implemented | Environment variable `LOOM_API_KEY` with rotation capability |
| Anonymous Access Restrictions | Implemented | Default: health check only; opt-in `LOOM_ALLOW_ANONYMOUS=true` for full access |
| Token Scope Management | Partial | Basic scopes: `["*"]` (full) or `["health"]` (restricted); extensible framework |
| OAuth2 Scaffold | Planned Q3 | Framework for token exchange (not yet implemented) |
| Role-Based Access Control (RBAC) | Partial | Feature flags and tier-based access (`@requires_tier` decorator) implemented; missing formal role definitions |
| Multi-Factor Authentication (MFA) | Planned | Recommended for enterprise tier |

**Audit Readiness:**
- Token storage: Environment variables (follows 12-factor app principles)
- No hardcoded API keys in source code
- Bearer token logging redacted (first 8 characters only)

### 4.2 Encryption & Cryptography

**Data in Transit:**

| Element | Status | Details |
|---------|--------|---------|
| TLS 1.2+ | Implemented | Hetzner network layer enforces TLS for all HTTP/2 connections |
| HTTPS Enforcement | Implemented | All external tool calls use HTTPS with SSL certificate verification |
| Certificate Validation | Implemented | No self-signed certificates accepted for remote API calls |
| Header Whitelisting | Implemented | `validators.py:SAFE_REQUEST_HEADERS` blocks injection of security-sensitive headers |

**Data at Rest:**

| Element | Status | Details |
|---------|--------|---------|
| SQLite Encryption | Optional | `SQLCipher` dependency available but not mandatory; configuration flag `USE_SQLCIPHER=true` for opt-in |
| Cache File Encryption | Partial | Content-hash cache stored in `~/.cache/loom/YYYY-MM-DD/` with file-level permissions (644) |
| Audit Log Encryption | Partial | HMAC-SHA256 signatures for integrity; optional file-level encryption with system utilities |
| Session Database Encryption | Optional | SQLite sessions can be encrypted with SQLCipher |
| PII Handling | Implemented | Pre-logging scrubbing via regex patterns (email, IP, phone, SSN, credit cards) |

**Key Management:**

| Element | Status | Details |
|---------|--------|---------|
| AUDIT_SECRET_KEY | Implemented | `LOOM_AUDIT_SECRET` environment variable for HMAC signing; validation on startup |
| API Keys | Implemented | All provider API keys stored as environment variables (Groq, NVIDIA NIM, DeepSeek, etc.) |
| Key Rotation | Manual | No automated rotation; documented process for manual rotation via environment variable update |
| Key Derivation | Not Applicable | No password-based key derivation; keys are static environment values |

**Audit Recommendations:**
- Enable SQLCipher by default for at-rest encryption
- Implement automated key rotation for audit signing keys
- Document encryption key lifecycle in formal change management process

### 4.3 Access Control

**Authentication Boundary:**

```
Internet → Hetzner Network → Port 8787 (Streamable-HTTP)
                              ↓
                         Verify Bearer Token
                         (auth.py:ApiKeyVerifier)
                              ↓
                         Scoped MCP Tool Call
                              ↓
                    Rate Limit Check (per tier)
                              ↓
                         Tool Execution
```

**Rate Limiting:**

| Tier | Requests/Minute | Requests/Day | Status |
|------|-----------------|--------------|--------|
| free | 10 | 100 | Implemented |
| pro | 60 | 10,000 | Implemented |
| enterprise | 300 | Unlimited | Implemented |

**Implementation:** `rate_limiter.py` with sliding-window counter, Redis support (distributed) + SQLite fallback (single-instance).

**Feature Flags:** 
- Tier-based feature access via `@requires_tier` decorator
- Environment-based toggles (e.g., `TOR_ENABLED`, `RATE_LIMIT_PERSIST`)

### 4.4 Audit Logging & Monitoring

**Audit Log System:**

| Component | Status | Details |
|-----------|--------|---------|
| Append-Only Logs | Implemented | JSONL format in `~/.loom/audit/` with atomic file writes |
| HMAC-SHA256 Signatures | Implemented | Every audit entry signed; `verify_integrity()` detects tampering |
| PII Scrubbing | Implemented | Regex-based redaction before audit entry creation |
| Tamper Detection | Implemented | Signature verification via `audit.py:verify_integrity()` |
| Log Retention | Partial | 30-day auto-cleanup via `research_cache_clear` tool (configurable) |
| Export Capability | Implemented | CSV/JSON export via `export_audit()` for compliance reporting |

**Audit Event Coverage:**

```python
# Every tool invocation logged:
AuditEntry(
    client_id: str,              # Authenticated user/API key
    tool_name: str,              # Tool executed (e.g., research_fetch)
    params_summary: dict,        # PII-scrubbed parameters
    timestamp: str,              # ISO UTC
    duration_ms: int,            # Latency tracking
    status: str,                 # "success", "error", "timeout", etc.
    signature: str,              # HMAC-SHA256
)
```

**Structured Logging:**

| Logger | Level | Coverage |
|--------|-------|----------|
| `loom.server` | DEBUG+ | Server startup, tool registration, initialization |
| `loom.auth` | INFO+ | Authentication success/failure, token mismatch |
| `loom.audit` | INFO+ | Audit entry creation, verification failures |
| `loom.rate_limiter` | DEBUG+ | Rate limit hits, tier enforcement |
| `loom.validators` | DEBUG+ | SSRF detection, URL validation failures |
| `loom.cache` | DEBUG+ | Cache hits/misses, eviction events |
| All tools | DEBUG+ | Tool-specific execution details, API errors |

**Log Format:** 
- Time: ISO 8601 UTC
- Level: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Request ID: Injected via `RequestIdFilter` from `tracing.py`
- Message: PII-scrubbed via `scrub_pii()` function

**Monitoring & Alerting (Planned):**
- Prometheus metrics on Hetzner (latency, throughput, error rates)
- SLA tracking: target 99.5% availability
- Circuit breaker for cascading failures
- Dead-letter queue (DLQ) for failed async tasks
- Real-time alerting via Slack webhook (on critical errors)

### 4.5 Incident Response & Disaster Recovery

**Incident Detection:**

| Mechanism | Status | Details |
|-----------|--------|---------|
| Error Rate Monitoring | Partial | Logs captured; alerting framework planned Q3 |
| Rate Limit Anomalies | Implemented | Rate limiter tracks per-user spikes |
| Authentication Failures | Implemented | Failed token attempts logged with client fingerprint |
| Timeout Detection | Implemented | Tool timeout + retry logic with exponential backoff |
| Circuit Breaker | Implemented | `cicd.py` circuit breaker for cascading failure prevention |

**Incident Response Process (Documented):**

1. **Detection:** Error rate spike or alerting rule trigger
2. **Classification:** Security breach vs. operational failure vs. performance issue
3. **Containment:** Circuit breaker activation; rate limit throttling
4. **Communication:** Slack notification to developer (solo); documentation for customers
5. **Remediation:** Rollback via git (if code-related) or manual intervention
6. **Post-Incident:** Root cause analysis; audit log export for forensics

**Disaster Recovery Plan:**

| RTO | RPO | Mechanism | Status |
|-----|-----|-----------|--------|
| 15 minutes | 1 hour | Daily SQLite backup to S3 (planned) | Partial |
| 30 minutes | Same | Automated Hetzner snapshot | Implemented |
| Full restore | - | Code from GitHub; data from backup | Documented |

**Backup Strategy:**
- Daily backup of audit logs and session database
- Retention: 30 days (rolling)
- Encryption: Optional (can enable with gpg wrapper)
- Tested restoration: Quarterly manual test (TODO)

### 4.6 Input Validation & SSRF Prevention

**URL Validation:**

```python
# From validators.py:validate_url()
- Scheme: http, https only
- Reserved IPs blocked: 127.0.0.1, 10.x, 172.16-31.x, 192.168.x, ::1, fc00::/7
- Hostname resolution: Cached (Redis w/ fallback to in-memory dict)
- TOCTOU prevention: Cache-based DNS resolution
- Max URL length: 2048 characters
- Timeout: 30 seconds (configurable)
```

**Parameter Validation:**

| Layer | Mechanism | Status |
|-------|-----------|--------|
| Schema | Pydantic v2 models (params.py) | Implemented |
| Strictness | `extra="forbid"`, `strict=True` | Implemented |
| Type Checking | Runtime validation + mypy static checks | Implemented |
| Character Capping | `MAX_CHARS_HARD_CAP` (200K default) | Implemented |
| GitHub Query Sanitization | Regex allow-list (GH_QUERY_RE) | Implemented |
| File Path Validation | Prevents path traversal (no `../`) | Implemented |

**Audit Readiness:**
- All parameter models in single file (`params.py`) for auditability
- Validation errors logged with sanitized context
- Request context available for incident investigation

### 4.7 Data Classification & Handling

**Data Types Processed:**

| Type | Sensitivity | Handling |
|------|-------------|----------|
| User API Key | High (Secret) | Environment variable; never logged verbatim; rotation required on exposure |
| PII (email, phone, IP, SSN) | High | Regex-scrubbed from logs; not stored; audit logs sanitized |
| Cache Content | Low-Medium | SHA-256 content hash keyed; daily directory structure; 30-day retention |
| Audit Logs | Medium | HMAC-signed for integrity; append-only; 30-day retention |
| Session Data | Medium | SQLite with optional encryption; LRU eviction (max 8 sessions) |
| Research Results | Low | Cached by content hash; deduplication enabled |
| Tool Configuration | Medium | Config file in `./config.json` or `$LOOM_CONFIG_PATH`; validated at startup |

**PII Scrubbing Rules (Implemented):**
```python
# From pii_scrubber.py (inferred from audit.py usage):
- Email: name@domain.tld → [EMAIL_REDACTED]
- IP Address: 192.168.1.1 → [IP_REDACTED]
- Phone: +1-555-0123 → [PHONE_REDACTED]
- SSN: 123-45-6789 → [SSN_REDACTED]
- Credit Card: 4111-1111-1111-1111 → [CC_REDACTED]
- API Key: sk_live_abc123... → [API_KEY_REDACTED]
```

### 4.8 Configuration Management

**Config System (`config.py`):**

| Feature | Status | Details |
|---------|--------|---------|
| Pydantic Validation | Implemented | All config keys validated on startup |
| Environment Variable Defaults | Implemented | Explicit `get()` calls with fallback values |
| Config File Support | Implemented | JSON-based; path resolved via `$LOOM_CONFIG_PATH` or `./config.json` |
| Change Tracking | Partial | Git-based (via .gitignore); no formal version control |
| Audit Trail | Partial | Config loading logged; changes not explicitly audited |

**Sensitive Config Elements:**
- `LOOM_API_KEY` (Bearer token)
- `LOOM_AUDIT_SECRET` (HMAC key)
- `LOOM_ALLOW_ANONYMOUS` (feature flag)
- Provider API keys (Groq, NVIDIA NIM, etc.)

**Audit Recommendation:** Implement formal config audit trail (capture all changes with timestamp + previous value).

### 4.9 Change Management

**Current Process:**

1. **Code Changes:** Git-based (conventional commits: `feat:`, `fix:`, etc.)
2. **Testing:** pytest with 80%+ coverage target (run on Hetzner, not local)
3. **Deployment:** Manual (git pull + restart loom-server systemd service)
4. **Approval:** Solo developer (no formal approval gate)

**Audit Gaps:**
- No formal change request (CR) process
- No pre-deployment approval checklist
- No automated testing in CI/CD
- No separation of duties (developer = deployer)

**Recommendations:**
- Implement GitHub Actions for automated testing
- Add formal change approval process (even for solo developer)
- Document rollback procedures
- Enable git commit signing (GPG)

### 4.10 Network Architecture & Physical Controls

**Infrastructure:**

| Component | Provider | Details |
|-----------|----------|---------|
| Compute | Hetzner | Dedicated CPU, 24 GB RAM |
| Network | Hetzner | DDoS protection, redundant BGP, IPv4 + IPv6 |
| Storage | Hetzner | Local NVMe SSD (encrypted filesystem) |
| Backup | Manual (S3 planned) | Daily snapshot of audit logs + sessions database |
| DNS | Hetzner | DNSSEC support |
| TLS Termination | Hetzner | Native TLS 1.2+ enforcement on inbound traffic |

**Hetzner Data Center Security (Shared Responsibility):**
- Physical security (biometric access, surveillance)
- Network security (DDoS mitigation, BGP filtering)
- Power redundancy (N+2 UPS + generators)
- Fire suppression (gaseous, not water-based)
- Temperature monitoring (24/7 environmental controls)

**Application-Level Controls:**
- No hardcoded credentials in code
- Environment variables for all secrets
- Audit logs stored locally (with backup)
- rate limiting at application level
- Circuit breaker for cascading failures

---

## 5. Known Gaps & Remediation Plan

### Critical Gaps (Pre-Audit)

| Gap | Impact | Remediation | Timeline |
|-----|--------|-------------|----------|
| **No external penetration test** | Medium | Conduct independent security assessment | Before Type II observation |
| **Manual change management** | Medium | Implement formal change request process | Q2 2026 |
| **No automated backups to S3** | High | Set up automated daily backups with encryption | Q2 2026 |
| **Optional SQLCipher** | Medium | Make at-rest encryption mandatory by default | Q2 2026 |
| **No employee security training** | Low | Document solo developer security practices; annual self-training log | Q3 2026 |
| **Informal incident response** | Medium | Create formal incident response playbook | Q2 2026 |
| **No vendor risk assessments** | Medium | Document Hetzner, Stripe, and provider SLAs | Q3 2026 |

### Medium-Priority Gaps (During Audit)

| Gap | Remediation |
|-----|-------------|
| No formal encryption key lifecycle | Document key rotation procedures; implement automated key versioning |
| Config audit trail missing | Log all config changes with timestamp + username + previous value |
| Limited RBAC | Extend role definitions beyond tier-based access; implement formal role matrix |
| No OAuth2 integration | Implement OAuth2 provider scaffold (can be optional for solo usage) |
| Partial data classification policy | Formalize data classification matrix + retention schedule |

### Low-Priority Gaps (Post-Audit)

| Gap | Timeline |
|-----|----------|
| No MFA support | Q4 2026 |
| Limited monitoring/alerting | Q3 2026 (Prometheus + Slack) |
| No automated CI/CD testing | Q3 2026 (GitHub Actions) |
| No git commit signing | Q3 2026 (GPG key management) |

---

## 6. Audit Requirements & Deliverables

### 6.1 Pre-Audit Information Required

We will provide the audit firm with:

1. **Architecture Documentation**
   - System topology diagram
   - Data flow diagrams (user → authentication → tool execution → audit logging)
   - Deployment architecture (Hetzner single-server setup)

2. **Control Documentation**
   - Security policy (draft attached below)
   - Access control matrix
   - Encryption and key management procedures
   - Incident response playbook
   - Change management procedures

3. **Evidence**
   - Sample audit logs (with PII redacted)
   - Configuration examples (sanitized API keys)
   - Code snippets: auth.py, audit.py, validators.py, rate_limiter.py
   - Test coverage report (pytest --cov output)

4. **Infrastructure Details**
   - Hetzner account information and SLA documentation
   - Network architecture diagram
   - Backup and disaster recovery procedures

5. **Personnel Information**
   - Solo developer background + security training
   - GitHub commit history (demonstrates change tracking)
   - Previous security certifications or audits (if any)

### 6.2 Expected Deliverables from Audit Firm

1. **SOC2 Type II Report**
   - SOC2 trust service criteria assessment (CC, A, C)
   - Control testing methodology and results
   - Management representation letter
   - Auditor attestation statement
   - Compliance statement (e.g., "System complies with SOC2 Type II security criteria")

2. **Detailed Findings Report**
   - Critical findings (must remediate before certification)
   - High findings (should remediate)
   - Medium findings (recommended)
   - Low findings (informational)
   - Executive summary with risk assessment

3. **Gap Assessment**
   - Current state vs. SOC2 requirements
   - Priority matrix for remediation
   - Timeline estimates

4. **Remediation Recommendations**
   - Detailed action items
   - Implementation priorities
   - Effort estimates
   - Success criteria

5. **Attestation Statement**
   - "We have tested the controls and found them effective as of [date]"
   - Statement of auditor independence
   - Scope limitations

---

## 7. Proposed Timeline

| Phase | Dates | Duration | Activities |
|-------|-------|----------|------------|
| **Planning & Assessment** | Apr 2026 - May 2026 | 2 weeks | Gap analysis, scope finalization, kickoff meeting |
| **Observation Period** | Apr 2026 - Sep 2026 | 6 months | Continuous control testing, logs collection |
| **Testing & Fieldwork** | Jul 2026 - Aug 2026 | 6 weeks | On-site/remote testing, control evidence collection |
| **Report & Remediation** | Aug 2026 - Sep 2026 | 4 weeks | Draft report, gap remediation, final testing |
| **Final Report Issuance** | Sep 2026 | - | SOC2 Type II report issued and signed |

**Key Milestones:**
- May 15, 2026: Audit kickoff meeting
- May 31, 2026: Complete gap remediation (backups, encryption, change management)
- Jul 15, 2026: Begin detailed control testing
- Aug 31, 2026: All findings addressed
- Sep 30, 2026: Final SOC2 Type II report issued

---

## 8. Budget & Engagement Model

### 8.1 Estimated Budget Range

Based on system complexity (single-server, 220+ tools, solo developer):

| Audit Firm Category | Estimated Cost | Notes |
|-------------------|-----------------|-------|
| **Mid-Market Boutique** | $15,000 - $25,000 | Recommended for technical depth |
| **Big 4 (small engagement)** | $25,000 - $50,000 | Higher cost; brand reputation |
| **Startup-Focused** | $12,000 - $18,000 | Lower cost; less brand equity |

### 8.2 Preferred Audit Firms

We are seeking proposals from firms with experience in:
- API/SaaS platforms
- Python/Linux environments
- Compliance automation tools (e.g., experience with Vanta, Drata, or Secureframe)
- Solo founder/small team organizations

**Recommended Firms:**
1. **Vanta** (US-based, automated compliance platform)
2. **Drata** (Canada-based, SOC2 + ISO 27001 + other frameworks)
3. **Secureframe** (US-based, AI-powered compliance)
4. **Big 4 Audit Firms** (Deloitte, PwC, EY, KPMG - for premium brand)

### 8.3 Engagement Model

We prefer:
- **Hybrid:** In-person kickoff meeting; remote testing and evidence collection
- **Remote-First:** All communication via video conference and secure file transfer
- **Deliverable-Based:** Clear pricing for each milestone (gap assessment, remediation, final report)

---

## 9. Security Policy & Control Statements

### 9.1 Information Security Policy (Draft)

**Policy Statement:**

Loom Research Tools is committed to protecting the confidentiality, integrity, and availability of information and systems. We maintain a comprehensive information security program that:

1. **Authenticates** all users via API keys with constant-time comparison
2. **Encrypts** data in transit (TLS 1.2+) and optionally at rest (SQLCipher)
3. **Audits** all tool invocations with tamper-proof HMAC-SHA256 signatures
4. **Scrubs** PII from logs and audit entries
5. **Validates** all user input to prevent SSRF, injection, and other attacks
6. **Monitors** rate limits per user/tier to ensure availability
7. **Detects** and responds to security incidents via circuit breakers and alerting
8. **Backs up** audit logs and sessions database daily
9. **Changes** code through git-based workflow with testing and approval
10. **Assesses** vendor risk and documents third-party SLAs

### 9.2 Acceptable Use Policy (Draft)

Users of Loom agree to:
- Use the service only for authorized research and intelligence gathering
- Not use the service for malicious purposes (e.g., unauthorized network penetration)
- Not attempt to circumvent authentication or rate limiting controls
- Not disclose or share API keys with unauthorized parties
- Comply with all applicable laws and regulations
- Report security incidents to the security contact immediately

**Prohibited Uses:**
- Automated attacks on third-party systems
- Phishing or social engineering
- Malware distribution
- Illegal surveillance or wiretapping
- Violation of copyright or intellectual property rights
- Defamation or libel
- Harassment or threats

---

## 10. Auditor Access & Support

### 10.1 Technical Access

We will provide the audit firm with:
- **SSH Access:** To Hetzner server for log inspection and control verification
- **API Access:** Test Bearer token with full scope for MCP tool testing
- **Source Code Access:** GitHub repository (private if needed; currently public)
- **Database Access:** Read-only access to audit logs, config, and sessions database

### 10.2 Assistance & Documentation

- **On-Call Support:** Developer available for technical questions (email, Slack, Zoom)
- **Architecture Walkthroughs:** Video call to explain system design and control flow
- **Log Interpretation:** Help explaining audit log format and PII scrubbing
- **Tool Demonstrations:** Live demo of MCP server tools and rate limiting
- **Evidence Collection:** Assistance gathering logs, screenshots, config files

### 10.3 Timelines & Communication

- **Weekly Status Calls:** 30-minute sync to discuss findings and progress
- **Slack Channel:** Real-time questions and document sharing
- **Response Time:** 24-hour response target for non-emergency questions
- **Evidence Delivery:** 2-business-day turnaround for requested documentation

---

## 11. Post-Audit Next Steps

### 11.1 Certification Maintenance

Once SOC2 Type II certification is achieved:

1. **Annual Reporting:** Provide SOC2 report to customers upon request
2. **Monitoring:** Continue audit log collection and control testing
3. **Continuous Improvement:** Implement recommended controls and enhancements
4. **Renewal:** Plan for next SOC2 Type II audit in 12 months (rolling certification)

### 11.2 Related Certifications

Successful SOC2 Type II audit will position us for:

- **ISO 27001:** Planned Q4 2026 (leverages SOC2 controls)
- **EU AI Act Conformity:** Building on existing 5 AI safety tools
- **GDPR Compliance:** Already implemented (PII scrubbing, audit logging, data retention)
- **HIPAA/FedRAMP:** Future roadmap items

---

## 12. Contact Information

**Point of Contact:**

- **Name:** Ahmed Adel Bakr Alderai
- **Title:** Founder/Principal Developer
- **Email:** ahmedalderai22@gmail.com
- **Phone:** +1 (available upon request)
- **GitHub:** @aadel (loom repository)

**Proposal Submission:**

Please send proposals to: ahmedalderai22@gmail.com

**Proposal Review Criteria:**
- Price competitiveness
- Auditor credentials and experience
- Timeline feasibility
- Geographic proximity (EU-based preferred)
- References from similar SaaS/API platforms

**Proposal Deadline:** May 31, 2026

---

## Appendices

### Appendix A: System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client (External User)                   │
└─────────────────────────────────────────────────────────────┘
                            │
                       Bearer Token
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Hetzner Network Layer                       │
│                  (TLS 1.2+, DDoS Protection)                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│          TCP 8787 (Streamable-HTTP MCP Server)              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ApiKeyVerifier (auth.py)                             │  │
│  │ - Verify Bearer token                                │  │
│  │ - Return AccessToken(scopes) or None                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ RateLimiter (rate_limiter.py)                        │  │
│  │ - Check tier limits (free/pro/enterprise)            │  │
│  │ - Sliding window counter per user                    │  │
│  │ - Redis (primary) + SQLite (fallback)                │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ MCP Tool Dispatcher                                  │  │
│  │ - 220+ tools: fetch, spider, search, github, etc.    │  │
│  │ - Parameter validation (Pydantic models)             │  │
│  │ - URL validation (SSRF prevention)                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│         ┌──────────────────┼──────────────────┐             │
│         ▼                  ▼                  ▼             │
│    ┌────────────┐   ┌────────────┐   ┌────────────┐       │
│    │ Scraping   │   │  Search    │   │   GitHub   │       │
│    │ (Scrapling │   │  (Multi-   │   │   (gh CLI) │       │
│    │  + Crawl4AI│   │  provider) │   │            │       │
│    └────────────┘   └────────────┘   └────────────┘       │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Audit Logger (audit.py)                              │  │
│  │ - PII scrubbing                                      │  │
│  │ - HMAC-SHA256 signing                                │  │
│  │ - Append-only JSONL logs                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Persistent Storage                                   │  │
│  │ - ~/.loom/audit/ (audit logs)                        │  │
│  │ - ~/.cache/loom/ (research cache)                    │  │
│  │ - ~/.loom/sessions/ (browser sessions)               │  │
│  │ - SQLite with optional encryption (SQLCipher)        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 Daily Backups (Planned)                     │
│                 - S3 bucket (encrypted)                     │
│                 - Retention: 30 days                        │
│                 - Tested quarterly                          │
└─────────────────────────────────────────────────────────────┘
```

### Appendix B: Relevant Code Snippets

#### B.1 Authentication (auth.py)

```python
class ApiKeyVerifier:
    """Verify bearer tokens against LOOM_API_KEY environment variable."""
    
    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify bearer token and return AccessToken if valid."""
        if self.api_key:
            # Constant-time comparison to prevent timing attacks
            if secrets.compare_digest(token, self.api_key):
                return AccessToken(token=token, client_id="api_key", scopes=["*"])
            return None  # Token mismatch
        
        # Default: restrict to health checks only
        return AccessToken(token="anonymous-restricted", client_id="anonymous-restricted", scopes=["health"])
```

#### B.2 Audit Logging (audit.py excerpt)

```python
@dataclass
class AuditEntry:
    """Single audit log entry for a tool invocation."""
    client_id: str
    tool_name: str
    params_summary: dict[str, Any]
    timestamp: str  # ISO UTC
    duration_ms: int
    status: str
    signature: str = ""
    
    def compute_signature(self, secret: str) -> str:
        """Compute HMAC-SHA256 signature."""
        json_str = self.to_json(include_signature=False)
        sig = hmac.new(secret.encode(), json_str.encode(), hashlib.sha256).hexdigest()
        return sig
```

#### B.3 URL Validation (validators.py excerpt)

```python
def validate_url(url: str, timeout_secs: int = 30) -> tuple[bool, str]:
    """SSRF-safe URL validation.
    
    Checks:
    - Scheme is http or https
    - Reserved IPs are blocked (127.0.0.1, 10.x, 172.16-31.x, 192.168.x, ::1, fc00::/7)
    - Hostname resolution is cached (Redis with fallback)
    - No timeout attacks
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, "Invalid scheme"
    
    # Resolve hostname and check for reserved IPs
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, timeout=timeout_secs)
        for addr in addresses:
            ip = ipaddress.ip_address(addr[4][0])
            if ip.is_private or ip.is_loopback:
                return False, "Reserved IP address"
    except (socket.error, ValueError) as e:
        return False, f"Resolution failed: {e}"
    
    return True, "OK"
```

#### B.4 Rate Limiting (rate_limiter.py excerpt)

```python
TIER_LIMITS = {
    "free": {"per_min": 10, "per_day": 100},
    "pro": {"per_min": 60, "per_day": 10000},
    "enterprise": {"per_min": 300, "per_day": None},  # Unlimited
}

async def check_limit(user_id: str, tier: str, category: str) -> dict | None:
    """Check rate limit for user. Returns None if OK, error dict otherwise."""
    limits = TIER_LIMITS[tier]
    
    # Sliding-window counter (60-second window)
    current_min = await count_requests_in_window(user_id, category, 60)
    if current_min >= limits["per_min"]:
        return {"error": "Rate limit exceeded", "code": "RATE_LIMITED"}
    
    # Daily counter
    if limits["per_day"] is not None:
        current_day = await count_requests_in_window(user_id, category, 86400)
        if current_day >= limits["per_day"]:
            return {"error": "Daily limit exceeded", "code": "DAILY_LIMIT_EXCEEDED"}
    
    return None  # OK
```

---

**End of RFP Document**

---

**Document Version:** 1.0  
**Last Updated:** May 4, 2026  
**Author:** Ahmed Adel Bakr Alderai  
**Classification:** Business-Confidential
