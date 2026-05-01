# Network Forensics Tools Integration — Executive Summary

**Date:** 2026-05-01  
**Scope:** 15 Missing GitHub repos, 29 MCP tools  
**Effort:** 287 hours (~6-8 weeks at 40h/week)  
**Priority:** Phase 1 (6 tools) = P1, Phase 2-3 (15 tools) = P2, Phase 4 (8 tools) = P3+  

---

## What's Missing

Loom currently has **318 MCP tools** across 29 integrated GitHub repos. However, critical gaps remain in:

### 1. Packet-Level Network Analysis (0 tools)
No Python tools for crafting/analyzing raw packets. Current toolkit lacks:
- Custom packet construction (Scapy)
- PCAP forensic analysis (PyShark)
- Intrusion detection on traffic (Zeek)

### 2. TLS/SSL Auditing (1 tool)
Only `cert_analyzer.py` exists. Missing:
- Comprehensive TLS configuration audit (testssl.sh)
- Certificate chain validation (openssl)
- Cipher strength assessment

### 3. Web Application Security (0 tools)
No active/passive web scanning. Missing:
- OWASP top-10 vulnerability scanning (ZAP)
- Web application crawling & reconnaissance

### 4. Advanced DNS Enumeration (1 tool)
Only ProjectDiscovery tools. Missing:
- Zone transfers & DNS reconnaissance (DNSRecon)
- Lightweight subdomain discovery (Fierce)

### 5. GPU-Accelerated Cryptanalysis (0 tools)
No hash cracking capabilities. Missing:
- Large-scale hash cracking (Hashcat)
- Wireless security forensics (Aircrack-ng)

---

## Gap Analysis: What You Get

### Priority 1 (Core) — 70 hours, Immediate Value
1. **Scapy** (2 tools) — packet crafting + PCAP analysis
   - `research_packet_craft` — custom packet construction
   - `research_packet_analyze` — PCAP statistics & protocol breakdown
2. **PyShark** (2 tools) — Wireshark integration
   - `research_packet_decode` — detailed packet layer parsing
   - `research_pcap_analyze` — flow-based traffic analysis
3. **Zeek** (2 tools) — network IDS/IPS integration
   - `research_zeek_ids_analyze` — run Zeek IDS on PCAP
   - `research_zeek_log_parse` — parse conn.log, ssl.log, http.log, dns.log

**Impact:** Real-time network forensics, intrusion detection, packet-level investigation  
**Use Cases:** Incident response, malware analysis, network troubleshooting

---

### Priority 2 (TLS & Web Security) — 50 hours, Critical Compliance
4. **testssl.sh** (2 tools) — TLS/SSL auditing
   - `research_testssl_analyze` — full TLS configuration audit
   - `research_tls_cert_chain` — certificate chain validation
5. **OWASP ZAP** (2 tools) — web application security
   - `research_zaproxy_scan` — active/passive web vulnerability scanning
   - `research_zaproxy_spider` — application crawling & reconnaissance

**Impact:** Compliance with PCI-DSS, SSL/TLS best practices, OWASP top-10 assessment  
**Use Cases:** Security audits, compliance reporting, web app penetration testing

---

### Priority 3 (Network Reconnaissance) — 50 hours, Operational Intelligence
6. **DNSRecon** (2 tools) — advanced DNS enumeration
   - `research_dns_recon` — multi-technique DNS reconnaissance
   - `research_dns_brute` — subdomain brute-forcing
7. **Masscan** (2 tools) — high-speed port scanning
   - `research_masscan_full_scan` — massive scale TCP/UDP scanning
   - `research_masscan_udp_scan` — UDP-specific reconnaissance
8. **Fierce** (1 tool) — lightweight DNS discovery
   - `research_fierce_subdomain_scan` — quick subdomain enumeration
9. **NetBox** (2 tools) — IP address management
   - `research_netbox_device_query` — IPAM device lookup
   - `research_netbox_ip_lookup` — IP address reservation tracking

