# Network Forensics Tools — Implementation Specification
## For Loom Backend Integration (15 repos, 29 MCP tools)

---

## 1. SCAPY — Packet Crafting & Analysis

**Module:** `src/loom/tools/scapy_backend.py`  
**GitHub:** https://github.com/secdev/scapy  
**Installation:** `pip install scapy>=2.4.5`

### Tool 1.1: `research_packet_craft`

```python
async def research_packet_craft(
    protocol: str,  # "TCP", "UDP", "ICMP", "DNS", "HTTP"
    src_ip: str,    # source IPv4 address
    dst_ip: str,    # destination IPv4 address
    src_port: int | None = None,  # for TCP/UDP (1-65535)
    dst_port: int | None = None,  # for TCP/UDP (1-65535)
    flags: str | None = None,  # "SYN", "ACK", "FIN", "RST" (comma-separated)
    payload: str | None = None,  # hex-encoded or text
    ttl: int = 64,
    timeout: int = 10,
) -> dict[str, Any]:
    """
    Craft and send a custom network packet using Scapy.
    
    Args:
        protocol: Layer 4 protocol (TCP, UDP, ICMP, DNS, HTTP)
        src_ip: Source IPv4 address (validated)
        dst_ip: Destination IPv4 address (validated)
        src_port: Source port (1-65535, required for TCP/UDP)
        dst_port: Destination port (1-65535, required for TCP/UDP)
        flags: TCP flags (SYN, ACK, FIN, RST, PUSH, URG, etc.)
        payload: Optional payload (hex or ASCII)
        ttl: IP TTL (1-255, default 64)
        timeout: Packet send timeout (seconds)
    
    Returns:
        {
            "success": bool,
            "packet_hex": str,        # hex-encoded packet
            "packet_size": int,       # bytes
            "protocol": str,
            "src_ip": str,
            "dst_ip": str,
            "sent_at": str,           # ISO timestamp
            "error": str | None
        }
    
    Raises:
        ValueError: Invalid IP/port/protocol
        AppException: Scapy not available or send failed
    
    Cost: 1 credit (light operation)
    """
```

**Implementation Notes:**
- Validate IPv4 addresses (no CIDR, no hostnames)
- Validate ports (1-65535 for TCP/UDP)
- Protocol whitelist: only TCP/UDP/ICMP/DNS/HTTP
- Require root/CAP_NET_RAW for raw socket send (check at registration)
- Return hex representation for security (no binary in JSON)
- Timeout must be <30s

---

### Tool 1.2: `research_packet_analyze`

```python
async def research_packet_analyze(
    pcap_file: str,     # path to .pcap/.pcapng file (validated for path traversal)
    packet_limit: int = 1000,  # max packets to analyze
    protocol_filter: str | None = None,  # "TCP", "UDP", "ICMP", "DNS", "HTTP"
    summary_only: bool = False,  # if true, return stats only (not per-packet)
) -> dict[str, Any]:
    """
    Parse and analyze a PCAP file using Scapy.
    
    Args:
        pcap_file: Path to PCAP file (must be in /tmp or validated directory)
        packet_limit: Max packets to parse (default 1000)
        protocol_filter: Optional protocol filter
        summary_only: If true, return aggregate stats (no per-packet data)
    
    Returns:
        {
            "success": bool,
            "total_packets": int,
            "file_size": int,           # bytes
            "timestamp_range": {
                "first": str,           # ISO timestamp
                "last": str
            },
            "protocols": {
                "tcp": int,
                "udp": int,
                "icmp": int,
                "dns": int,
                "http": int,
                "other": int
            },
            "top_ips": [
                {"ip": str, "packet_count": int, "direction": "src|dst"}
            ],
            "packets": [                # if summary_only=False
                {
                    "index": int,
                    "timestamp": str,
                    "src_ip": str,
                    "dst_ip": str,
                    "protocol": str,
                    "size": int,
                    "flags": [str] | None,
                    "payload_hex": str | None
                }
            ],
            "error": str | None
        }
    
    Raises:
        ValueError: File path traversal, unsupported format
        AppException: Scapy parse error
    
    Cost: 3 credits (medium operation, depends on file size)
    """
```

