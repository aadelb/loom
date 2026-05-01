# Network Forensics & Infrastructure Mapping Research
## Loom Integration Roadmap for 15 Missing Tools (29 MCP Functions)

**Research Date:** 2026-05-01  
**Status:** Identified high-priority repos for integration  
**Integration Target:** Round 3 expansion (after current 318 tools)

---

## Executive Summary

Loom has integrated 29/44 planned GitHub repos with 318 total MCP tools. This research identifies **15 critical network forensics, packet analysis, and infrastructure monitoring tools** that provide gap coverage in:

1. **Packet-level analysis** (Scapy, PyShark, Zeek)
2. **Network reconnaissance** (Masscan, DNSRecon, Fierce)
3. **Security monitoring** (Suricata, Zeek, ntopng)
4. **Cryptographic analysis** (testssl.sh, Hashcat, Aircrack-ng)
5. **Infrastructure management** (NetBox, Zabbix, osquery)
6. **Web security testing** (OWASP ZAP)

These tools fill critical gaps in:
- Real-time traffic inspection & packet crafting
- Advanced DNS/subdomain enumeration
- TLS/SSL certificate chain analysis
- Host intrusion detection & monitoring
- Password hash cracking & cryptanalysis
- Wireless network security testing

---

## Missing Tools by Category

### 1. Packet-Level Analysis (3 repos, 6 tools)

#### **Scapy** (GitHub: secdev/scapy)
- **Type:** Python library (subprocess + library modes)
- **Stars:** ~10K | **Python:** 3.7+
- **Proposed Tools:**
  - `research_packet_craft` — Construct raw packets with custom headers/payloads
  - `research_packet_analyze` — Parse & dissect captured packets (binary data)
- **Use Case:** Forensic packet reconstruction, protocol fuzzing, network simulation
- **Integration Effort:** ⭐⭐⭐ (Medium — requires binary handling)
- **Loom Value:** High — unique low-level network capability

#### **PyShark** (GitHub: KimiTheCat/pyshark)
- **Type:** Python wrapper for Wireshark/tshark (subprocess mode)
- **Stars:** ~2K | **Python:** 3.6+
- **Proposed Tools:**
  - `research_packet_decode` — Decode PCAP/live packets to structured format
  - `research_pcap_analyze` — Statistical analysis of PCAP files
- **Use Case:** PCAP file analysis, protocol identification, forensic packet inspection
- **Integration Effort:** ⭐⭐⭐ (Medium — depends on tshark binary)
- **Loom Value:** High — integrates with Wireshark ecosystem

#### **Zeek** (GitHub: zeek/zeek)
- **Type:** C++ with Zeek scripting (subprocess + library modes)
- **Stars:** ~2.5K | **Requires:** Zeek 5.0+ binary, Python 3.8+
- **Proposed Tools:**
  - `research_zeek_ids_analyze` — Run Zeek IDS on PCAP/live traffic
  - `research_zeek_log_parse` — Parse Zeek conn.log, ssl.log, http.log
- **Use Case:** Network intrusion detection, connection analysis, SSL/TLS monitoring
- **Integration Effort:** ⭐⭐⭐⭐ (High — complex log parsing)
- **Loom Value:** Critical — enterprise-grade network security monitoring

---

### 2. Network Reconnaissance (3 repos, 5 tools)

#### **Masscan** (GitHub: robertdavidgraham/masscan)
- **Type:** C (subprocess mode only)
- **Stars:** ~24K | **Requires:** masscan binary
- **Proposed Tools:**
  - `research_masscan_full_scan` — Rapid TCP/UDP port scan (100K+ ports/sec)
  - `research_masscan_udp_scan` — UDP-only reconnaissance (DNS, SNMP, etc.)
- **Use Case:** Large-scale network discovery, incident response scanning
- **Integration Effort:** ⭐⭐ (Low — simple subprocess wrapper)
- **Loom Value:** Medium — faster than nmap but less detailed

#### **DNSRecon** (GitHub: darkoperator/dnsrecon)
- **Type:** Python script (subprocess mode)
- **Stars:** ~2.5K | **Python:** 2.7+ (legacy, needs Python 3 port)
- **Proposed Tools:**
  - `research_dns_recon` — Multi-technique DNS reconnaissance (AXFR, MX, NS, TXT)
  - `research_dns_brute` — Subdomain brute-forcing with custom wordlists
- **Use Case:** DNS infrastructure mapping, zone enumeration, DNSSEC analysis
- **Integration Effort:** ⭐⭐ (Low — subprocess wrapper)
- **Loom Value:** High — complements existing ProjectDiscovery tools

