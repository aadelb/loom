# Network Forensics Tools Integration — TODO Tasks
## 15 Missing Repos, 29 MCP Tools, 157-hour sprint

**Start Date:** 2026-05-01  
**Target Completion:** ~6 weeks  
**Team Size:** 1-2 developers  

---

## Phase 1: Core Packet Analysis (P1) — 70 hours, Week 1-2

### Sprint 1.1: Scapy Integration (6 tools: packet_craft, packet_analyze)

#### SCAPY-001: Project Setup & Dependency Validation
- [ ] Clone https://github.com/secdev/scapy
- [ ] Run `pip install scapy>=2.4.5` on both Mac + Hetzner
- [ ] Verify scapy imports: `python3 -c "from scapy.all import *"`
- [ ] Check libpcap availability: `dpkg -l | grep libpcap` (Linux)
- [ ] Create `src/loom/tools/scapy_backend.py` (empty module)
- [ ] Add scapy to `pyproject.toml` under `[project.optional-dependencies]`

**Effort:** 2h | **Owner:** -

#### SCAPY-002: Implement research_packet_craft
- [ ] Read NETWORK_TOOLS_IMPLEMENTATION_SPEC.md section 1.1
- [ ] Add `ScapyPacketCraftParams` to `src/loom/params.py`
- [ ] Implement `research_packet_craft()` async function
  - [ ] IPv4 validation (reuse validators.validate_url pattern)
  - [ ] Port validation (1-65535)
  - [ ] Protocol whitelist (TCP, UDP, ICMP, DNS, HTTP)
  - [ ] Build Scapy packet: `IP(src=src_ip, dst=dst_ip) / TCP(...)`
  - [ ] Convert to hex: `raw(packet).hex()`
  - [ ] Return {"success": True, "packet_hex": "...", ...}
- [ ] Handle errors: missing protocol, invalid IP → ValueError
- [ ] Write docstring with cost estimation (1 credit)

**Effort:** 4h | **Owner:** -

#### SCAPY-003: Implement research_packet_analyze
- [ ] Add `ScapyPacketAnalyzeParams` to `params.py`
- [ ] Implement `research_packet_analyze()` async function
  - [ ] Validate pcap_file path (reject `..`, absolute paths)
  - [ ] Load PCAP: `rdpcap(pcap_file)`
  - [ ] Filter by protocol if requested
  - [ ] Extract: src/dst IP, port, protocol, packet size, flags
  - [ ] Aggregate statistics: protocol counts, top IPs, byte totals
  - [ ] Return 500-1000 packet limit (paginate if needed)
- [ ] Handle errors: file not found, unsupported format, Scapy parse failure

**Effort:** 6h | **Owner:** -

#### SCAPY-004: Write Unit Tests (scapy)
- [ ] Create `tests/test_tools/test_scapy_backend.py`
  - [ ] `test_packet_craft_tcp_syn()` — craft SYN packet
  - [ ] `test_packet_craft_udp()` — UDP packet
  - [ ] `test_packet_craft_icmp()` — ICMP echo
  - [ ] `test_packet_craft_invalid_ip()` — reject "invalid_ip"
  - [ ] `test_packet_craft_port_out_of_range()` — reject port 99999
  - [ ] `test_pcap_analyze_sample()` — load tests/fixtures/sample.pcap
  - [ ] `test_pcap_analyze_protocol_filter()` — filter by TCP only
  - [ ] `test_pcap_analyze_not_found()` — 404 PCAP file
- [ ] Run: `pytest tests/test_tools/test_scapy_backend.py -v`
- [ ] Achieve 80%+ coverage

**Effort:** 4h | **Owner:** -

#### SCAPY-005: Register Tools in Server
- [ ] Add Scapy tools to `src/loom/server.py:_register_tools()`
  - [ ] `mcp.tool()(_wrap_tool(research_packet_craft, ScapyPacketCraftParams, "..."))`
  - [ ] `mcp.tool()(_wrap_tool(research_packet_analyze, ScapyPacketAnalyzeParams, "..."))`