**Implementation Notes:**
- Validate pcap_file path (reject `..`, absolute paths outside temp)
- Support .pcap and .pcapng formats
- Truncate per-packet list if >packet_limit
- Payload shown as hex for security (binary-safe)
- Parse layer 2/3/4 headers automatically
- Handle fragmented packets gracefully

---

## 2. PYSHARK — PCAP Decoding & Wireshark Integration

**Module:** `src/loom/tools/pyshark_backend.py`  
**GitHub:** https://github.com/KimiTheCat/pyshark  
**Installation:** `pip install pyshark>=0.6` (requires tshark binary)

### Tool 2.1: `research_packet_decode`

```python
async def research_packet_decode(
    pcap_file: str,
    packet_index: int | None = None,  # if set, decode single packet
    output_format: str = "json",  # "json", "text", "csv"
    deep_inspection: bool = False,  # parse all dissector layers
) -> dict[str, Any]:
    """
    Decode packets from PCAP using tshark (Wireshark CLI).
    
    Args:
        pcap_file: Path to PCAP file
        packet_index: Optional single packet index (0-based)
        output_format: Output format (json, text, csv)
        deep_inspection: If true, parse all protocol layers
    
    Returns:
        {
            "success": bool,
            "packets_decoded": int,
            "packets": [
                {
                    "index": int,
                    "timestamp": str,
                    "frame": {
                        "size": int,
                        "protocols": [str]  # ["eth", "ip", "tcp", "http"]
                    },
                    "ethernet": {
                        "src": str,
                        "dst": str
                    },
                    "ip": {
                        "version": int,
                        "src": str,
                        "dst": str,
                        "ttl": int,
                        "protocol": str
                    },
                    "tcp": {
                        "src_port": int,
                        "dst_port": int,
                        "flags": [str],
                        "seq": int,
                        "ack": int
                    } | None,
                    "udp": {
                        "src_port": int,
                        "dst_port": int,
                        "length": int
                    } | None,
                    "dns": {
                        "queries": [str],
                        "answers": [str],
                        "response_code": str
                    } | None,
                    "http": {
                        "method": str,
                        "request_uri": str,
                        "status_code": int
                    } | None,
                    "payload_hex": str | None
                }
            ],
            "error": str | None
        }
    
    Raises:
        ValueError: Invalid file path, tshark not found
        AppException: tshark parse failure
    
    Cost: 3 credits
    """
```

**Implementation Notes:**
- Requires tshark binary (check with `shutil.which("tshark")`)
- Use `-T json` flag for structured output
- Limit to 1000 packets by default (add parameter if needed)
- Parse nested protocol headers using Wireshark's dissector output
- HTTP body redaction (security)

---

### Tool 2.2: `research_pcap_analyze`

```python
async def research_pcap_analyze(
    pcap_file: str,
    analysis_type: str = "flow",  # "flow", "timeline", "geo", "protocol"
) -> dict[str, Any]:
    """
    Statistical analysis of PCAP file (flow-based, temporal, geographic).
    
    Args:
        pcap_file: Path to PCAP file
        analysis_type: Type of analysis
            - "flow": TCP/UDP flow statistics (src/dst IP/port pairs)
            - "timeline": Temporal distribution of packets
            - "geo": Geographic IP distribution (requires MaxMind GeoIP2)
            - "protocol": Protocol distribution & anomalies
    
    Returns:
        {
            "success": bool,
            "analysis_type": str,
            "total_packets": int,
            "total_bytes": int,
            "flows": [                       # if analysis_type="flow"
                {
                    "src_ip": str,
                    "src_port": int,
                    "dst_ip": str,
                    "dst_port": int,
                    "protocol": str,
                    "packet_count": int,
                    "byte_count": int,
                    "duration": float,
                    "packets_per_sec": float
                }
            ],
            "timeline": {                    # if analysis_type="timeline"
                "buckets": [
                    {
                        "time_bucket": str,  # ISO timestamp (1s, 1m, 1h)
                        "packet_count": int,
                        "byte_count": int
                    }
                ]
            },
            "protocols": {                   # if analysis_type="protocol"
                "tcp": int,
                "udp": int,
                "icmp": int,
                "dns": int,
                "tls": int,
                "http": int,
                "other": int
            },
            "top_talkers": [
                {"ip": str, "packet_count": int, "byte_count": int}
            ],
            "error": str | None
        }
    
    Cost: 5 credits (heavy operation)
    """
```