#### **Fierce** (GitHub: mschwager/fierce)
- **Type:** Python library + CLI (subprocess mode)
- **Stars:** ~3.5K | **Python:** 3.6+
- **Proposed Tools:**
  - `research_fierce_subdomain_scan` — Lightweight subdomain discovery (DNS + reverse lookup)
- **Use Case:** Quick DNS enumeration, zone transfer detection
- **Integration Effort:** ⭐⭐ (Low — library wrapper)
- **Loom Value:** Medium — lightweight alternative to heavy scanners

---

### 3. Cryptographic & TLS Analysis (4 repos, 8 tools)

#### **testssl.sh** (GitHub: drwetter/testssl.sh)
- **Type:** Bash script (subprocess mode)
- **Stars:** ~8K | **Requires:** openssl, timeout
- **Proposed Tools:**
  - `research_testssl_analyze` — Full TLS/SSL configuration audit
  - `research_tls_cert_chain` — Certificate chain validation & analysis
- **Use Case:** SSL/TLS vulnerability scanning, certificate forensics
- **Integration Effort:** ⭐⭐⭐ (Medium — JSON output parsing)
- **Loom Value:** High — complements cert_analyzer.py

#### **Hashcat** (GitHub: hashcat/hashcat)
- **Type:** C (CUDA/HIP accelerated, subprocess mode)
- **Stars:** ~19K | **Requires:** hashcat binary + GPU
- **Proposed Tools:**
  - `research_hashcat_crack` — GPU-accelerated hash cracking (MD5, SHA1/256, bcrypt, etc.)
  - `research_hashcat_benchmark` — Hash cracking performance benchmarking
- **Use Case:** Password hash analysis, forensic cryptanalysis
- **Integration Effort:** ⭐⭐⭐⭐ (High — GPU dependency, requires benchmark parsing)
- **Loom Value:** Medium — optional GPU acceleration, CPU fallback to hashlib

#### **Aircrack-ng** (GitHub: aircrack-ng/aircrack-ng)
- **Type:** C (subprocess mode)
- **Stars:** ~5K | **Requires:** aircrack-ng, airmon-ng, airodump-ng binaries
- **Proposed Tools:**
  - `research_aircrack_capture_analyze` — Parse .cap wireless packet captures
  - `research_aircrack_key_recovery` — WPA2/WPA3 key recovery from captures
- **Use Case:** Wireless security assessment, WiFi forensics
- **Integration Effort:** ⭐⭐⭐⭐⭐ (Very High — requires pcap handling + handshake parsing)
- **Loom Value:** Low — niche use case, complex binary interactions

---

### 4. Security Monitoring & Host Detection (4 repos, 6 tools)

#### **Suricata** (GitHub: OISF/suricata)
- **Type:** C with Lua (subprocess mode)
- **Stars:** ~2.5K | **Requires:** suricata binary + rules
- **Proposed Tools:**
  - `research_suricata_ids_scan` — Run Suricata IDS on PCAP/live
  - `research_suricata_alert_parse` — Parse Suricata eve.json alerts
- **Use Case:** IDS alerting, PCAP forensics, threat detection
- **Integration Effort:** ⭐⭐⭐ (Medium — eve.json parsing)
- **Loom Value:** High — enterprise IDS integration

#### **osquery** (GitHub: osquery/osquery)
- **Type:** C++ (subprocess mode, daemon mode optional)
- **Stars:** ~7.5K | **Requires:** osquery binary
- **Proposed Tools:**
  - `research_osquery_host_monitor` — Query host state (processes, network, files)
  - `research_osquery_audit` — Enable/parse audit logs (FIM, process execution)
- **Use Case:** Host-based intrusion detection, forensic host analysis
- **Integration Effort:** ⭐⭐⭐ (Medium — JSON SQL results parsing)
- **Loom Value:** High — cross-platform (Linux/macOS/Windows) host monitoring

#### **Zabbix** (GitHub: zabbix/zabbix)
- **Type:** C with agent (library + API mode)
- **Stars:** ~3K | **Requires:** Zabbix server API credentials
- **Proposed Tools:**
  - `research_zabbix_metric_query` — Query metrics from Zabbix API
  - `research_zabbix_event_monitor` — Retrieve Zabbix events & problem alerts
- **Use Case:** Network monitoring data extraction, event correlation
- **Integration Effort:** ⭐⭐⭐ (Medium — REST API wrapper)
- **Loom Value:** Medium — assumes Zabbix deployment exists

