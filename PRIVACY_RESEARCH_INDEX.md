# Loom Privacy Research: Complete Index

## Research Overview

**Date**: 2026-05-01  
**Scope**: Privacy, anonymity, counter-surveillance, and anti-forensics tools on GitHub  
**Method**: GitHub API search with star ranking  
**Results**: 18 tools identified, 14 recommended for integration, 49+ total tasks

---

## Key Documents

### 1. **PRIVACY_RESEARCH_REPORT.md** (Primary Reference)
   - Comprehensive analysis of all 18 tools
   - Detailed descriptions, use cases, threat models
   - Integration patterns and implementation guidance
   - Strategic rationale for Loom
   - GitHub search queries for future updates
   - **Best for**: Understanding the "why" behind each tool

### 2. **PRIVACY_INTEGRATION_SUMMARY.txt** (Quick Reference)
   - Tier 1/2/3 breakdown
   - Quick links and effort estimates
   - Implementation checklist
   - Strategic benefits at a glance
   - Next steps and timeline
   - **Best for**: Quick overview and decision-making

### 3. **PRIVACY_TOOLS_COMPARISON.csv** (Data Format)
   - Spreadsheet with all 18 tools
   - Stars, GitHub URLs, categories, effort
   - Sortable by tier, priority, effort
   - **Best for**: Spreadsheet analysis and tracking

### 4. **CLAUDE.md** (Integration Tasks)
   - INTEGRATE-032 through INTEGRATE-049 (18 tasks)
   - Tier 1: 4 tools (INTEGRATE-032-035)
   - Tier 2: 4 tools (INTEGRATE-036-039)
   - Tier 3: 10 tools (INTEGRATE-040-049)
   - File locations, tool signatures, test requirements
   - **Best for**: Implementation planning and tracking

---

## Quick Start Guide

### For Decision Makers
1. Read PRIVACY_INTEGRATION_SUMMARY.txt (5 min)
2. Review Tier 1 tools in PRIVACY_RESEARCH_REPORT.md (15 min)
3. Check effort/ROI tradeoffs in PRIVACY_TOOLS_COMPARISON.csv (5 min)
4. **Decision**: Approve TIER 1 (FingerprintJS + creepjs + usbkill + Forensia)

### For Project Managers
1. Copy integration tasks from CLAUDE.md
2. Create GitHub issues INTEGRATE-032 through INTEGRATE-049
3. Assign Tier 1 tasks to dev (estimate: 2 weeks)
4. Plan Tier 2 for weeks 3-4 (estimate: 2 weeks)
5. Review Tier 3 capability roadmap

### For Developers
1. Clone PRIVACY_RESEARCH_REPORT.md for tool details
2. Follow implementation pattern in CLAUDE.md section "Adding new tools"
3. Use PRIVACY_TOOLS_COMPARISON.csv to track progress
4. Reference example tool signatures in PRIVACY_RESEARCH_REPORT.md

---

## Tools by Category

### Anti-Forensics (3 tools)
- **usbkill** (4583⭐) — Physical device kill-switch
- **Forensia** (783⭐) — Evidence cleanup automation
- **silk-guardian** (720⭐) — Linux anti-forensics

### Browser Fingerprinting (6 tools)
- **FingerprintJS** (27020⭐) — Advanced fingerprinting detection
- **supercookie** (7042⭐) — Favicon-based tracking
- **browser-fingerprinting** (4999⭐) — Bot detection analysis
- **creepjs** (2360⭐) — Privacy exposure assessment
- **fingerprint-suite** (2076⭐) — Anonymization validation
- **chameleon** (544⭐) — Fingerprint randomization

### Steganography (3 tools)
- **LSB-Steganography-Python** (13⭐) — Image data hiding
- **steganography-python** (13⭐) — Media concealment
- **stegma** (2⭐) — Multi-format covert channels

### Specialized Tools (6 tools)
- **ulexecve** (208⭐) — Fileless execution
- **saruman** (141⭐) — Binary obfuscation
- **flock-detection** (6⭐) — Wireless surveillance detection
- **swiftGuard** (456⭐) — macOS anti-forensics
- **BrowserBlackBox** (2⭐) — Interactive privacy audit
- **PII-Recon** (1⭐) — Data exposure detection

---

## Integration Timeline

### Weeks 1-2: TIER 1 (Critical Path)
```
├─ INTEGRATE-032: FingerprintJS (start here, 4 days)
├─ INTEGRATE-033: creepjs (3 days, parallel)
├─ INTEGRATE-034: usbkill (5 days, start early)
└─ INTEGRATE-035: Forensia (4 days)
Total: 16 days capacity for ~2 developers
```

### Weeks 3-4: TIER 2 (Operational Enhancement)
```
├─ INTEGRATE-036: supercookie (3 days)
├─ INTEGRATE-037: fingerprint-suite (4 days)
├─ INTEGRATE-038: silk-guardian (4 days)
└─ INTEGRATE-039: LSB steganography (3 days)
Total: 14 days
```

### Weeks 5-6: TIER 3 (Specialized Capabilities)
```
├─ INTEGRATE-040-049: 10 tools
├─ Effort: 2-5 days each
└─ Stagger based on priority + capacity
```