---

## 3. ZEEK — Network Intrusion Detection & Monitoring

**Module:** `src/loom/tools/zeek_backend.py`  
**GitHub:** https://github.com/zeek/zeek  
**Installation:** `pip install zeek>=5.0` (requires zeek binary)

### Tool 3.1: `research_zeek_ids_analyze`

```python
async def research_zeek_ids_analyze(
    pcap_file: str,
    zeek_rules: str | None = None,  # custom rules (disabled for safety)
    detect_anomalies: bool = True,
) -> dict[str, Any]:
    """
    Run Zeek IDS on PCAP file for network intrusion detection.
    
    Args:
        pcap_file: Path to PCAP file
        zeek_rules: Reserved (not allowed — use default rules only)
        detect_anomalies: Enable anomaly detection
    
    Returns:
        {
            "success": bool,
            "alerts": [
                {
                    "timestamp": str,
                    "src_ip": str,
                    "dst_ip": str,
                    "src_port": int,
                    "dst_port": int,
                    "signature": str,
                    "category": str,
                    "severity": str,  # "low", "medium", "high", "critical"
                    "description": str
                }
            ],
            "anomalies": [                # if detect_anomalies=True
                {
                    "type": str,          # "port_scan", "brute_force", "dos", etc.
                    "src_ip": str,
                    "description": str,
                    "confidence": float
                }
            ],
            "summary": {
                "total_alerts": int,
                "critical_count": int,
                "high_count": int,
                "medium_count": int,
                "low_count": int
            },
            "error": str | None
        }
    
    Cost: 5 credits
    """
```

**Implementation Notes:**
- Reject custom zeek_rules parameter (security, prevent injection)
- Use Zeek's default Suricata rule set for consistency
- Parse notice.log and signatures.log
- Timeout: 120s max
- Return alert summary + top alerts (limit to 100)

---

### Tool 3.2: `research_zeek_log_parse`

```python
async def research_zeek_log_parse(
    zeek_log_file: str,  # path to conn.log, ssl.log, http.log, or dns.log
    log_type: str = "auto",  # "conn", "ssl", "http", "dns", or "auto"
    filters: dict[str, Any] | None = None,  # optional filters
) -> dict[str, Any]:
    """
    Parse Zeek logs (conn.log, ssl.log, http.log, dns.log).
    
    Args:
        zeek_log_file: Path to Zeek log file
        log_type: Log type ("conn", "ssl", "http", "dns", or auto-detect)
        filters: Optional filters (e.g., {"dst_port": 443, "service": "ssl"})
    
    Returns:
        {
            "success": bool,
            "log_type": str,
            "total_records": int,
            "records": [
                {
                    # For conn.log:
                    "ts": str,
                    "uid": str,
                    "src_ip": str,
                    "src_port": int,
                    "dst_ip": str,
                    "dst_port": int,
                    "protocol": str,
                    "service": str,
                    "duration": float,
                    "orig_bytes": int,
                    "resp_bytes": int,
                    "conn_state": str,
                    
                    # For ssl.log:
                    "version": str,
                    "cipher": str,
                    "server_name": str,
                    "issuer": str,
                    "client_issuer": str,
                    
                    # For http.log:
                    "method": str,
                    "uri": str,
                    "referrer": str,
                    "status_code": int,
                    "user_agent": str,
                    
                    # For dns.log:
                    "query": str,
                    "qclass": str,
                    "qtype": str,
                    "rcode": str,
                    "answers": [str]
                }
            ],
            "error": str | None
        }
    
    Cost: 3 credits
    """
```

