# Privacy, Anonymity & Counter-Surveillance GitHub Research Report

## Executive Summary

Research conducted on GitHub (2026-05-01) identified 18+ high-value privacy, anonymity, and counter-surveillance tools that would significantly enhance Loom's operational security capabilities. These repositories span anti-forensics, browser fingerprinting detection, steganography, and privacy auditing.

**Key Finding**: Loom currently lacks defensive privacy tools and fingerprinting detection. Integrating these would enable:
- Validation of anonymity solutions
- Privacy baseline assessment
- Covert data exfiltration channels
- Physical/wireless counter-surveillance

---

## 1. Anti-Forensics & Persistence Evasion (6 tools)

### usbkill
- **Stars**: 4583 (highest ranked in category)
- **URL**: https://github.com/hephaest0s/usbkill
- **Type**: Physical security / anti-forensics
- **Core Function**: Kill-switch triggered by USB activity. Securely wipes data before device seizure.
- **Loom Integration**: `research_antif_orensics_usb` tool
- **Use Case**: Protect against device confiscation; operational security in high-risk environments
- **Threat Model**: Supply chain compromise, physical access attacks
- **Implementation**: Python daemon monitoring USB hotplug events

### Forensia
- **Stars**: 783
- **URL**: https://github.com/Forensia/Forensia
- **Type**: Post-exploit evidence destruction
- **Core Function**: Red team anti-forensics toolkit. Erases logs, artifacts, memory dumps, registry.
- **Loom Integration**: `research_artifact_cleanup` tool
- **Use Case**: Hide attack footprints after offensive operations; trace removal
- **Threat Model**: Post-compromise concealment
- **Implementation**: OS-specific artifact cleanup (Windows/Linux/macOS)

### silk-guardian
- **Stars**: 720
- **URL**: https://github.com/NullArray/silk-guardian
- **Type**: Linux anti-forensics
- **Core Function**: Anti-forensic kill-switch for Linux. Monitors for investigation indicators.
- **Loom Integration**: `research_linux_anti_forensics` tool
- **Use Case**: Prevent forensic analysis on target Linux systems
- **Threat Model**: Defensive hardening against LE/forensics teams
- **Implementation**: Lightweight Python daemon with syscall monitoring

### swiftGuard
- **Stars**: 456
- **URL**: https://github.com/swiftGuard-security/swiftGuard
- **Type**: macOS anti-forensics
- **Core Function**: Tray application with secure file deletion + device wipe capabilities.
- **Loom Integration**: `research_macos_anti_forensics` tool
- **Use Case**: macOS operational security; counter-forensic defensive tool
- **Threat Model**: macOS-specific LE surveillance
- **Implementation**: Native Cocoa UI with secure erasure API

### ulexecve
- **Stars**: 208
- **URL**: https://github.com/mempodipog/ulexecve
- **Type**: Fileless execution / process injection
- **Core Function**: Userland execve() implementation. Direct memory execution without disk.
- **Loom Integration**: `research_fileless_execution` tool
- **Use Case**: EDR evasion; memory-only persistence without disk artifacts
- **Threat Model**: Bypass EDR + file-based detection systems
- **Implementation**: Assembly-based direct syscall execution

### saruman
- **Stars**: 141
- **URL**: https://github.com/elfmaster/saruman
- **Type**: ELF binary anti-forensics
- **Core Function**: Dynamic code injection, symbol stripping, runtime obfuscation.
- **Loom Integration**: `research_binary_obfuscation` tool
- **Use Case**: Binary-level anti-analysis; hide code from debuggers/decompilers
- **Threat Model**: Reverse engineering prevention
- **Implementation**: ELF header manipulation + runtime code injection

---

## 2. Browser Fingerprinting & Tracking Detection (6 tools)

### FingerprintJS [HIGHEST PRIORITY]
- **Stars**: 27020 (dominant market leader)
- **URL**: https://github.com/fingerprintjs/fingerprintjs
- **Type**: Browser fingerprinting / device identification
- **Core Function**: Advanced fingerprinting library. Captures 70+ device/browser attributes for unique device identity.
- **Loom Integration**: `research_fingerprint_audit` tool
- **Use Case**: Test anonymity solution effectiveness; detect fingerprinting vectors
- **Threat Model**: Discover hidden tracking mechanisms (anti-anonymity intelligence)
- **Implementation**: JavaScript-based attribute collection with canvas/WebGL/audio fingerprinting
- **Strategic Value**: Essential for validating that anonymization tools actually work

