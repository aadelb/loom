"""research_web_check — Comprehensive website OSINT analyzer.

Performs multiple checks on a domain: DNS records, SSL certificate,
security headers, cookies, trackers, technology stack, WHOIS data, etc.
"""

from __future__ import annotations

import logging
import re
import socket
import ssl
from datetime import UTC, datetime
from typing import Any

import httpx

from loom.validators import EXTERNAL_TIMEOUT_SECS, validate_url

logger = logging.getLogger("loom.tools.webcheck_backend")

# Common tracking scripts and patterns
TRACKER_PATTERNS = {
    "google_analytics": (r"google-analytics|_gat\.|gtag\.js", "Google Analytics"),
    "google_ads": (r"googleads|doubleclick", "Google Ads"),
    "facebook_pixel": (r"facebook\.com/tr|pixel\.quantserve", "Facebook Pixel"),
    "hotjar": (r"hotjar\.com", "Hotjar"),
    "intercom": (r"intercom\.io", "Intercom"),
    "segment": (r"segment\.com|analytics\.js", "Segment"),
    "mixpanel": (r"mixpanel\.com", "Mixpanel"),
    "amplitude": (r"amplitude\.com", "Amplitude"),
    "twitter_analytics": (r"twitter\.com/i/|analytics\.twitter", "Twitter Analytics"),
    "linkedin_insight": (r"linkedin\.com/px", "LinkedIn Insight"),
    "tiktok_pixel": (r"tiktok\.com/.*pixel", "TikTok Pixel"),
}

# Technology detection patterns (simplified Wappalyzer-style)
TECH_PATTERNS = {
    "framework": {
        "React": r"<script[^>]*>.*react|\"react\"|_react",
        "Vue": r"<script[^>]*>.*vue\.js|__vue__|Vue\.version",
        "Angular": r"ng-app|ng-controller|angular\.js",
        "jQuery": r"jquery|jQuery",
        "Next.js": r"__NEXT_|_next/",
        "Nuxt": r"__NUXT__|_nuxt/",
        "Svelte": r"svelte",
    },
    "cms": {
        "WordPress": r"wp-content|wp-includes|wordpress",
        "Drupal": r"drupal\.settings|sites/all",
        "Joomla": r"joomla|component=",
        "Magento": r"magento|mage",
        "Shopify": r"cdn\.shopify\.com|myshopify\.com",
    },
    "web_server": {
        "Apache": r"Apache|Apache\.",
        "Nginx": r"nginx",
        "IIS": r"IIS|Microsoft-IIS",
        "Caddy": r"Caddy",
    },
    "language": {
        "PHP": r"php|X-Powered-By.*PHP",
        "Python": r"X-Powered-By.*Python",
        "Node.js": r"X-Powered-By.*Node|Express",
        "Java": r"Java|X-Powered-By.*Java",
        "ASP.NET": r"X-AspNet|ASP\.NET",
    },
}


def research_web_check(domain: str, checks: list[str] | None = None) -> dict[str, Any]:
    """Comprehensive website OSINT analysis.

    Performs multiple checks on a domain: DNS records, SSL certificate,
    security headers, cookies, trackers, technology stack, WHOIS, etc.

    Args:
        domain: Target domain (e.g., 'example.com')
        checks: Specific checks to run (default: all). Options:
                dns, ssl, headers, cookies, trackers, tech, whois, robots

    Returns:
        Dict with keys:
          - domain: input domain
          - checks_run: list of checks performed
          - dns: DNS resolution results (A, AAAA, MX, TXT records)
          - ssl: SSL certificate info
          - headers: HTTP response headers (sample)
          - security_headers: security-related headers analysis
          - cookies: Cookies found in response
          - trackers: Third-party tracking scripts detected
          - tech_stack: Detected technologies
          - robots: robots.txt content (truncated)
          - error: str (if critical operation failed)
    """
    # Validate domain
    domain = _validate_domain(domain)
    if not domain:
        return {"domain": domain, "error": "Invalid domain format"}

    # Default to all checks if not specified
    if checks is None:
        checks = ["dns", "ssl", "headers", "cookies", "trackers", "tech", "robots"]

    # Normalize check names
    checks = [c.lower() for c in checks]
    valid_checks = {"dns", "ssl", "headers", "cookies", "trackers", "tech", "robots"}
    checks = [c for c in checks if c in valid_checks]

    if not checks:
        return {
            "domain": domain,
            "error": "No valid checks specified",
        }

    result: dict[str, Any] = {
        "domain": domain,
        "checks_run": checks,
    }

    # Construct URL for HTTP requests
    url = f"https://{domain}"

    # Try to fetch the domain to get response data
    response_data = _fetch_url(url)

    # Run each check
    if "dns" in checks:
        result["dns"] = _check_dns(domain)

    if "ssl" in checks:
        result["ssl"] = _check_ssl(domain)

    if response_data:
        response_headers = response_data.get("headers", {})
        response_html = response_data.get("html", "")

        if "headers" in checks:
            result["headers"] = _check_headers(response_headers)

        if "cookies" in checks:
            result["cookies"] = _check_cookies(response_headers)

        if "trackers" in checks:
            result["trackers"] = _check_trackers(response_html, response_headers)

        if "tech" in checks:
            result["tech_stack"] = _detect_tech(response_html, response_headers)

    if "robots" in checks:
        result["robots"] = _check_robots(url)

    return result