#### **ntopng** (GitHub: ntop/ntopng)
- **Type:** C/Lua (REST API mode)
- **Stars:** ~1K | **Requires:** ntopng server + API access
- **Proposed Tools:**
  - `research_ntop_traffic_analyze` — Query traffic statistics (flows, IPs, protocols)
  - `research_ntop_stats` — Retrieve device/interface statistics
- **Use Case:** Real-time traffic monitoring, flow analysis
- **Integration Effort:** ⭐⭐⭐ (Medium — REST API client)
- **Loom Value:** Medium — depends on ntopng deployment

---

### 5. Infrastructure Management (2 repos, 4 tools)

#### **NetBox** (GitHub: netbox-community/netbox)
- **Type:** Python Django (REST API mode)
- **Stars:** ~15K | **Requires:** NetBox server + API token
- **Proposed Tools:**
  - `research_netbox_device_query` — Query devices, IP addresses, interfaces
  - `research_netbox_ip_lookup` — IPAM lookup and availability checking
- **Use Case:** Network infrastructure discovery, IP address management
- **Integration Effort:** ⭐⭐ (Low — standard REST API wrapper)
- **Loom Value:** High — complements existing infrastructure tools

---

### 6. Web Security Testing (1 repo, 2 tools)

#### **OWASP ZAP** (GitHub: zaproxy/zaproxy)
- **Type:** Java (REST API mode)
- **Stars:** ~11K | **Requires:** ZAP daemon + API token
- **Proposed Tools:**
  - `research_zaproxy_scan` — Run active/passive web security scans
  - `research_zaproxy_spider` — Crawl and analyze web applications
- **Use Case:** Web application security testing, vulnerability scanning
- **Integration Effort:** ⭐⭐⭐ (Medium — REST API + XML parsing)
- **Loom Value:** High — enterprise web security integration

---

## Integration Priority Matrix

| Repo | Stars | Effort | Value | Priority | Notes |
|------|-------|--------|-------|----------|-------|
| **Scapy** | 10K | ⭐⭐⭐ | High | P1 | Foundational packet manipulation |
| **Zeek** | 2.5K | ⭐⭐⭐⭐ | Critical | P1 | Enterprise IDS, complex integration |
| **PyShark** | 2K | ⭐⭐⭐ | High | P1 | PCAP analysis, Wireshark integration |
| **Masscan** | 24K | ⭐⭐ | Medium | P2 | Fast reconnaissance scanning |
| **testssl.sh** | 8K | ⭐⭐⭐ | High | P1 | TLS/SSL vulnerability auditing |
| **NetBox** | 15K | ⭐⭐ | High | P2 | IP address management |
| **OWASP ZAP** | 11K | ⭐⭐⭐ | High | P1 | Web application security |
| **DNSRecon** | 2.5K | ⭐⭐ | High | P2 | DNS infrastructure mapping |
| **osquery** | 7.5K | ⭐⭐⭐ | High | P2 | Host-level intrusion detection |
| **Suricata** | 2.5K | ⭐⭐⭐ | High | P2 | IDS/IPS integration |
| **Fierce** | 3.5K | ⭐⭐ | Medium | P3 | Lightweight DNS enumeration |
| **Zabbix** | 3K | ⭐⭐⭐ | Medium | P3 | Network metrics (if deployed) |
| **ntopng** | 1K | ⭐⭐⭐ | Medium | P3 | Traffic flow analysis (if deployed) |
| **Hashcat** | 19K | ⭐⭐⭐⭐ | Medium | P3 | Hash cracking w/ GPU acceleration |
| **Aircrack-ng** | 5K | ⭐⭐⭐⭐⭐ | Low | P4 | Wireless security (niche) |

---

## Implementation Roadmap

### Phase 1: Core Packet Analysis (P1) — Week 1-2
- **Scapy**: Packet crafting + parsing
- **PyShark**: PCAP decoding + statistical analysis
- **Zeek**: IDS alerting + connection log parsing

### Phase 2: Cryptographic & TLS Tools (P1) — Week 2-3
- **testssl.sh**: TLS configuration audit + certificate chain validation
- **OWASP ZAP**: Web app scanning + spidering

### Phase 3: Network Reconnaissance (P2) — Week 3-4
- **DNSRecon**: DNS enumeration + zone transfers
- **Masscan**: Large-scale port scanning
- **Fierce**: Lightweight DNS discovery
- **NetBox**: IP address management integration

### Phase 4: Security Monitoring (P2) — Week 4-5
- **osquery**: Host monitoring + audit logging
- **Suricata**: IDS on PCAP + alert parsing
- **Zabbix**: Metrics query + event monitoring
- **ntopng**: Traffic statistics + flow analysis