---

## Strategic Value by Tool

### Tier 1: Must-Have
- **FingerprintJS**: Essential for privacy research validation
- **creepjs**: Fastest privacy baseline assessment (5 min)
- **usbkill**: Only tool providing physical security layer
- **Forensia**: Automates post-exploit evidence destruction

### Tier 2: High-Impact
- **supercookie**: Reveals invisible tracking (favicon persistence)
- **fingerprint-suite**: Validates anonymity tools actually work
- **silk-guardian**: Linux-only defensive hardening
- **LSB-Steganography**: Enables covert data exfiltration

### Tier 3: Specialized
- **ulexecve**: EDR evasion via memory execution
- **saruman**: Binary-level code hiding
- **flock-detection**: Physical counter-surveillance
- Others: Domain-specific research capabilities

---

## Success Metrics (Post-Integration)

Track these KPIs after TIER 1 deployment:

1. **Privacy Audit Velocity**
   - Target: <5 minutes for complete privacy baseline
   - Metric: Time from `research_fingerprint_audit()` to report

2. **Fingerprinting Effectiveness**
   - Target: 99%+ detection of common tracking vectors
   - Metric: False negative rate on test browsers

3. **Tool Adoption**
   - Target: >80% of privacy assessments use FingerprintJS
   - Metric: Tool invocation frequency across user base

4. **Artifact Cleanup Reliability**
   - Target: 100% artifact removal on test systems
   - Metric: Zero artifacts remaining after `research_artifact_cleanup()`

5. **Anti-Forensics Effectiveness**
   - Target: Undetectable device activity with usbkill
   - Metric: Forensic tool false negative rate

---

## Risk Mitigation

### Dependency Management
- Pin all tool versions in `requirements-privacy.txt`
- Run security audit via Snyk before each release
- Verify Python 3.11+ compatibility for each tool

### Platform-Specific Handling
- usbkill → Linux/macOS only
- swiftGuard → macOS only
- Forensia → Windows/Linux/macOS (OS-specific codepaths)
- silk-guardian → Linux only

### Rate Limiting & Performance
- Implement caching for fingerprint audits
- Stagger requests to avoid API rate limits
- Add circuit breakers for timeout-prone tools

### Testing in Production
- All anti-forensics tools tested in sandboxes only
- No production artifact deletion without explicit confirmation
- Dry-run mode for destructive operations

---

## FAQ

**Q: Why start with FingerprintJS?**  
A: Highest star count (27K), most impactful for privacy research, easiest implementation, enables other fingerprinting tools.

**Q: What about implementation order?**  
A: Follow Tier 1 → Tier 2 → Tier 3. Within tier, start with highest stars / lowest effort first.

**Q: How long to integrate TIER 1?**  
A: 2 weeks with 1-2 developers. FingerprintJS takes 4 days (start here). Others run in parallel.

**Q: Which tools need API keys?**  
A: None of these privacy tools require API keys. All are self-contained.

**Q: Can I skip any TIER 1 tools?**  
A: Not recommended. Each fills a distinct gap:
  - FingerprintJS: fingerprint detection
  - creepjs: quick assessment
  - usbkill: physical security
  - Forensia: evidence cleanup

**Q: Which tools require special permissions?**  
A: usbkill, swiftGuard, Forensia, silk-guardian all require elevated privileges (admin/root) for filesystem operations.

---

## Useful Commands

### List all integration tasks
```bash
grep -n "INTEGRATE-03" /Users/aadel/projects/loom/CLAUDE.md
```

### Create GitHub issues from tasks
```bash
# Extract task list
grep "INTEGRATE-" CLAUDE.md | head -20
```

### Check CSV sorting
```bash
# Sort by effort (high to low)
sort -t, -k8 -nr PRIVACY_TOOLS_COMPARISON.csv | head -10

# Sort by tier + stars
sort -t, -k5,k1 -nr PRIVACY_TOOLS_COMPARISON.csv
```

### Track integration progress
```bash
# Count completed tasks (after implementation)
grep "✓ INTEGRATE-" CLAUDE.md | wc -l
```

---

## Related Repositories

All tools are hosted on GitHub with public repositories. No special access required.

Key repositories:
- https://github.com/fingerprintjs/fingerprintjs (27K⭐)
- https://github.com/hephaest0s/usbkill (4.6K⭐)
- https://github.com/Forensia/Forensia (783⭐)
- https://github.com/abrahamjuliot/creepjs (2.3K⭐)
- https://github.com/jonasstrehle/supercookie (7K⭐)

Full list in PRIVACY_TOOLS_COMPARISON.csv (GitHub URL column).

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-05-01 | 1.0 | Initial research + integration roadmap |

---

## Document Relationships

```
PRIVACY_RESEARCH_INDEX.md (this file)
├─ PRIVACY_RESEARCH_REPORT.md (detailed analysis)
├─ PRIVACY_INTEGRATION_SUMMARY.txt (quick reference)
├─ PRIVACY_TOOLS_COMPARISON.csv (data format)
├─ CLAUDE.md (task checklist)
└─ (Supporting files in repo)
```

---

**For questions or updates, see PRIVACY_RESEARCH_REPORT.md section 9 (GitHub search recommendations).**
