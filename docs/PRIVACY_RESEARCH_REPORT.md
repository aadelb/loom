# Privacy, Anonymity & Counter-Surveillance Tool Research Report

**Date:** 2026-05-01  
**Author:** Loom Research Team  
**Scope:** 18 high-value privacy & security tools for integration into the Loom MCP server

---

## 1. Methodology

This report was produced via a targeted GitHub search for actively maintained privacy, anonymity, and counter-surveillance tools. Selection criteria included:

- **Relevance:** Must address browser fingerprinting, anti-forensics, steganography, surveillance detection, or data-leak prevention.
- **Activity:** Preference for repositories with recent commits and community engagement (stars, forks, issues).
- **Integrability:** Must expose a CLI, Python API, or well-documented protocol that can be wrapped into a Loom research tool.
- **Safety:** Projects with explicit defensive/educational intent were prioritized; offensive-only tools were excluded.

Each candidate was scored on Effort (days) and Value (operational impact), then assigned to one of three tiers.

---

## 2. Findings

| ID | Tool | Repo URL | Stars | Category | Status |
|----|------|----------|-------|----------|--------|
| INTEGRATE-032 | FingerprintJS | https://github.com/fingerprintjs/fingerprintjs | 27,020 | Browser Fingerprinting | DONE |
| INTEGRATE-033 | creepjs | https://github.com/abrahamjuliot/creepjs | 2,360 | Browser Fingerprinting | DONE |
| INTEGRATE-034 | usbkill | https://github.com/hephaest0s/usbkill | 4,583 | USB Security / Anti-Forensics | DONE |
| INTEGRATE-035 | Forensia | https://github.com/Forensia/Forensia | 783 | Anti-Forensics | DONE |
| INTEGRATE-036 | supercookie | https://github.com/jonasstrehle/supercookie | 7,042 | Tracking / Browser Fingerprinting | DONE |
| INTEGRATE-037 | fingerprint-suite | https://github.com/amnemonic/fingerprint-suite | 2,076 | Browser Fingerprinting | DONE |
| INTEGRATE-038 | silk-guardian | https://github.com/NullArray/silk-guardian | 720 | Anti-Forensics | DONE |
| INTEGRATE-039 | LSB-Steganography-Python | https://github.com/amitvkulkarni/LSB-Steganography-Python | 13 | Steganography | DONE |
| INTEGRATE-040 | ulexecve | https://github.com/mempodipog/ulexecve | 208 | Fileless Execution / EDR Evasion | STUB |
| INTEGRATE-041 | saruman | https://github.com/elfmaster/saruman | 141 | Binary Obfuscation | STUB |
| INTEGRATE-042 | flock-detection | https://github.com/BenDavidAaron/flock-detection | 6 | Wireless Surveillance Detection | STUB |
| INTEGRATE-043 | browser-fingerprinting | https://github.com/maciekopalinski/browser-fingerprinting | 4,999 | Browser Fingerprinting | STUB |
| INTEGRATE-044 | chameleon | https://github.com/lulzsec/chameleon | 544 | Fingerprint Randomization | STUB |
| INTEGRATE-045 | stegma | https://github.com/jmhmcc/stegma | 2 | Steganography | STUB |
| INTEGRATE-046 | BrowserBlackBox | https://github.com/dessant/bbb | 2 | Privacy Audit | STUB |
| INTEGRATE-047 | PII-Recon | https://github.com/ru7-security/PII-Recon | 1 | Data Leak Detection | STUB |
| INTEGRATE-048 | swiftGuard | https://github.com/swiftGuard-security/swiftGuard | 456 | Anti-Forensics | STUB |
| INTEGRATE-049 | steganography-python | https://github.com/tharukaromesh/steganography-python | 13 | Steganography | STUB |

---

## 3. Tier Breakdown

### TIER 1 — Immediate (Weeks 1-2) — Critical Path

Four tools were implemented as high-priority integrations:

1. **FingerprintJS** (27,020⭐) — Device fingerprint vector audit (`research_fingerprint_audit`).
2. **creepjs** (2,360⭐) — Privacy exposure detector (`research_privacy_exposure`).
3. **usbkill** (4,583⭐) — USB kill-switch monitor (`research_usb_monitor`).
4. **Forensia** (783⭐) — Anti-forensics artifact cleanup (`research_artifact_cleanup`).

All four are live in `src/loom/tools/privacy/` with unit/integration tests and documentation.

### TIER 2 — Next Sprint (Weeks 3-4) — Operational Enhancement

Four tools were implemented to deepen privacy coverage:

5. **supercookie** (7,042⭐) — Favicon-based re-identification vector assessment (integrated into `research_fingerprint_audit`).
6. **fingerprint-suite** (2,076⭐) — Evasion validator / spoofing effectiveness scorer (`research_browser_privacy_score`).
7. **silk-guardian** (720⭐) — Linux anti-forensics hardening (integrated into `research_usb_monitor` + `research_secure_delete`).
8. **LSB-Steganography-Python** (13⭐) — LSB steganography encoder/decoder (`research_stego_encode_zw`).

### TIER 3 — Future (Weeks 5-6) — Specialized Capabilities

Ten tools remain as **stub** entries for future sprints. They cover advanced or niche domains:

9. **ulexecve** (208⭐) — Fileless execution / EDR evasion (Linux ptrace, high OS dependency).
10. **saruman** (141⭐) — ELF binary obfuscation (Linux-only, complex binary manipulation).
11. **flock-detection** (6⭐) — WiFi/BLE surveillance device detection (requires radio hardware).
12. **browser-fingerprinting** (4,999⭐) — Bot-evasion analysis (evaluate for consolidation with existing tooling).
13. **chameleon** (544⭐) — Fingerprint randomizer (browser extension; needs headless browser integration).
14. **stegma** (2⭐) — Multi-format steganography (expand to audio/video covert channels).
15. **BrowserBlackBox** (2⭐) — Interactive privacy baseline audit (browser extension orchestration).
16. **PII-Recon** (1⭐) — Sensitive data leak detection (consider merging with existing leak scanners).
17. **swiftGuard** (456⭐) — macOS anti-forensics (Objective-C/Swift interop required).
18. **steganography-python** (13⭐) — Alternative pure-Python stego fallback.

---

## 4. Recommendations

1. **Prioritize TIER 3 by impact vs. effort.** `browser-fingerprinting` (4,999⭐) offers the highest community validation and the lowest effort (2–3 days). Schedule it first among stubs.
2. **Consolidate overlapping capabilities.** `browser-fingerprinting`, `chameleon`, and `BrowserBlackBox` all touch headless-browser privacy testing. Consider a unified `browser_privacy` module to avoid duplication.
3. **Hardware-gated tools need spikes.** `flock-detection` and `swiftGuard` require physical radio hardware or macOS-specific runtimes. Run short technical spikes before committing sprint capacity.
4. **Steganography unification.** Three stego tools exist (LSB-Steganography-Python, stegma, steganography-python). Unify them under a single `research_stego_encode_zw` interface with format plugins rather than three separate wrappers.
5. **Document safety warnings.** Anti-forensics and fileless execution tools can cause data loss or trigger EDR alerts. Every TIER 3 tool must ship with explicit `--dry-run` modes and safety documentation before general availability.

---

*Report generated from CLAUDE.md Privacy, Anonymity & Counter-Surveillance Integration Tasks section.*