**Impact:** Comprehensive network mapping, fast large-scale scanning, infrastructure discovery  
**Use Cases:** Security assessment, network planning, threat intelligence gathering

---

### Priority 4 (Security Monitoring) — 40 hours, Operational Visibility
10. **osquery** (2 tools) — host-level intrusion detection
    - `research_osquery_host_monitor` — query host state (processes, network, files)
    - `research_osquery_audit` — enable/parse endpoint detection & response logs
11. **Suricata** (2 tools) — IDS/IPS engine integration
    - `research_suricata_ids_scan` — run Suricata on PCAP/live
    - `research_suricata_alert_parse` — parse Suricata eve.json alerts
12. **Zabbix** (2 tools) — network monitoring metrics
    - `research_zabbix_metric_query` — retrieve historical metrics
    - `research_zabbix_event_monitor` — retrieve alerts & events
13. **ntopng** (2 tools) — real-time traffic monitoring
    - `research_ntop_traffic_analyze` — flow statistics & bandwidth
    - `research_ntop_stats` — device & interface statistics

**Impact:** 24/7 operational monitoring, anomaly detection, event correlation  
**Use Cases:** NOC monitoring, continuous compliance, SLA tracking

---

### Priority 5 (Cryptanalysis) — 30 hours, Advanced (Optional)
14. **Hashcat** (2 tools) — GPU-accelerated hash cracking
    - `research_hashcat_crack` — large-scale hash cracking
    - `research_hashcat_benchmark` — hash cracking performance testing
15. **Aircrack-ng** (2 tools) — wireless security forensics
    - `research_aircrack_capture_analyze` — parse .cap wireless captures
    - `research_aircrack_key_recovery` — WPA2/WPA3 key recovery

**Impact:** Cryptographic analysis, password recovery, wireless forensics  
**Use Cases:** Forensic investigation, wireless security assessment

---

## Integration Timeline

```
Week 1-2: P1 (Scapy, PyShark, Zeek)                    70h
  └─ Network forensics foundation
  └─ Real-time IDS integration
  └─ Packet-level analysis capability

Week 2-3: P2 (testssl.sh, OWASP ZAP)                   50h
  └─ TLS/SSL compliance auditing
  └─ Web application security testing
  └─ OWASP top-10 vulnerability scanning

Week 3-4: P3 (DNSRecon, Masscan, Fierce, NetBox)       50h
  └─ Large-scale network reconnaissance
  └─ Infrastructure discovery & mapping
  └─ IP address management integration

Week 4-5: P4 (osquery, Suricata, Zabbix, ntopng)       40h
  └─ Host-level intrusion detection
  └─ Continuous monitoring & alerting
  └─ Operational visibility

Week 5+: P5 (Hashcat, Aircrack-ng) [OPTIONAL]          30h
  └─ Advanced cryptanalysis
  └─ GPU-accelerated password cracking
  └─ Wireless forensics

Cross-cutting (testing, docs, security):               47h
  └─ Parameter models, server registration
  └─ 80%+ test coverage across all tools
  └─ Security validation & deployment
```

---

## Cost Impact

### Credit System
Each tool assigned credit cost (1-10 credits):

| Tool Category | Weight | Example Tools | Cost |
|---|---|---|---|
| Lightweight (API/parsing) | 1-2 | NetBox, Zabbix | 1-2 cr |
| Medium (subprocess, I/O) | 3-5 | Scapy, PyShark, DNSRecon | 3-5 cr |
| Heavy (network scanning, IDS) | 5-10 | Masscan, testssl, Zeek, ZAP | 5-10 cr |

### Monthly Allocation
- **Free tier** (500 credits): ~50-100 network investigations/month
- **Pro tier** (10K credits): ~1000-2000 investigations/month
- **Team tier** (50K credits): Full operational use
- **Enterprise tier** (200K credits): Unlimited

---

## Security Considerations