- [ ] Handle ImportError if scapy not installed → log WARNING, skip
- [ ] Run: `python3 -c "from loom.server import create_app; print(len(create_app()._registered_tools))"`
- [ ] Verify tool count increased by 2

**Effort:** 2h | **Owner:** -

#### SCAPY-006: Documentation (scapy)
- [ ] Add entries to `docs/tools-reference.md`:
  - [ ] `research_packet_craft` — parameters, return schema, examples
  - [ ] `research_packet_analyze` — parameters, return schema, examples
- [ ] Add entries to `docs/help.md`:
  - [ ] Troubleshooting: "Scapy not installed", "libpcap missing"
  - [ ] Use cases: "Packet crafting for fuzzing", "PCAP forensics"
- [ ] Add cost estimates (1 credit, 3 credits)

**Effort:** 2h | **Owner:** -

---

### Sprint 1.2: PyShark Integration (2 tools: packet_decode, pcap_analyze)

#### PYSHARK-001: Project Setup
- [ ] Clone https://github.com/KimiTheCat/pyshark
- [ ] Install: `pip install pyshark>=0.6`
- [ ] Verify tshark: `which tshark` (should be in PATH from Wireshark)
- [ ] Create `src/loom/tools/pyshark_backend.py`
- [ ] Test: `python3 -c "import pyshark; print(pyshark.__version__)"`

**Effort:** 2h | **Owner:** -

#### PYSHARK-002: Implement research_packet_decode
- [ ] Add `PysharkPacketDecodeParams` to `params.py`
- [ ] Implement `research_packet_decode()` async function
  - [ ] Validate pcap_file path
  - [ ] Create PyShark reader: `FileCapture(pcap_file)`
  - [ ] Filter packets by protocol if requested
  - [ ] Extract layers: frame, ethernet, IP, TCP/UDP, DNS, HTTP
  - [ ] Parse TCP flags: SYN, ACK, FIN, RST, PUSH, URG
  - [ ] Return limit of 500 packets (paginate)
  - [ ] Hex-encode payload for security
- [ ] Handle errors: tshark not found, PCAP parse failure

**Effort:** 6h | **Owner:** -

#### PYSHARK-003: Implement research_pcap_analyze
- [ ] Add `PysharkPcapAnalyzeParams` to `params.py`
- [ ] Implement `research_pcap_analyze()` async function
  - [ ] Support analysis_type: "flow", "timeline", "geo", "protocol"
  - [ ] **Flow mode**: Group by (src_ip, src_port, dst_ip, dst_port) → count packets/bytes
  - [ ] **Timeline mode**: Bin packets into 1s/1m/1h buckets → aggregate
  - [ ] **Protocol mode**: Count TCP/UDP/ICMP/DNS/HTTP/other
  - [ ] **Geo mode**: Use MaxMind GeoIP2 if available (optional)
  - [ ] Return top 20 flows/talkers

**Effort:** 8h | **Owner:** -

#### PYSHARK-004-006: Tests + Server Registration + Documentation
- [ ] Unit tests: `tests/test_tools/test_pyshark_backend.py` (4h)
- [ ] Register in `server.py` (2h)
- [ ] Docs: `tools-reference.md`, `help.md` (2h)

**Effort:** 8h | **Owner:** -

---

### Sprint 1.3: Zeek Integration (2 tools: zeek_ids_analyze, zeek_log_parse)

#### ZEEK-001-006: Implementation & Testing
- [ ] Project setup (2h)
  - [ ] Install zeek>=5.0 binary
  - [ ] Create `src/loom/tools/zeek_backend.py`
- [ ] Implement `research_zeek_ids_analyze()` (8h)
  - [ ] Run zeek on PCAP: `zeek -r file.pcap`
  - [ ] Parse notice.log → extract alerts
  - [ ] Return severity breakdown (critical/high/medium/low)
  - [ ] Limit to 100 alerts