### Phase 5: Advanced Cryptanalysis (P3+) — Week 5+
- **Hashcat**: GPU-accelerated hash cracking (optional, CPU fallback)
- **Aircrack-ng**: Wireless forensics (niche, deferred)

---

## Gap Analysis

### Currently Missing from Loom
1. **Low-level packet manipulation** — Scapy fills this gap
2. **Live traffic inspection** — PyShark + Zeek provide real-time analysis
3. **TLS configuration auditing** — testssl.sh + cert_analyzer complement each other
4. **DNS infrastructure mapping** — DNSRecon + Fierce + ProjectDiscovery tools
5. **Host-level IDS** — osquery provides EDR-like capabilities
6. **Wireless security** — Aircrack-ng covers WiFi forensics (low priority)
7. **GPU-accelerated cryptanalysis** — Hashcat for large-scale hash cracking

### Existing Overlaps (Avoid Duplication)
- **Port scanning**: nmap (existing) vs Masscan (faster, less detail)
  - **Decision**: Keep both — nmap for detail, masscan for speed
- **Subdomain enumeration**: ProjectDiscovery (subfinder, httpx) vs DNSRecon vs Fierce
  - **Decision**: All serve different purposes (httpx for HTTP probing, DNSRecon for DNS details, Fierce for quick scans)
- **Packet capture**: tcpdump (not integrated) vs PyShark wrapper
  - **Decision**: Use PyShark as primary, require tcpdump binary

---

## Dependency Matrix

| Tool | Requires | Language | Binary Deps | Licensing |
|------|----------|----------|-------------|-----------|
| Scapy | Python 3.7+ | Python | libpcap | GPL-2.0 |
| PyShark | Python 3.6+, tshark | Python | wireshark/tshark | MIT |
| Zeek | C++ compiler, Zeek 5.0+ | Python+C++ | zeek binary | BSD-3 |
| testssl.sh | Bash, openssl | Bash | openssl, timeout | GPLv2 |
| OWASP ZAP | Java 11+, ZAP daemon | Java | zaproxy binary | Apache-2.0 |
| DNSRecon | Python 3.6+ | Python | (none) | GPL-2.0 |
| Masscan | C compiler | C | masscan binary | AGPL-3.0 |
| NetBox | Python 3.8+, API | Python | netbox server | Apache-2.0 |
| osquery | C++, osquery daemon | Python+C++ | osquery binary | Apache-2.0 |
| Suricata | C, suricata daemon | Python+C | suricata binary | GPL-2.0 |
| Fierce | Python 3.6+ | Python | (none) | GPLv2 |
| Zabbix | Python 3.6+, API | Python | zabbix server | GPLv2 |
| ntopng | C, ntop daemon | Python+C | ntopng binary | GPLv3 |
| Hashcat | C, CUDA/HIP (optional) | C | hashcat binary | MIT |
| Aircrack-ng | C, wireless drivers | C | aircrack-ng binaries | GPLv2 |

---

## Loom Integration Strategy

### For Binary-Based Tools (subprocess mode)
1. **Graceful degradation**: Wrap in try/except; return `{"error": "tool_not_installed"}`
2. **Binary path detection**: Use `shutil.which()` to verify availability at startup
3. **Input validation**: Strict regex/whitelist for domain/IP/port arguments
4. **Timeout handling**: 60-300s limits per tool, kill zombie processes
5. **Output parsing**: JSON where possible, regex fallback for text

### For Library-Based Tools (direct imports)
1. **Optional imports**: Guard with try/except in server.py
2. **Graceful skip**: If ImportError, log WARNING and skip tool registration
3. **Vendor dependencies**: Pin versions in `pyproject.toml` (all extras)

### For API-Based Tools (REST client)
1. **Config-driven**: URL/token from environment variables or LOOM_CONFIG
2. **Connection validation**: Implement `research_tool_health_check` variant
3. **Error handling**: Return structured errors for 403/404/5xx
4. **Rate limiting**: Respect tool's own rate limits

---

## Security Considerations

### Input Validation (CRITICAL)
- **Domains/IPs**: Whitelist alphanumeric + dots/hyphens/colons (existing validators.py pattern)
- **Ports**: 1-65535 integer range
- **File paths**: No path traversal (restrict to temp dir, no `/` or `..`)
- **DNS zones**: No shell metacharacters

### Command Injection Prevention
- **subprocess**: Always use `shell=False`, pass args as list
- **Domain validation**: Reject domains starting with `-` to prevent flag injection
- **Port validation**: Integer parsing before use