**Implementation Notes:**
- Auto-detect log type from filename/headers
- Parse Zeek's tab-separated format with header
- Support filtering by field (e.g., service="ssl", dst_port=443)
- Limit output to 500 records (paginate if needed)

---

## 4. TESTSSL.SH — TLS/SSL Configuration Auditing

**Module:** `src/loom/tools/testssl_backend.py`  
**GitHub:** https://github.com/drwetter/testssl.sh  
**Installation:** `bash` script + `openssl`, `timeout` (system packages)

### Tool 4.1: `research_testssl_analyze`

```python
async def research_testssl_analyze(
    hostname: str,
    port: int = 443,
    checks: str = "all",  # "all", "certs", "protocols", "ciphers", "vulnerabilities"
    severity_filter: str | None = None,  # "critical", "high", "medium", "low"
) -> dict[str, Any]:
    """
    Audit TLS/SSL configuration using testssl.sh.
    
    Args:
        hostname: Target hostname (validated)
        port: TLS port (1-65535, default 443)
        checks: Type of checks to run
        severity_filter: Optional severity minimum
    
    Returns:
        {
            "success": bool,
            "hostname": str,
            "port": int,
            "tls_version": str,                  # "TLS 1.2", "TLS 1.3", etc.
            "certificate": {
                "subject": str,
                "issuer": str,
                "valid_from": str,
                "valid_to": str,
                "days_remaining": int,
                "cn": str,
                "san": [str],
                "key_bits": int,
                "signature_algorithm": str,
                "is_valid": bool,
                "validation_errors": [str]
            },
            "protocols": {
                "ssl2": bool,
                "ssl3": bool,
                "tls10": bool,
                "tls11": bool,
                "tls12": bool,
                "tls13": bool
            },
            "ciphers": [
                {
                    "name": str,
                    "bits": int,
                    "protocol": str,
                    "strength": str,             # "weak", "fair", "good", "excellent"
                    "vulnerabilities": [str]
                }
            ],
            "vulnerabilities": [
                {
                    "name": str,                # "HEARTBLEED", "POODLE", "CVE-XXXX", etc.
                    "severity": str,            # "critical", "high", "medium", "low"
                    "status": str,              # "vulnerable", "not vulnerable", "unknown"
                    "description": str
                }
            ],
            "recommendations": [str],
            "error": str | None
        }
    
    Cost: 3 credits
    """
```

**Implementation Notes:**
- Hostname validation: only FQDN + TLD, no IPs
- Port validation: 1-65535
- testssl.sh --json output parsing
- Timeout: 60s per hostname
- Skip custom checks parameter (hardcode to default set)

---

### Tool 4.2: `research_tls_cert_chain`

```python
async def research_tls_cert_chain(
    hostname: str,
    port: int = 443,
    verify_chain: bool = True,
) -> dict[str, Any]:
    """
    Analyze TLS certificate chain and trust path.
    
    Args:
        hostname: Target hostname
        port: TLS port (default 443)
        verify_chain: If true, validate chain against system CA store
    
    Returns:
        {
            "success": bool,
            "hostname": str,
            "certificates": [
                {
                    "index": int,
                    "subject": str,
                    "issuer": str,
                    "valid_from": str,
                    "valid_to": str,
                    "key_bits": int,
                    "signature_algorithm": str,
                    "subject_alt_names": [str],
                    "extended_key_usage": [str],
                    "fingerprint_sha1": str,
                    "fingerprint_sha256": str,
                    "is_self_signed": bool,
                    "is_expired": bool
                }
            ],
            "chain_validation": {                # if verify_chain=True
                "is_valid": bool,
                "root_ca": str,
                "trusted": bool,
                "errors": [str]
            },
            "ocsp_stapling": {
                "enabled": bool,
                "response_status": str
            },
            "error": str | None
        }
    
    Cost: 2 credits
    """
```

**Implementation Notes:**
- Use openssl s_client to fetch certificates
- Parse PEM format certificates
- Validate chain to system CA store (/etc/ssl/certs, etc.)
- OCSP stapling detection via openssl

---

## 5. OWASP ZAP — Web Application Security Testing