def _validate_domain(domain: str) -> str:
    """Validate and normalize domain name.

    Args:
        domain: domain name

    Returns:
        Validated domain (lowercased, stripped)
    """
    if not domain or not isinstance(domain, str):
        return ""

    domain = domain.strip().lower()

    # Remove trailing www. or https:// prefix if present
    if domain.startswith("www."):
        domain = domain[4:]
    if domain.startswith("https://"):
        domain = domain[8:]
    if domain.startswith("http://"):
        domain = domain[7:]

    # Basic validation: alphanumeric, dots, hyphens
    if not re.match(r"^[a-z0-9.-]+$", domain):
        return ""

    # Must have at least one dot
    if "." not in domain:
        return ""

    # Max 255 chars
    if len(domain) > 255:
        return ""

    return domain


def _fetch_url(url: str) -> dict[str, Any] | None:
    """Fetch URL and return headers and HTML content.

    Args:
        url: Full URL to fetch

    Returns:
        Dict with 'headers' and 'html' keys, or None on error
    """
    try:
        with httpx.Client(
            timeout=EXTERNAL_TIMEOUT_SECS,
            follow_redirects=True,
        ) as client:
            response = client.get(url)
            return {
                "headers": dict(response.headers),
                "html": response.text,
            }
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def _check_dns(domain: str) -> dict[str, Any]:
    """Check DNS records for the domain.

    Args:
        domain: domain name

    Returns:
        Dict with A, AAAA, MX, TXT records
    """
    result: dict[str, Any] = {
        "domain": domain,
        "a_records": [],
        "aaaa_records": [],
        "mx_records": [],
        "txt_records": [],
        "errors": [],
    }

    try:
        # A records (IPv4)
        try:
            ips = socket.getaddrinfo(domain, None, socket.AF_INET)
            result["a_records"] = list(set(ip[4][0] for ip in ips))
        except socket.gaierror as e:
            result["errors"].append(f"A record lookup failed: {e}")

        # AAAA records (IPv6)
        try:
            ips = socket.getaddrinfo(domain, None, socket.AF_INET6)
            result["aaaa_records"] = list(set(ip[4][0] for ip in ips))
        except socket.gaierror:
            pass  # IPv6 may not be available

        # MX records (requires dnspython or similar)
        try:
            import dns.resolver

            try:
                mx_records = dns.resolver.resolve(domain, "MX")
                result["mx_records"] = [
                    {
                        "priority": mx.preference,
                        "exchange": str(mx.exchange).rstrip("."),
                    }
                    for mx in mx_records
                ]
            except Exception as e:
                result["errors"].append(f"MX record lookup: {e}")

            # TXT records
            try:
                txt_records = dns.resolver.resolve(domain, "TXT")
                result["txt_records"] = [str(txt) for txt in txt_records]
            except Exception as e:
                logger.debug("txt_record_lookup_error: %s", e)

        except ImportError:
            result["errors"].append("dnspython not available for MX/TXT lookup")

    except Exception as e:
        logger.exception("DNS check error")
        result["errors"].append(f"Unexpected error: {e}")

    return result