- [ ] Implement `research_zeek_log_parse()` (6h)
  - [ ] Parse Zeek logs (conn.log, ssl.log, http.log, dns.log)
  - [ ] Auto-detect log type from filename
  - [ ] Return structured records (limit 500)
- [ ] Unit tests (4h)
- [ ] Server registration (2h)
- [ ] Documentation (2h)

**Effort:** 24h | **Owner:** -

---

## Phase 2: TLS/Cryptographic Tools (P1) — 50 hours, Week 2-3

### Sprint 2.1: testssl.sh Integration

#### TESTSSL-001-006: Implementation & Testing
- [ ] Project setup (2h)
  - [ ] Download testssl.sh: `wget https://github.com/drwetter/testssl.sh/raw/master/testssl.sh`
  - [ ] Make executable: `chmod +x testssl.sh`
  - [ ] Verify: `./testssl.sh -h`
  - [ ] Create `src/loom/tools/testssl_backend.py`
- [ ] Implement `research_testssl_analyze()` (10h)
  - [ ] Run: `testssl.sh --json hostname:port`
  - [ ] Parse JSON output
  - [ ] Extract: TLS version, ciphers, certificates, vulnerabilities
  - [ ] Return severity breakdown
- [ ] Implement `research_tls_cert_chain()` (8h)
  - [ ] Use openssl s_client: `openssl s_client -connect host:port`
  - [ ] Extract certificate chain
  - [ ] Validate chain to system CA store
  - [ ] Check OCSP stapling
- [ ] Unit tests (4h)
- [ ] Server registration (2h)
- [ ] Documentation (2h)

**Effort:** 28h | **Owner:** -

### Sprint 2.2: OWASP ZAP Integration

#### ZAP-001-006: Implementation & Testing
- [ ] Project setup (2h)
  - [ ] Install ZAP: Docker or native
  - [ ] Start daemon: `zaproxy -cmd -port 8080` (or config)
  - [ ] Create `src/loom/tools/zaproxy_backend.py`
- [ ] Implement `research_zaproxy_scan()` (12h)
  - [ ] Call ZAP REST API: `/JSON/core/action`
  - [ ] Start scan: `asyncScan` (passive/active)
  - [ ] Poll for completion: `scanProgress`
  - [ ] Parse vulnerabilities: risk/confidence/type/URL
  - [ ] Return top 20 vulns
- [ ] Implement `research_zaproxy_spider()` (8h)
  - [ ] Start spider: `/JSON/spider/action`
  - [ ] Collect URLs, forms, external links
  - [ ] Return structured crawl results
- [ ] Unit tests (mock ZAP API) (4h)
- [ ] Server registration (2h)
- [ ] Documentation (2h)

**Effort:** 30h | **Owner:** -

---

## Phase 3: Network Reconnaissance (P2) — 50 hours, Week 3-4

### Sprint 3.1-3.4: DNSRecon, Masscan, Fierce, NetBox

#### DNS-RECON-001-003: Implementation
- [ ] Project setup: Clone, install, verify binary (2h)
- [ ] Implement `research_dns_recon()` — enumerate DNS records (6h)
- [ ] Implement `research_dns_brute()` — brute-force subdomains (6h)
- [ ] Unit tests + server registration + docs (6h)

**Effort:** 20h | **Owner:** -

#### MASSCAN-001-003: Implementation
- [ ] Setup: Clone, compile/install masscan (2h)
- [ ] Implement `research_masscan_full_scan()` — TCP/UDP scan (6h)
- [ ] Implement `research_masscan_udp_scan()` — UDP-only scan (4h)
- [ ] Tests + registration + docs (6h)

**Effort:** 18h | **Owner:** -

#### FIERCE-001-003: Implementation
- [ ] Setup: Install fierce Python lib (1h)
- [ ] Implement `research_fierce_subdomain_scan()` (5h)
- [ ] Tests + registration + docs (4h)