### Input Validation (CRITICAL)
✓ All domains/IPs validated against injection attacks  
✓ No shell metacharacters allowed in any parameter  
✓ Path traversal prevention (no `..` in file paths)  
✓ Port validation (1-65535 numeric only)  

### Command Execution Safety
✓ All subprocess calls use `shell=False`  
✓ Binary availability checked at registration time  
✓ Timeouts enforced (<60s per network operation)  
✓ Error messages sanitized (no stack traces)  

### Privilege Requirements
⚠ Raw socket operations (Scapy) require CAP_NET_RAW or root  
⚠ Wireless tools (Aircrack-ng) require elevated privileges  
✓ Graceful degradation if permissions denied  

### API Key Protection
✓ All API credentials from environment variables or config  
✓ Never logged in output or error messages  
✓ Audit logging redacts sensitive parameters  

---

## Deployment Checklist

### Pre-Deployment
- [ ] All 29 tools implemented & unit tested
- [ ] 80%+ code coverage across all new tools
- [ ] Security review: input validation, command injection, SSRF
- [ ] Integration tests: journey workflows passing
- [ ] Documentation: all 29 tools in tools-reference.md + help.md

### Deployment
- [ ] Binary dependencies installed on all servers
- [ ] Environmental variables configured (.env.production)
- [ ] Tool registration verified in server startup logs
- [ ] Monitoring alerts configured for tool failures

### Post-Deployment
- [ ] Gradual rollout: beta → 10% users → 50% → 100%
- [ ] Monitor error rates, latency, credit usage
- [ ] Collect user feedback on new tools
- [ ] Version tag: v0.1.0-alpha.3
- [ ] Update CLAUDE.md with new tool count (347)

---

## What You Can Do After Integration

### Day 1: Packet Forensics
```
# Analyze captured network traffic
research_packet_analyze(pcap_file="incident.pcap")
→ Detect unusual protocols, top talkers, connections

# Deep dive into suspicious traffic
research_packet_decode(pcap_file="incident.pcap", packet_index=42)
→ Full protocol layers (Ethernet, IP, TCP, HTTP, DNS)
```

### Day 2: TLS Vulnerability Audit
```
# Audit target's SSL configuration
research_testssl_analyze(hostname="api.example.com")
→ Weak ciphers, protocol downgrade attacks, missing HSTS

# Validate certificate chain
research_tls_cert_chain(hostname="api.example.com")
→ Certificate pinning issues, expired certs, trust path problems
```

### Day 3: Web Application Assessment
```
# Scan for OWASP top-10
research_zaproxy_scan(target_url="https://example.com", scan_type="active")
→ SQL injection, XSS, CSRF, weak authentication, etc.

# Crawl application structure
research_zaproxy_spider(target_url="https://example.com")
→ Hidden pages, forms, external links, crawl paths
```

### Day 4-5: Network Reconnaissance
```
# Enumerate all subdomains
research_dns_recon(hostname="example.com")
→ Zone transfers, MX records, TXT records, DNSSEC info

# Large-scale port scanning
research_masscan_full_scan(target_ip="203.0.113.0/24", ports="1-65535")
→ Find all open ports across subnet in seconds (vs hours with nmap)
```

### Week 2: Incident Response
```
# Extract host-level forensics
research_osquery_host_monitor(query_type="processes")
→ Running processes, open files, network connections, installed software

# Correlate with network IDS
research_zeek_ids_analyze(pcap_file="incident.pcap")
→ Intrusion detection signatures, anomalous flows, protocol violations
```

### Week 3-4: Continuous Monitoring
```
# Track network metrics
research_zabbix_metric_query(hostname="server-01", metric_name="cpu_usage", time_range="7d")
→ Detect anomalies, capacity planning, trend analysis

# Real-time traffic monitoring
research_ntop_traffic_analyze(interface="eth0")
→ Bandwidth hogs, protocol distribution, flow analysis
```

---

## Known Limitations

### P1 Packet Analysis
- Scapy requires `libpcap` (Linux) or WinPcap (Windows)
- PyShark requires tshark binary (from Wireshark)
- Zeek configuration/rules are fixed (no custom rules for security)