def _check_ssl(domain: str) -> dict[str, Any]:
    """Check SSL certificate for the domain.

    Args:
        domain: domain name

    Returns:
        Dict with SSL info
    """
    result: dict[str, Any] = {
        "domain": domain,
        "has_ssl": False,
        "subject": {},
        "issuer": {},
        "not_before": None,
        "not_after": None,
        "days_until_expiry": None,
        "is_expired": False,
        "san": [],
    }

    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(socket.AF_INET), server_hostname=domain) as s:
            s.settimeout(10)
            s.connect((domain, 443))

            cert_dict = s.getpeercert()

        if not cert_dict:
            result["error"] = "No certificate returned"
            return result

        result["has_ssl"] = True

        # Parse subject and issuer
        result["subject"] = _parse_dn(cert_dict.get("subject", ()))
        result["issuer"] = _parse_dn(cert_dict.get("issuer", ()))

        # Parse dates
        not_before = _parse_cert_date(cert_dict.get("notBefore", ""))
        not_after = _parse_cert_date(cert_dict.get("notAfter", ""))

        result["not_before"] = not_before.isoformat() if not_before else None
        result["not_after"] = not_after.isoformat() if not_after else None

        if not_after:
            delta = not_after - datetime.now(UTC)
            result["days_until_expiry"] = delta.days
            result["is_expired"] = delta.total_seconds() < 0

        # Extract SANs
        result["san"] = _extract_san(cert_dict.get("subjectAltName", ()))

    except socket.timeout:
        result["error"] = "SSL connection timeout"
    except socket.gaierror as e:
        result["error"] = f"DNS resolution failed: {e}"
    except ssl.SSLError as e:
        result["error"] = f"SSL error: {e}"
    except Exception as e:
        logger.exception("SSL check error")
        result["error"] = f"Unexpected error: {e}"

    return result


def _check_headers(headers: dict[str, str]) -> dict[str, str]:
    """Analyze response headers.

    Args:
        headers: HTTP response headers

    Returns:
        Dict with key headers (server, content-type, etc.)
    """
    result: dict[str, str] = {}

    # Key headers to extract
    key_headers = [
        "server",
        "content-type",
        "content-length",
        "cache-control",
        "x-powered-by",
        "x-aspnet-version",
        "x-frame-options",
        "strict-transport-security",
        "content-security-policy",
    ]

    for key in key_headers:
        # Case-insensitive lookup
        for h_key, h_value in headers.items():
            if h_key.lower() == key.lower():
                result[key.lower()] = h_value
                break

    return result


def _check_cookies(headers: dict[str, str]) -> dict[str, Any]:
    """Extract cookies from Set-Cookie headers.

    Args:
        headers: HTTP response headers

    Returns:
        Dict with cookie info
    """
    cookies: list[dict[str, str]] = []

    # Find Set-Cookie headers (case-insensitive)
    for key, value in headers.items():
        if key.lower() == "set-cookie":
            # Parse cookie name=value; attributes
            parts = value.split(";")
            if parts:
                name_value = parts[0].strip()
                if "=" in name_value:
                    name, cookie_val = name_value.split("=", 1)
                    cookie: dict[str, str] = {
                        "name": name.strip(),
                        "value": cookie_val.strip(),
                    }
                    # Parse attributes
                    for attr in parts[1:]:
                        attr = attr.strip()
                        if "=" in attr:
                            attr_name, attr_value = attr.split("=", 1)
                            cookie[attr_name.strip().lower()] = attr_value.strip()
                        else:
                            cookie[attr.lower()] = "true"

                    cookies.append(cookie)

    return {
        "count": len(cookies),
        "cookies": cookies,
    }


def _check_trackers(html: str, headers: dict[str, str]) -> dict[str, Any]:
    """Detect tracking scripts in HTML and headers.

    Args:
        html: HTML content
        headers: HTTP response headers

    Returns:
        Dict with trackers found
    """
    found_trackers: list[dict[str, str]] = []

    # Check HTML for tracker patterns
    for tracker_id, (pattern, name) in TRACKER_PATTERNS.items():
        if re.search(pattern, html, re.IGNORECASE):
            found_trackers.append({
                "id": tracker_id,
                "name": name,
                "source": "html",
            })

    # Check headers for tracker domains
    for key, value in headers.items():
        for tracker_id, (pattern, name) in TRACKER_PATTERNS.items():
            if re.search(pattern, value, re.IGNORECASE):
                # Avoid duplicates
                if not any(t["id"] == tracker_id for t in found_trackers):
                    found_trackers.append({
                        "id": tracker_id,
                        "name": name,
                        "source": "headers",
                    })

    return {
        "count": len(found_trackers),
        "trackers": found_trackers,
    }