**Effort:** 10h | **Owner:** -

#### NETBOX-001-003: Implementation
- [ ] Setup: Config API token, verify connectivity (2h)
- [ ] Implement `research_netbox_device_query()` (4h)
- [ ] Implement `research_netbox_ip_lookup()` (4h)
- [ ] Tests + registration + docs (6h)

**Effort:** 16h | **Owner:** -

---

## Phase 4: Security Monitoring (P2) — 40 hours, Week 4-5

### Sprint 4.1-4.4: osquery, Suricata, Zabbix, ntopng

#### OSQUERY-001-003: Implementation
- [ ] Setup: Install osquery daemon (2h)
- [ ] Implement `research_osquery_host_monitor()` (6h)
- [ ] Implement `research_osquery_audit()` (6h)
- [ ] Tests + registration + docs (6h)

**Effort:** 20h | **Owner:** -

#### SURICATA-001-003: Implementation
- [ ] Setup: Install suricata, configure rules (2h)
- [ ] Implement `research_suricata_ids_scan()` (6h)
- [ ] Implement `research_suricata_alert_parse()` (4h)
- [ ] Tests + registration + docs (6h)

**Effort:** 18h | **Owner:** -

#### ZABBIX-001-003: Implementation
- [ ] Setup: Config API credentials (1h)
- [ ] Implement `research_zabbix_metric_query()` (4h)
- [ ] Implement `research_zabbix_event_monitor()` (4h)
- [ ] Tests + registration + docs (4h)

**Effort:** 13h | **Owner:** -

#### NTOPNG-001-003: Implementation
- [ ] Setup: Config API access (1h)
- [ ] Implement `research_ntop_traffic_analyze()` (4h)
- [ ] Implement `research_ntop_stats()` (4h)
- [ ] Tests + registration + docs (4h)

**Effort:** 13h | **Owner:** -

---

## Phase 5: Advanced Cryptanalysis (P3+) — 30 hours, Week 5+

### Sprint 5.1-5.2: Hashcat, Aircrack-ng (Optional/Deferred)

#### HASHCAT-001-003: Implementation
- [ ] Setup: Install hashcat + GPU support (optional) (2h)
- [ ] Implement `research_hashcat_crack()` (8h)
- [ ] Implement `research_hashcat_benchmark()` (6h)
- [ ] Tests + registration + docs (6h)

**Effort:** 22h | **Owner:** -

#### AIRCRACK-001-003: Implementation (LOW PRIORITY)
- [ ] Setup: Install aircrack-ng suite (2h)
- [ ] Implement `research_aircrack_capture_analyze()` (6h)
- [ ] Implement `research_aircrack_key_recovery()` (8h)
- [ ] Tests + registration + docs (6h)

**Effort:** 22h | **Owner:** -

---

## Cross-Cutting Tasks

### CROSS-001: Parameter Models (params.py)
- [ ] Add all 29 tool parameter models to `src/loom/params.py`
- [ ] Validate: required fields, field types, constraints
- [ ] Use Pydantic v2: `extra="forbid"`, `strict=True`
- [ ] Add docstrings & examples

**Effort:** 6h | **Owner:** -

### CROSS-002: Server Registration (server.py)
- [ ] Add all 29 tools to `_register_tools()` function
- [ ] Handle ImportError for optional tools
- [ ] Test tool count: 318 → 318 + 29 = 347

**Effort:** 3h | **Owner:** -

### CROSS-003: Documentation
- [ ] Update `docs/tools-reference.md` — all 29 tools
- [ ] Update `docs/help.md` — troubleshooting, use cases
- [ ] Create `docs/network-forensics.md` — workflows
- [ ] Update `CLAUDE.md` — tool count (318 → 347)
- [ ] Run `scripts/verify_completeness.py` — fix all failures