### Output Sanitization
- **Remove API keys**: Grep output for patterns like `token=`, `key=`, redact before returning
- **Truncate large outputs**: PCAP files, mass scan results (>10MB) → summarize
- **Error messages**: Never expose full stack traces to users

### Privilege Escalation
- **Wireless tools** (aircrack-ng, airmon-ng): Require root/sudo
  - **Strategy**: Check capabilities, return error if unavailable; document in tool_params
- **Packet capture** (tcpdump, pyshark): May require root for live capture
  - **Strategy**: Fall back to offline PCAP analysis if live capture denied

---

## Estimated Implementation Hours

| Phase | Repos | Tools | Dev | Test | Docs | Total |
|-------|-------|-------|-----|------|------|-------|
| P1: Packet Analysis | 3 | 6 | 24h | 12h | 6h | **42h** |
| P1: TLS + Web | 2 | 4 | 16h | 8h | 4h | **28h** |
| P2: Recon + Infrastructure | 5 | 8 | 20h | 10h | 5h | **35h** |
| P2: Security Monitoring | 4 | 6 | 18h | 9h | 4h | **31h** |
| P3: Cryptanalysis | 2 | 4 | 12h | 6h | 3h | **21h** |
| **TOTAL** | **16** | **28** | **90h** | **45h** | **22h** | **157h** |

---

## Testing Strategy

### Unit Tests
- Tool parameter validation (100+ test cases per tool)
- Output parsing & schema validation
- Error handling (missing binary, timeout, invalid input)

### Integration Tests
- Real subprocess execution (with timeouts)
- PCAP file analysis (fixtures in tests/fixtures/)
- API client connections (mocked responses)

### E2E Tests (Journey)
- Complete packet analysis workflows
- DNS enumeration → certificate validation → web scan
- Host monitoring → network forensics correlation

---

## Documentation Requirements

### Per-Tool Docs
1. **Reference entry** in `docs/tools-reference.md`
   - Parameters, return schema, examples
   - Cost estimation (credits)
2. **Help section** in `docs/help.md`
   - Troubleshooting (binary not found, permission denied)
   - Common use cases & workflows
   - Related tools & cross-references

### Guides
1. **Network Forensics Guide** (`docs/network-forensics.md`)
   - Workflow: capture → decode → analyze → correlate
   - Tool selection matrix
2. **TLS/Cryptographic Analysis Guide** (`docs/crypto-analysis.md`)
   - Certificate validation workflow
   - Hash identification & cracking strategies

---

## Deployment Checklist

- [ ] All 15 repos cloned & tested locally
- [ ] Binary dependencies documented in setup.md
- [ ] Parameter models added to params.py
- [ ] Tool registration in server.py
- [ ] Full test suite passes (>80% coverage)
- [ ] Documentation complete & cross-linked
- [ ] Code review approval
- [ ] Deployed to production with gradual rollout
- [ ] Monitoring alerts configured for tool failures

---

## Conclusion

This research identifies **15 high-value network/infrastructure tools** covering critical gaps in Loom's reconnaissance and security monitoring capabilities. The P1 phase (6 tools, Packet Analysis + TLS) can be completed in ~70h and provides immediate value for network forensics workflows. P2-P3 phases provide operational monitoring (osquery, Zabbix) and advanced cryptanalysis capabilities.

**Recommended next steps:**
1. Prioritize P1 tools (Scapy, PyShark, testssl.sh, OWASP ZAP) — estimated 70h
2. Run dependency validation on target systems
3. Create prototype implementations for 3-5 repos
4. Integrate feedback and refine effort estimates
5. Plan Phase 2 (Recon + Monitoring) for subsequent sprint

---

## References

- Scapy: https://scapy.net/
- PyShark: https://kimisgamedevelopment.wordpress.com/pyshark/
- Zeek: https://zeek.org/
- testssl.sh: https://github.com/drwetter/testssl.sh
- OWASP ZAP: https://www.zaproxy.org/
- DNSRecon: https://github.com/darkoperator/dnsrecon
- Masscan: https://github.com/robertdavidgraham/masscan
- NetBox: https://netbox.dev/
- osquery: https://osquery.io/
- Suricata: https://suricata.io/
- Fierce: https://github.com/mschwager/fierce
- Zabbix: https://www.zabbix.com/
- ntopng: https://www.ntop.org/
- Hashcat: https://hashcat.net/hashcat/
- Aircrack-ng: https://www.aircrack-ng.org/