def _detect_tech(html: str, headers: dict[str, str]) -> dict[str, list[str]]:
    """Detect technologies used on the website.

    Args:
        html: HTML content
        headers: HTTP response headers

    Returns:
        Dict with technologies by category
    """
    detected: dict[str, list[str]] = {
        "framework": [],
        "cms": [],
        "web_server": [],
        "language": [],
    }

    combined = html + " ".join(f"{k}: {v}" for k, v in headers.items())

    for category, patterns in TECH_PATTERNS.items():
        for tech_name, pattern in patterns.items():
            if re.search(pattern, combined, re.IGNORECASE):
                detected[category].append(tech_name)

    # Remove duplicates
    for category in detected:
        detected[category] = list(set(detected[category]))

    return detected


def _check_robots(url: str) -> dict[str, Any]:
    """Fetch and analyze robots.txt.

    Args:
        url: Base URL of the site

    Returns:
        Dict with robots.txt info
    """
    robots_url = url.rstrip("/") + "/robots.txt"
    result: dict[str, Any] = {
        "url": robots_url,
        "found": False,
        "content": "",
        "user_agents": [],
        "disallowed_paths": [],
    }

    try:
        with httpx.Client(timeout=EXTERNAL_TIMEOUT_SECS) as client:
            response = client.get(robots_url)

        if response.status_code == 200:
            result["found"] = True
            content = response.text
            # Truncate to 2000 chars
            result["content"] = content[:2000]

            # Parse basic robots.txt rules
            current_user_agent = "default"
            user_agents_dict: dict[str, list[str]] = {}

            for line in content.split("\n"):
                line = line.strip().split("#")[0].strip()
                if not line:
                    continue

                if line.lower().startswith("user-agent:"):
                    current_user_agent = line.split(":", 1)[1].strip()
                    if current_user_agent not in user_agents_dict:
                        user_agents_dict[current_user_agent] = []

                elif line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        if current_user_agent not in user_agents_dict:
                            user_agents_dict[current_user_agent] = []
                        user_agents_dict[current_user_agent].append(path)

            result["user_agents"] = list(user_agents_dict.keys())

            # Collect all disallowed paths
            for paths in user_agents_dict.values():
                result["disallowed_paths"].extend(paths)
            result["disallowed_paths"] = list(set(result["disallowed_paths"]))

    except Exception as e:
        logger.warning("Failed to fetch robots.txt: %s", e)
        result["error"] = str(e)

    return result


def _parse_dn(dn_tuple: tuple[tuple[tuple[str, str], ...], ...]) -> dict[str, str]:
    """Parse X.509 DN to dict.

    Args:
        dn_tuple: DN tuple from SSL cert

    Returns:
        Dict with RDN components
    """
    result = {}
    for rdn in dn_tuple:
        for type_name, value in rdn:
            short_name = {
                "commonName": "CN",
                "organizationName": "O",
                "countryName": "C",
                "stateOrProvinceName": "ST",
                "localityName": "L",
                "organizationalUnitName": "OU",
                "emailAddress": "EMAIL",
            }.get(type_name, type_name)

            result[short_name] = value

    return result


def _parse_cert_date(date_str: str) -> datetime | None:
    """Parse SSL certificate date.

    Args:
        date_str: Date string from cert (format: 'Jan  1 00:00:00 2025 GMT')

    Returns:
        datetime object or None
    """
    if not date_str:
        return None

    try:
        date_str_clean = " ".join(date_str.replace("GMT", "").split())
        dt = datetime.strptime(date_str_clean, "%b %d %H:%M:%S %Y")
        return dt.replace(tzinfo=UTC)
    except ValueError as e:
        logger.warning("Failed to parse certificate date '%s': %s", date_str, e)
        return None


def _extract_san(san_tuple: tuple[tuple[str, str], ...]) -> list[str]:
    """Extract Subject Alternative Names from cert.

    Args:
        san_tuple: SAN tuple from cert

    Returns:
        List of SAN strings
    """
    result = []
    for san_type, san_value in san_tuple:
        result.append(f"{san_type}:{san_value}")
    return result
