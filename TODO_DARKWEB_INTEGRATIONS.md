# Dark Web & Underground Intelligence Integration TODO

Based on comprehensive GitHub research (2026-05-01), these are the recommended integration tasks for Loom.

## Tier 1: IMMEDIATE (This Sprint)

### INTEGRATE-026: Implement robin (AI-Powered Dark Web OSINT)
- **Priority**: HIGH | **Stars**: 4927 | **Effort**: MEDIUM
- **URL**: https://github.com/apurvsinghgautam/robin
- **Task**:
  - [ ] Clone and audit robin codebase
  - [ ] Design research_robin_scan() MCP tool signature
  - [ ] Implement Tor integration via existing tor.py module
  - [ ] Handle timeouts (expect 30-60s Tor delays)
  - [ ] Implement 24-48 hour response caching
  - [ ] Add result normalization (threat scores, sources)
  - [ ] Write comprehensive tests (mocked dark web responses)
  - [ ] Add to tools-reference.md documentation
  - [ ] Create integration test with live Tor (if available)

### INTEGRATE-027: Implement OnionScan (Service Vulnerability Scanner)
- **Priority**: HIGH | **Stars**: 1700+ | **Effort**: MEDIUM
- **URL**: https://github.com/s-rah/onionscan
- **Task**:
  - [ ] Download and compile OnionScan Go binary
  - [ ] Design research_onion_scan() MCP tool
  - [ ] Implement subprocess wrapper for Go binary
  - [ ] Accept: .onion URL parameter
  - [ ] Parse vulnerability output into structured format
  - [ ] Implement 48-hour caching (services stable)
  - [ ] Add error handling for offline .onion services
  - [ ] Test with known .onion services
  - [ ] Document in tools-reference.md

### INTEGRATE-028: Enhance TorBot Integration (dark_recon.py Refresh)
- **Priority**: MEDIUM | **Stars**: 4044 | **Effort**: LOW
- **URL**: https://github.com/DedSecInside/TorBot
- **Task**:
  - [ ] Review current dark_recon.py implementation
  - [ ] Check TorBot version (may be outdated)
  - [ ] Update TorBot to latest stable version
  - [ ] Add multi-target concurrent crawling
  - [ ] Implement result deduplication
  - [ ] Add output sanitization (prevent SSRF leaks)
  - [ ] Improve error handling for failed crawls
  - [ ] Write integration tests
  - [ ] Update documentation

---

## Tier 2: NEXT 2-3 WEEKS

### INTEGRATE-029: Standardize HaveIBeenPwned Integration
- **Priority**: HIGH | **Stars**: N/A | **Effort**: LOW-MEDIUM
- **URLs**: 
  - https://github.com/sinduvi87/haveibeenpwned
  - https://github.com/ShadowStrike-CTF/hibp-breach-auditor
- **Task**:
  - [ ] Audit existing breach_check.py module
  - [ ] Design research_breach_check_comprehensive() tool
  - [ ] Support: email lookup, password hash (k-anonymity), username
  - [ ] Implement bulk credential checking
  - [ ] Add breach timeline analysis
  - [ ] Integrate with credential dump data
  - [ ] Implement 24-hour cache with TTL
  - [ ] Add compliance reporting features
  - [ ] Write tests with test breach data
  - [ ] Document in tools-reference.md

### INTEGRATE-030: Implement telegram-osint-scraper
- **Priority**: MEDIUM | **Stars**: 0 (emerging) | **Effort**: MEDIUM
- **URLs**:
  - https://github.com/Neurone4444/telegram-osint-scraper
  - https://github.com/aceloolrd/telegram-osint-scraper
- **Task**:
  - [ ] Evaluate both telegram-osint-scraper repos
  - [ ] Design research_telegram_osint() MCP tool
  - [ ] Accept: channel URL/ID, keyword, date range
  - [ ] Implement Telethon integration (if needed)
  - [ ] Extract public channel messages
  - [ ] Analyze discussion sentiment
  - [ ] Implement Telegram rate limiting
  - [ ] Add message archival/caching
  - [ ] Identify underground communities
  - [ ] Write tests with public Telegram channels
  - [ ] Document in tools-reference.md

### INTEGRATE-031: Integrate dark-web-osint-tools Suite
- **Priority**: MEDIUM | **Stars**: 2080 | **Effort**: MEDIUM-HIGH
- **URL**: https://github.com/apurvsinghgautam/dark-web-osint-tools
- **Task**:
  - [ ] Audit tools in the suite
  - [ ] Select key utilities for integration
  - [ ] Design research_darkweb_suite() orchestrator
  - [ ] Implement sub-tools as modular components
  - [ ] Leverage existing Tor infrastructure
  - [ ] Add result caching and deduplication
  - [ ] Implement tool composition/chaining
  - [ ] Test with multiple query types
  - [ ] Document each sub-tool
  - [ ] Create end-to-end integration tests