### P2 TLS Tools
- testssl.sh is Bash (runs on Linux/macOS only)
- Certificate validation uses system CA store (may differ across systems)
- OCSP stapling detection is optional

### P3 Reconnaissance
- Masscan is AGPL-3.0 licensed (check org compliance)
- DNSRecon requires DNSSEC support on target
- Zone transfers may be blocked by firewalls

### P4 Monitoring
- osquery and Suricata require daemon processes running
- Zabbix/ntopng require external server infrastructure
- Some metrics may be unavailable in restricted environments

### P5 Cryptanalysis
- Hashcat requires GPU (NVIDIA CUDA/AMD HIP)
- Aircrack-ng requires wireless adapter + driver support
- Both tools have high CPU/memory overhead

---

## FAQ

**Q: Do I need to integrate all 15 repos?**  
A: No. P1 (6 tools) are critical and recommended. P2-P3 add operational value. P4-P5 are optional based on use case.

**Q: What's the minimum viable set?**  
A: Scapy + PyShark + testssl.sh = 5 tools, covers 80% of network forensics needs. Effort: ~35h.

**Q: Can I deploy P1 first, then P2-P4 later?**  
A: Absolutely. Each phase is independent. Staging P1 alone for 2 weeks, then rolling in P2-P3 over time is a valid approach.

**Q: Will this slow down the server?**  
A: No. All tools are async and non-blocking. Heavy operations (IDS, web scanning) run in subprocess pools with timeouts.

**Q: Do I need GPU support?**  
A: Only for Hashcat (optional P5). Hashcat can fall back to CPU (slower). Aircrack-ng is niche (deferred).

**Q: What's the storage impact?**  
A: PCAP files can be large (100s MB). Cache storage for analysis results: ~1KB per record. Monitor cache size on Hetzner.

**Q: Can I customize tool parameters?**  
A: Yes. All tools use Pydantic models in `params.py`. Modify constraints, add fields, or remove features as needed.

---

## Next Steps

1. **Review** this summary + detailed specs
2. **Prioritize** which repos matter most for your use case
3. **Validate** binary dependencies on your infrastructure
4. **Plan** sprints: P1 first, then P2-P3 in parallel/sequence
5. **Assign** implementation tasks (sprints, estimated 287h total)
6. **Test** thoroughly: unit + integration + security
7. **Deploy** to staging, collect feedback, then production

---

## Documents Created

1. **NETWORK_FORENSICS_INTEGRATION_RESEARCH.md** — Comprehensive research report
   - 15 repos analyzed, priority matrix, dependency matrix, gap analysis
   - Implementation roadmap & effort estimates

2. **NETWORK_TOOLS_IMPLEMENTATION_SPEC.md** — Technical implementation guide
   - Complete function signatures, parameter models, return schemas
   - Cost estimates, security checklist, testing templates

3. **NETWORK_TOOLS_TODO.md** — Actionable task breakdown
   - Sprint-based task list (SCAPY-001, PYSHARK-001, etc.)
   - Cross-cutting work (params, registration, testing, documentation)
   - Effort estimates per task, dependencies, success criteria

4. **NETWORK_TOOLS_SUMMARY.md** — This document
   - Executive summary, timeline, deployment checklist, FAQ

---

## Contacts & Resources

- **GitHub Repos**: See NETWORK_FORENSICS_INTEGRATION_RESEARCH.md section "References"
- **Loom Docs**: `CLAUDE.md`, `docs/tools-reference.md`, `docs/help.md`
- **Implementation Guide**: `NETWORK_TOOLS_IMPLEMENTATION_SPEC.md` (function-by-function)
- **Task Breakdown**: `NETWORK_TOOLS_TODO.md` (sprint planning)

---

**Status:** Research Complete ✓ | Implementation Ready ✓ | Deployment Pending ⏳

All 15 repos identified, analyzed, and scoped. Ready to begin P1 development.