**Module:** `src/loom/tools/zaproxy_backend.py`  
**GitHub:** https://github.com/zaproxy/zaproxy  
**Installation:** Docker: `docker pull zaproxy/zaproxy` or native Java installation

### Tool 5.1: `research_zaproxy_scan`

```python
async def research_zaproxy_scan(
    target_url: str,
    scan_type: str = "passive",  # "passive", "active", "full"
    max_depth: int = 3,
    timeout: int = 300,
) -> dict[str, Any]:
    """
    Run OWASP ZAP web security scan.
    
    Args:
        target_url: Target URL (https://example.com)
        scan_type: "passive" (fast), "active" (slow), "full" (very slow)
        max_depth: Max crawl depth (1-5)
        timeout: Scan timeout (10-600 seconds)
    
    Returns:
        {
            "success": bool,
            "target_url": str,
            "scan_type": str,
            "scan_id": str,
            "start_time": str,
            "end_time": str,
            "duration": float,
            "vulnerabilities": [
                {
                    "type": str,                # "SQL Injection", "XSS", "CSRF", etc.
                    "risk": str,                # "Critical", "High", "Medium", "Low", "Info"
                    "confidence": str,          # "High", "Medium", "Low"
                    "url": str,
                    "method": str,              # "GET", "POST", etc.
                    "parameter": str,
                    "description": str,
                    "solution": str,
                    "reference_urls": [str],
                    "cwe": str,
                    "wasc": str
                }
            ],
            "summary": {
                "critical": int,
                "high": int,
                "medium": int,
                "low": int,
                "info": int
            },
            "pages_scanned": int,
            "error": str | None
        }
    
    Cost: 10 credits (heavy operation)
    """
```

**Implementation Notes:**
- Validate target_url (protocol, domain, path)
- Require ZAP daemon running on localhost:8080 (configurable)
- Use ZAP REST API at http://localhost:8080/JSON/core/action
- Reject URL lists (single URL only)
- Active scan limited to 5 min timeout
- Return top 20 vulnerabilities (paginate if needed)

---

### Tool 5.2: `research_zaproxy_spider`

```python
async def research_zaproxy_spider(
    target_url: str,
    max_depth: int = 3,
    follow_redirects: bool = True,
    timeout: int = 120,
) -> dict[str, Any]:
    """
    Spider/crawl web application using OWASP ZAP.
    
    Args:
        target_url: Target URL
        max_depth: Max recursion depth (1-5)
        follow_redirects: Follow HTTP redirects
        timeout: Crawl timeout (10-300 seconds)
    
    Returns:
        {
            "success": bool,
            "target_url": str,
            "pages_found": int,
            "urls": [
                {
                    "url": str,
                    "method": str,
                    "status_code": int,
                    "page_title": str,
                    "depth": int,
                    "time_ms": int
                }
            ],
            "forms_found": [
                {
                    "url": str,
                    "method": str,
                    "action": str,
                    "fields": [
                        {"name": str, "type": str}
                    ]
                }
            ],
            "external_links": int,
            "error": str | None
        }
    
    Cost: 5 credits
    """
```

---

## 6-15. REMAINING TOOLS (Brief Specs)

### 6. DNSRecon — DNS Infrastructure Mapping

**Module:** `src/loom/tools/dnsrecon_backend.py`

```python
# research_dns_recon(hostname, record_types="all")
# research_dns_brute(hostname, wordlist_size="small", threads=10)
```

### 7. Masscan — Fast Port Scanning

**Module:** `src/loom/tools/masscan_backend.py`

```python
# research_masscan_full_scan(target_ip, ports="1-65535", rate=1000)
# research_masscan_udp_scan(target_ip, ports="53,123,161,500", rate=1000)
```

### 8-9. Fierce — Lightweight DNS Discovery

**Module:** `src/loom/tools/fierce_backend.py`

```python
# research_fierce_subdomain_scan(domain, wordlist_size="medium")
```

### 10. NetBox — IP Address Management

**Module:** `src/loom/tools/netbox_backend.py`

```python
# research_netbox_device_query(filters: dict) → [devices]
# research_netbox_ip_lookup(ip_address) → IPAM record
```