---

## Tier 3: BACKLOG (Strategic, Lower Priority)

### INTEGRATE-032: Monitor robin-smesh (Early Stage)
- **Priority**: LOW | **Stars**: 2 | **Effort**: LOW (research only)
- **URL**: https://github.com/copyleftdev/robin-smesh
- **Task**:
  - [ ] Monitor repository for maturity/activity
  - [ ] Review source code periodically
  - [ ] Assess Rust ecosystem integration
  - [ ] Schedule re-evaluation Q3 2026
  - [ ] Create integration plan if it matures

### INTEGRATE-033: Ransomware Payment Site Monitoring
- **Priority**: MEDIUM | **Effort**: MEDIUM-HIGH
- **Task**:
  - [ ] Research major ransomware groups' leak sites
  - [ ] Identify common .onion infrastructure patterns
  - [ ] Design research_ransomware_monitor() tool
  - [ ] Implement crawler for gang leak sites
  - [ ] Track ransom demands and payment statuses
  - [ ] Correlate with incident timelines
  - [ ] Add notification/alerting
  - [ ] Create security intelligence reports

### INTEGRATE-034: Enhance Blockchain Forensics
- **Priority**: MEDIUM | **Effort**: MEDIUM
- **Task**:
  - [ ] Audit existing crypto_trace.py module
  - [ ] Integrate Glassnode API (on-chain analytics)
  - [ ] Implement CoinJoin detection
  - [ ] Add Monero ring signature analysis
  - [ ] Implement Bitcoin address clustering
  - [ ] Track ransom payment wallets
  - [ ] Create blockchain intelligence reports

### INTEGRATE-035: Implement Discord Server Reconnaissance
- **Priority**: LOW | **Effort**: MEDIUM
- **Task**:
  - [ ] Design research_discord_osint() tool
  - [ ] Implement Discord API integration
  - [ ] Identify underground Discord communities
  - [ ] Track threat actor communications
  - [ ] Extract user metadata
  - [ ] Implement rate limiting

### INTEGRATE-036: Implement Private Tracker Intelligence
- **Priority**: LOW | **Effort**: MEDIUM
- **Task**:
  - [ ] Research private torrent tracker enumeration
  - [ ] Design research_private_tracker_monitor() tool
  - [ ] Implement tracker discovery
  - [ ] Monitor for leaked files
  - [ ] Correlate with breach databases
  - [ ] Generate exfiltration alerts

---

## Implementation Notes

### Common Patterns
- All tools require Tor infrastructure (use existing TOR_ENABLED env var)
- Implement 24-48 hour caching for dark web content (slower, less frequent changes)
- Extend timeouts to 60+ seconds for Tor operations
- Normalize all output to consistent schema: {source, timestamp, confidence_score, threat_level}
- Implement proper error handling for offline .onion services

### Security Checklist
- [ ] SSRF validation on all .onion URLs (use validators.validate_url())
- [ ] Rate limiting to avoid detection
- [ ] Respect ToS and robots.txt where applicable
- [ ] Log all queries (audit trail)
- [ ] Sanitize all output (prevent injection)
- [ ] Consider residential proxies for sensitive queries

### Testing Strategy
- Unit tests: Tool function isolation (mocked Tor responses)
- Integration tests: Actual Tor queries (if available)
- Journey tests: Multi-tool workflows
- Security tests: SSRF/injection attempts

### Documentation
- Add entries to docs/tools-reference.md for each new tool
- Include: parameters, return schema, examples, cost estimation
- Add troubleshooting entries to docs/help.md
- Create integration guides for complex tools

---

## Metrics & Success Criteria

Each integration should achieve:
- [ ] 80%+ code coverage
- [ ] < 100ms response time (with caching)
- [ ] All SSRF vulnerabilities prevented
- [ ] Proper error handling (partial results acceptable)
- [ ] Comprehensive documentation
- [ ] Integration tests passing

---

## Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Immediate** | This Sprint (1-2 weeks) | 026, 027, 028 |
| **Near-term** | 2-3 weeks after immediate | 029, 030, 031 |
| **Strategic** | Q2-Q3 2026 | 032-036 |
| **Backlog** | As needed | Other tools |

---

## Success Definition

Loom will have comprehensive dark web & underground intelligence coverage including:
- AI-powered dark web OSINT (robin)
- Service vulnerability scanning (OnionScan)
- Breach database integration (HaveIBeenPwned)
- Telegram threat intelligence (telegram-osint-scraper)
- Ransomware tracking (custom module)
- Blockchain forensics (enhanced)
- Multi-platform OSINT (Discord, private trackers)

This represents a complete intelligence gathering stack for threat actors, infrastructure correlation, and early warning systems.