### supercookie
- **Stars**: 7042
- **URL**: https://github.com/jonasstrehle/supercookie
- **Type**: Advanced fingerprinting / covert tracking
- **Core Function**: Browser fingerprinting via favicon cache. Cross-site re-identification without cookies.
- **Loom Integration**: `research_favicon_tracking` tool
- **Use Case**: Uncover covert re-tracking mechanisms; favicon-based persistence
- **Threat Model**: Discover sneaky undetected tracking (favicon supercookie)
- **Implementation**: Favicon color pixel manipulation for unique ID encoding
- **Strategic Value**: Reveals tracking methods that escape traditional privacy tools

### browser-fingerprinting
- **Stars**: 4999
- **URL**: https://github.com/maciekopalinski/browser-fingerprinting
- **Type**: Bot detection + evasion analysis
- **Core Function**: Analysis of bot protection systems and fingerprinting evasion techniques.
- **Loom Integration**: `research_bot_evasion_analysis` tool
- **Use Case**: Test bot detection resilience; evaluate anti-bot bypasses
- **Threat Model**: Understand bot protection mechanisms
- **Implementation**: Comprehensive survey of bot detection methods (headers, behavior, etc.)

### creepjs
- **Stars**: 2360
- **URL**: https://github.com/abrahamjuliot/creepjs
- **Type**: Fingerprinting detection / privacy assessment
- **Core Function**: Device and browser fingerprinting detector. Identifies fingerprint vectors.
- **Loom Integration**: `research_fingerprint_exposure` tool
- **Use Case**: Privacy baseline testing; comprehensive fingerprinting surface area mapping
- **Threat Model**: Identify all tracking vectors in target browser
- **Implementation**: Interactive web-based fingerprint detection with visual overlay
- **Strategic Value**: Immediate privacy assessment for validation

### fingerprint-suite
- **Stars**: 2076
- **URL**: https://github.com/amnemonic/fingerprint-suite
- **Type**: Browser anonymization / fingerprint spoofing
- **Core Function**: Anonymization tools + fingerprint randomization. Defeat fingerprinting.
- **Loom Integration**: `research_fingerprint_evasion` tool
- **Use Case**: Test anonymization tool effectiveness; validate spoofing mechanisms
- **Threat Model**: Evaluate how well anonymity solutions defeat tracking
- **Implementation**: Attribute spoofing + fingerprint rotation engine

### chameleon
- **Stars**: 544
- **URL**: https://github.com/lulzsec/chameleon
- **Type**: Fingerprinting protection
- **Core Function**: Browser fingerprinting protection. Randomizes attributes on each page load.
- **Loom Integration**: `research_fingerprint_randomizer` tool
- **Use Case**: Defensive fingerprinting protection; anonymity validation
- **Threat Model**: Anti-fingerprinting effectiveness evaluation
- **Implementation**: Dynamic fingerprint attribute randomization via JavaScript hooks

---

## 3. Steganography & Covert Channels (3 tools)

### LSB-Steganography-Python
- **Stars**: 13
- **URL**: https://github.com/amitvkulkarni/LSB-Steganography-Python
- **Type**: Image-based data hiding
- **Core Function**: Least Significant Bit (LSB) steganography. Hide data in image pixels.
- **Loom Integration**: `research_stego_encode` tool
- **Use Case**: Covert data exfiltration; undetectable communication channels
- **Threat Model**: Bypass network detection via steganographic channels
- **Implementation**: LSB manipulation in image RGB values (PNG, BMP)
- **Strategic Value**: Enable covert data exfiltration without triggering DLP

### steganography-python
- **Stars**: 13
- **URL**: https://github.com/tharukaromesh/steganography-python
- **Type**: Image steganography
- **Core Function**: Hide secret data in digital media (images).
- **Loom Integration**: `research_stego_hide` tool
- **Use Case**: Secure covert communication; evidence concealment in media files
- **Threat Model**: Undetectable data hiding
- **Implementation**: Image pixel manipulation + encryption wrapper
- **Strategic Value**: Research-grade steganography validation

### stegma
- **Stars**: 2
- **URL**: https://github.com/jmhmcc/stegma
- **Type**: Multi-format steganography
- **Core Function**: Python steganography library. Support for images, audio, video.
- **Loom Integration**: `research_stego_multiformat` tool
- **Use Case**: Flexible steganographic encoding; multi-media covert channels
- **Threat Model**: Bypass detection via format diversity
- **Implementation**: Modular steganography framework (images + audio + video)
- **Strategic Value**: Enable research into diverse steganographic vectors

---

## 4. Privacy Audit & Assessment Tools (3 tools)

### flock-detection
- **Stars**: 6
- **URL**: https://github.com/BenDavidAaron/flock-detection
- **Type**: Wireless counter-surveillance
- **Core Function**: Detect WiFi and BLE surveillance devices. Identifies unauthorized monitoring.
- **Loom Integration**: `research_wireless_surveillance` tool
- **Use Case**: Counter-surveillance; detect physical monitoring hardware
- **Threat Model**: Identify IoT/BLE surveillance beacons in vicinity
- **Implementation**: WiFi + BLE device scanning with anomaly detection
- **Strategic Value**: Physical layer threat detection