### 11-12. osquery — Host Monitoring & Audit

**Module:** `src/loom/tools/osquery_backend.py`

```python
# research_osquery_host_monitor(query_type: str) → host state
# research_osquery_audit(audit_type: str) → audit logs
```

### 13-14. Suricata — IDS/IPS Integration

**Module:** `src/loom/tools/suricata_backend.py`

```python
# research_suricata_ids_scan(pcap_file) → alerts
# research_suricata_alert_parse(alert_file) → parsed alerts
```

### 15-16. Zabbix & ntopng — Monitoring Platforms

**Module:** `src/loom/tools/monitoring_backend.py`

```python
# research_zabbix_metric_query(hostname, metric_name, time_range)
# research_zabbix_event_monitor(severity_filter) → events
# research_ntop_traffic_analyze(interface) → traffic stats
# research_ntop_stats(filter: dict) → device stats
```

---

## Parameter Model Template (params.py)

```python
from pydantic import BaseModel, Field, field_validator

class ScapyPacketCraftParams(BaseModel):
    protocol: str = Field(..., pattern="^(TCP|UDP|ICMP|DNS|HTTP)$")
    src_ip: str = Field(..., description="Source IPv4")
    dst_ip: str = Field(..., description="Destination IPv4")
    src_port: int | None = Field(None, ge=1, le=65535)
    dst_port: int | None = Field(None, ge=1, le=65535)
    flags: str | None = None
    payload: str | None = None
    ttl: int = Field(64, ge=1, le=255)
    timeout: int = Field(10, ge=1, le=30)
    
    model_config = {"extra": "forbid", "strict": True}
    
    @field_validator("src_ip", "dst_ip")
    @classmethod
    def validate_ipv4(cls, v):
        from loom.validators import validate_url  # reuse IP validation
        return v
```

---

## Server Registration Template (server.py)

```python
# In _register_tools():

# Scapy tools
mcp.tool()(
    _wrap_tool(
        research_packet_craft,
        ScapyPacketCraftParams,
        "Craft and send custom network packets",
    )
)

mcp.tool()(
    _wrap_tool(
        research_packet_analyze,
        ScapyPacketAnalyzeParams,
        "Analyze PCAP files with Scapy",
    )
)

# ... (repeat for all 29 tools)
```

---

## Testing Template (tests/test_tools/test_network_forensics.py)

```python
import pytest
from loom.tools.scapy_backend import research_packet_craft, research_packet_analyze

@pytest.mark.asyncio
async def test_packet_craft_tcp_syn():
    """Test TCP SYN packet crafting."""
    result = await research_packet_craft(
        protocol="TCP",
        src_ip="192.168.1.100",
        dst_ip="192.168.1.1",
        src_port=12345,
        dst_port=80,
        flags="SYN"
    )
    assert result["success"] is True
    assert "packet_hex" in result
    assert result["protocol"] == "TCP"

@pytest.mark.asyncio
async def test_packet_craft_invalid_ip():
    """Test rejection of invalid IPs."""
    with pytest.raises(ValueError):
        await research_packet_craft(
            protocol="TCP",
            src_ip="invalid_ip",
            dst_ip="192.168.1.1",
            src_port=80,
            dst_port=80
        )

@pytest.mark.asyncio
@pytest.mark.slow
async def test_pcap_analysis_full():
    """Test PCAP file analysis with real file."""
    # Use fixture from tests/fixtures/sample.pcap
    result = await research_packet_analyze(
        pcap_file="tests/fixtures/sample.pcap",
        packet_limit=100
    )
    assert result["success"] is True
    assert result["total_packets"] > 0
    assert "protocols" in result
```

---

## Cost Model