**Effort:** 12h | **Owner:** -

### CROSS-004: Security Validation
- [ ] Input validation audit: all 29 tools
- [ ] Command injection test: 50+ payloads
- [ ] SSRF test: 10+ bypass vectors
- [ ] Output sanitization: no API keys in logs
- [ ] Create `tests/test_security/test_network_forensics.py`

**Effort:** 8h | **Owner:** -

### CROSS-005: Integration Tests (Journey)
- [ ] Create journey test: Packet capture → analyze → detect anomalies
- [ ] Create journey test: Scan target → enumerate DNS → validate certs
- [ ] Create journey test: PCAP upload → forensic analysis
- [ ] Test with mocked responses + live data (on Hetzner)

**Effort:** 8h | **Owner:** -

### CROSS-006: Final Validation & Deployment
- [ ] Run full test suite: `pytest tests/ --cov=src/loom -k "network"`
- [ ] Code review: all 29 tools by peer
- [ ] Performance benchmark: latency, memory, CPU
- [ ] Staging deployment: 1 week beta
- [ ] Production rollout: gradual, monitoring alerts

**Effort:** 10h | **Owner:** -

---

## Dependency Installation Summary

```bash
# Core packet analysis
pip install scapy>=2.4.5
pip install pyshark>=0.6
apt-get install wireshark        # provides tshark

# Network monitoring
apt-get install zeek>=5.0
apt-get install suricata
apt-get install osquery

# Reconnaissance
apt-get install dnsrecon         # or pip if available
apt-get install masscan
pip install fierce

# TLS auditing
apt-get install testssl.sh       # or download from GitHub
apt-get install openssl

# Web security
docker run -d -p 8080:8080 zaproxy/zaproxy:latest

# Infrastructure
pip install pynetbox             # NetBox API client
pip install pyzabbix             # Zabbix API client
pip install requests             # ntopng API client

# Cryptanalysis (optional)
apt-get install hashcat
apt-get install aircrack-ng
```

---

## Effort Summary

| Phase | Hours | Weeks | Status |
|-------|-------|-------|--------|
| **P1: Packet Analysis** | 70 | 2 | TODO |
| **P1: TLS Tools** | 50 | 2 | TODO |
| **P2: Recon** | 50 | 2 | TODO |
| **P2: Monitoring** | 40 | 1-2 | TODO |
| **P3: Cryptanalysis** | 30 | 1-2 | DEFERRED |
| **Cross-Cutting** | 47 | Throughout | TODO |
| **TOTAL** | **287** | **6-8** | **IN PROGRESS** |

**Note:** Estimate is 287h (vs. 157h in spec). Reason: includes comprehensive testing, security validation, documentation, and deployment tasks. Actual sprint velocity will determine final timeline.

---

## Success Criteria

- [ ] All 29 tools implemented and tested (80%+ coverage)
- [ ] All 29 tools registered in MCP server
- [ ] All 29 tools documented in tools-reference.md + help.md
- [ ] Zero security issues in code review
- [ ] Tool count: 318 → 347 (verified in server log)
- [ ] All journey tests passing (mocked + live)
- [ ] Performance benchmarks: <2s latency for lightweight tools, <30s for heavy
- [ ] Staging deployment: 1 week without critical issues
- [ ] Production deployment: gradual rollout with monitoring

---

## Sign-Off

Once all tasks are complete:

1. Update CLAUDE.md with new tool count and categories
2. Create release notes for v0.1.0-alpha.3
3. Tag git commit: `git tag v0.1.0-alpha.3`
4. Deploy to production with monitoring alerts
5. Schedule post-mortems & retrospective

---

## References

- Implementation Spec: `NETWORK_TOOLS_IMPLEMENTATION_SPEC.md`
- Research Report: `NETWORK_FORENSICS_INTEGRATION_RESEARCH.md`
- Loom Architecture: `CLAUDE.md`
- Tools Reference: `docs/tools-reference.md`