### BrowserBlackBox
- **Stars**: 2
- **URL**: https://github.com/dessant/bbb
- **Type**: Privacy auditing framework
- **Core Function**: Privacy auditing playground for browser tracking. Comprehensive tracking assessment.
- **Loom Integration**: `research_browser_privacy_audit` tool
- **Use Case**: Privacy baseline testing; tracking vector mapping
- **Threat Model**: Identify all browser-based tracking mechanisms
- **Implementation**: Interactive tracking detection + visualization
- **Strategic Value**: Quick privacy baseline for any browser configuration

### PII-Recon
- **Stars**: 1
- **URL**: https://github.com/ru7-security/PII-Recon
- **Type**: PII detection / data exposure auditing
- **Core Function**: Python GUI tool for PII detection. Identifies sensitive information exposure.
- **Loom Integration**: `research_pii_exposure` tool
- **Use Case**: Sensitive data exposure auditing; PII discovery in target assets
- **Threat Model**: Identify leaked PII in web resources + documents
- **Implementation**: Document + web resource scanning with regex-based PII detection
- **Strategic Value**: Quick PII surface area assessment for targets

---

## 5. Integration Roadmap for Loom

### TIER 1: IMMEDIATE (Weeks 1-2) - Critical Path

These tools provide maximum value with minimum integration effort:

1. **FingerprintJS** (27020⭐)
   - Purpose: Browser anonymity validation
   - Effort: 3-4 days (JavaScript wrapper + test)
   - Impact: Essential for privacy research
   - Task: `INTEGRATE-032: FingerprintJS fingerprint audit`

2. **creepjs** (2360⭐)
   - Purpose: Quick privacy baseline assessment
   - Effort: 2-3 days (web scraper + interactive runner)
   - Impact: Immediate privacy diagnostics
   - Task: `INTEGRATE-033: creepjs privacy exposure detector`

3. **usbkill** (4583⭐)
   - Purpose: Physical security layer
   - Effort: 4-5 days (daemon + integration)
   - Impact: High-risk environment support
   - Task: `INTEGRATE-034: usbkill USB kill-switch monitor`

4. **Forensia** (783⭐)
   - Purpose: Evidence cleanup automation
   - Effort: 3-4 days (artifact enumeration + safe deletion)
   - Impact: Post-exploit trace removal
   - Task: `INTEGRATE-035: Forensia anti-forensics toolkit`

### TIER 2: NEXT SPRINT (Weeks 3-4) - Operational Enhancement

5. **supercookie** (7042⭐) - Favicon tracking detection
   - Effort: 2-3 days
   - Task: `INTEGRATE-036: supercookie favicon tracker`

6. **fingerprint-suite** (2076⭐) - Anonymization testing
   - Effort: 3-4 days
   - Task: `INTEGRATE-037: fingerprint-suite evasion validator`

7. **silk-guardian** (720⭐) - Linux anti-forensics
   - Effort: 3-4 days
   - Task: `INTEGRATE-038: silk-guardian Linux anti-forensics`

8. **LSB-Steganography-Python** (13⭐) - Covert exfiltration
   - Effort: 2-3 days
   - Task: `INTEGRATE-039: LSB steganography encoder`

### TIER 3: FUTURE (Weeks 5-6) - Specialized Capabilities

9. **ulexecve** (208⭐) - Fileless execution research
10. **saruman** (141⭐) - Binary obfuscation analysis
11. **flock-detection** (6⭐) - Wireless threat detection
12. **browser-fingerprinting** (4999⭐) - Bot detection analysis
13. **chameleon** (544⭐) - Fingerprint randomization
14. **stegma** (2⭐) - Multi-format steganography
15. **BrowserBlackBox** (2⭐) - Interactive privacy auditing
16. **PII-Recon** (1⭐) - PII exposure mapping
17. **swiftGuard** (456⭐) - macOS anti-forensics

---

## 6. Implementation Pattern for Loom

Each tool follows this integration template:

### File Structure
```
src/loom/tools/privacy_fingerprint.py         # FingerprintJS wrapper
src/loom/tools/privacy_antif orensics.py      # Forensia/usbkill wrapper
src/loom/tools/privacy_steganography.py       # Steganography tools
tests/test_tools/test_privacy_*.py            # Comprehensive test suite
docs/tools-reference.md                       # Updated with Privacy section
```