| Tool | Category | Credits | Rationale |
|------|----------|---------|-----------|
| research_packet_craft | Packet ops | 1 | Lightweight, in-memory |
| research_packet_analyze | Packet ops | 3 | File I/O, parsing |
| research_packet_decode | Packet ops | 3 | tshark invocation |
| research_pcap_analyze | Packet ops | 5 | Flow analysis, memory |
| research_zeek_ids_analyze | IDS | 5 | Full Zeek scan |
| research_zeek_log_parse | Parsing | 3 | Log file parsing |
| research_testssl_analyze | TLS | 3 | Network round-trip |
| research_tls_cert_chain | TLS | 2 | Certificate parsing |
| research_zaproxy_scan | Web | 10 | Heavy active scan |
| research_zaproxy_spider | Web | 5 | Crawling |
| research_dns_recon | DNS | 3 | DNS queries |
| research_dns_brute | DNS | 5 | Wordlist-based |
| research_masscan_full_scan | Scanning | 5 | High-speed scan |
| research_masscan_udp_scan | Scanning | 5 | UDP scan |
| research_fierce_subdomain_scan | DNS | 2 | Lightweight |
| research_netbox_device_query | Infrastructure | 1 | API query |
| research_netbox_ip_lookup | Infrastructure | 1 | API query |
| research_osquery_host_monitor | Host | 2 | System query |
| research_osquery_audit | Host | 3 | Audit log parse |
| research_suricata_ids_scan | IDS | 5 | Suricata invocation |
| research_suricata_alert_parse | Parsing | 2 | JSON parsing |
| research_zabbix_metric_query | Monitoring | 2 | API query |
| research_zabbix_event_monitor | Monitoring | 3 | Event retrieval |
| research_ntop_traffic_analyze | Monitoring | 3 | API query |
| research_ntop_stats | Monitoring | 2 | Statistics query |

**Total Monthly Credit Allocation:**
- Free tier: 500 credits → ~50-100 network scans/month
- Pro tier: 10K credits → ~1000-2000 scans/month
- Team tier: 50K credits → full operational use

---

## Security Checklist

- [ ] All file paths validated (no path traversal)
- [ ] All IPs/domains validated (regex + whitelist)
- [ ] All ports validated (1-65535)
- [ ] No shell metacharacters allowed
- [ ] All subprocesses use shell=False
- [ ] API keys never logged (redaction in wrapper)
- [ ] Timeouts enforced (<60s for network ops)
- [ ] Root privilege checks (wireless tools, raw sockets)
- [ ] Binary availability checks at startup
- [ ] Error messages sanitized (no stack traces)
- [ ] Rate limiting enforced per tool per user

---

## Deployment Validation

```bash
# Check binary dependencies
which scapy && echo "✓ Scapy" || echo "✗ Scapy"
which tshark && echo "✓ tshark" || echo "✗ tshark"
which zeek && echo "✓ Zeek" || echo "✗ Zeek"
which testssl && echo "✓ testssl.sh" || echo "✗ testssl.sh"
which zaproxy && echo "✓ ZAP CLI" || echo "✗ ZAP CLI"
which dnsrecon && echo "✓ DNSRecon" || echo "✗ DNSRecon"
which masscan && echo "✓ Masscan" || echo "✗ Masscan"
which fierce && echo "✓ Fierce" || echo "✗ Fierce"

# Test tool registration
python3 -c "from loom.server import create_app; app = create_app(); print(f'Tools: {len(app._registered_tools)}')"

# Run minimal integration test
pytest tests/test_tools/test_network_forensics.py -k "test_packet_craft_tcp" -v
```

---

## Summary

This specification provides implementation details for **15 network forensics/infrastructure tools** (29 MCP functions) to integrate into Loom. Key features:

1. **Packet-level analysis** (Scapy, PyShark, Zeek)
2. **TLS/SSL auditing** (testssl.sh)
3. **Web security testing** (OWASP ZAP)
4. **Network reconnaissance** (DNSRecon, Masscan, Fierce)
5. **Security monitoring** (Suricata, osquery)
6. **Infrastructure management** (NetBox, Zabbix, ntopng)

Each tool includes:
- Complete function signature with Pydantic models
- Input validation strategy
- Return schema (JSON)
- Cost estimation
- Implementation notes
- Security considerations

**Estimated effort:** 157 hours (development, testing, documentation)  
**Recommended priority:** P1 (Scapy, PyShark, testssl.sh, OWASP ZAP) → P2 (remaining)