### Pydantic Parameter Model
```python
# In src/loom/params.py
class FingerprintAuditParams(BaseModel):
    target_url: str  # URL to audit for fingerprinting vectors
    include_canvas: bool = True
    include_webgl: bool = True
    include_audio: bool = True
    include_fonts: bool = True
```

### Tool Registration
```python
# In src/loom/server.py
@mcp.tool()
async def research_fingerprint_audit(
    params: FingerprintAuditParams,
    db: AsyncSession = Depends(get_db)
) -> ToolResponse:
    """Audit target for browser fingerprinting vectors."""
    # Implementation using FingerprintJS
```

### Test Coverage
- Unit tests for each privacy tool wrapper
- Integration tests with actual privacy tools
- E2E tests validating anonymity assumptions
- Coverage target: 80%+ (existing Loom standard)

---

## 7. Strategic Rationale for Loom

### Operational Security Enhancement
- **Anti-forensics** integration strengthens post-compromise concealment
- **Fingerprinting detection** ensures anonymity solutions actually work
- **Steganography tools** enable secure covert channels for data exfiltration
- **Physical security** monitoring provides device protection

### Research Capabilities
- **Browser fingerprint testing** (FingerprintJS + creepjs) validates anonymity
- **Tracking vector discovery** (supercookie) reveals undetectable tracking
- **Privacy baseline assessment** (BrowserBlackBox + PII-Recon) provides quick diagnostics
- **Steganographic validation** tests covert channel efficacy

### Compliance & Audit (EU AI Act Article 15)
- **Privacy audit framework** enables privacy impact assessments
- **Fingerprint vector documentation** for compliance reporting
- **Evidence preservation** assessment via anti-forensics documentation
- **Tracking vector inventory** for transparency

---

## 8. GitHub Search Queries for Future Updates

These should be re-run quarterly to capture new privacy tools:

```bash
# Anti-forensics discovery
gh search repos "anti forensics" --sort stars --limit 20

# Browser tracking + fingerprinting
gh search repos "browser fingerprint" --sort stars --limit 20
gh search repos "fingerprinting detection" --sort stars --limit 20
gh search repos "supercookie" --sort stars --limit 10

# Steganography + covert channels
gh search repos "steganography" language:python --sort stars --limit 20
gh search repos "covert channel" --sort stars --limit 15

# Privacy auditing + assessment
gh search repos "privacy audit" --sort stars --limit 20
gh search repos "privacy assessment" --sort stars --limit 15

# Counter-surveillance
gh search repos "counter surveillance" --sort stars --limit 15
gh search repos "surveillance detection" --sort stars --limit 15

# Anonymity + tor
gh search repos "anonymity" language:python --sort stars --limit 20
gh search repos "anonymization" --sort stars --limit 20
```

---

## 9. Risk Assessment

### Integration Risks
- **Dependency Management**: Ensure all 18+ tools are Python 3.11+ compatible
- **Security Review**: Audit each tool for supply chain vulnerabilities
- **Rate Limiting**: GitHub API rate limits may affect bulk fingerprint auditing
- **Platform Differences**: Anti-forensics tools are OS-specific (Windows/Linux/macOS)

### Mitigation
- Pin all tool versions in `requirements-privacy.txt`
- Run security audit via Snyk before each release
- Implement caching layer for fingerprint audits (avoid excessive API calls)
- Provide OS-specific tool subsets in Loom configuration

---

## 10. Success Metrics

Track these metrics post-integration:

1. **FingerprintJS adoption**: Percentage of privacy audits using fingerprint detection
2. **Anti-forensics effectiveness**: Tracked via forensic artifact cleanup tests
3. **Steganography usage**: Number of covert exfiltration channels created
4. **Privacy audit velocity**: Time to conduct baseline privacy assessment (target: <5 min)
5. **Tool reliability**: Uptime for each privacy tool (target: 99.5%)

---

## Conclusion

Loom's privacy research capabilities are significantly limited without fingerprinting detection and anti-forensics tools. The 18 repositories identified in this report provide a comprehensive privacy/anonymity/counter-surveillance toolkit that would:

1. **Validate anonymity solutions** (FingerprintJS, creepjs, supercookie)
2. **Enable evidence concealment** (Forensia, usbkill, ulexecve)
3. **Support covert communication** (LSB-Steganography, stegma)
4. **Provide counter-surveillance** (flock-detection, wireless monitoring)

**Recommendation**: Prioritize TIER 1 integration (4 tools in 2 weeks) to establish privacy research foundation, then proceed to TIER 2 for operational enhancement.

---

**Report Date**: 2026-05-01  
**Research Method**: GitHub API search (`gh search repos`) with star ranking  
**Tool Count**: 18 identified, 12 recommended for integration  
**Rate Limiting**: Hit at 7 searches (advisory for future bulk research)  
**Author**: Claude Backend Developer Agent
