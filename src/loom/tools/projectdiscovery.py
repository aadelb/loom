"""ProjectDiscovery reconnaissance suite tools — nuclei, katana, subfinder, httpx.

Integrates the ProjectDiscovery Go toolkit for vulnerability scanning, web crawling,
subdomain enumeration, and HTTP probing. All tools validate inputs to prevent
command injection and check binary availability before execution.

Reference: https://github.com/projectdiscovery
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any

from loom.validators import validate_url

logger = logging.getLogger("loom.tools.projectdiscovery")


def _validate_domain(domain: str) -> str:
    """Validate domain name to prevent command injection.

    Allows alphanumeric, dots, hyphens, and underscores.
    Returns the validated domain.

    Args:
        domain: domain name to validate

    Returns:
        The validated domain string

    Raises:
        ValueError: if domain contains disallowed characters
    """
    if not domain or len(domain) > 255:
        raise ValueError("domain must be 1-255 characters")

    # Allow alphanumeric, dots, hyphens, underscores
    if not re.match(r"^[a-z0-9._-]+$", domain, re.IGNORECASE):
        raise ValueError("domain contains disallowed characters")

    return domain




def _validate_domain_with_port(target: str) -> str:
    """Validate domain:port format to prevent command injection.

    Allows alphanumeric, dots, hyphens, underscores, and colons for ports.
    Returns the validated domain:port string.

    Args:
        target: domain:port string to validate (e.g., "example.com:8080")

    Returns:
        The validated domain:port string

    Raises:
        ValueError: if target contains disallowed characters or invalid port
    """
    if not target or len(target) > 261:  # 255 for domain + 5 for port + colon
        raise ValueError("domain:port must be 1-261 characters")

    # Check if it has a port
    if ':' in target:
        parts = target.rsplit(':', 1)
        if len(parts) != 2:
            raise ValueError("invalid domain:port format")
        domain_part, port_part = parts

        # Validate domain part
        if not re.match(r"^[a-z0-9._-]+$", domain_part, re.IGNORECASE):
            raise ValueError("domain contains disallowed characters")

        # Validate port part
        try:
            port = int(port_part)
            if port < 1 or port > 65535:
                raise ValueError(f"port {port} out of range 1-65535")
        except ValueError as exc:
            raise ValueError(f"invalid port: {str(exc)}") from exc

        return target
    else:
        # No port, just validate as domain
        return _validate_domain(target)


def _check_binary_exists(binary_name: str) -> tuple[bool, str | None]:
    """Check if a binary exists in PATH.

    Args:
        binary_name: name of the binary to check (e.g., 'subfinder')

    Returns:
        Tuple of (exists: bool, path: str | None)
    """
    path = shutil.which(binary_name)
    return (path is not None, path)


def research_subfinder(
    domain: str,
    timeout: int = 60,
) -> dict[str, Any]:
    """Enumerate subdomains using passive sources (subfinder).

    Uses the ProjectDiscovery subfinder binary to passively enumerate
    subdomains via 20+ DNS/certificate sources without active probing.

    Args:
        domain: target domain (e.g., "example.com")
        timeout: subprocess timeout in seconds (1-120, default 60)

    Returns:
        Dict with:
        - domain: the queried domain
        - subdomains: list of discovered subdomains
        - count: total number of subdomains found
        - sources_used: list of sources that found subdomains
        - error: error message if enumeration failed
        - warning: warning message if binary not found
    """
    try:
        domain = _validate_domain(domain)
    except ValueError as exc:
        return {"domain": domain, "error": str(exc), "count": 0, "subdomains": []}

    # Check binary exists
    exists, binary_path = _check_binary_exists("subfinder")
    if not exists:
        return {
            "domain": domain,
            "warning": "subfinder binary not found in PATH",
            "subdomains": [],
            "count": 0,
            "sources_used": [],
            "error": "subfinder not installed",
        }

    try:
        # Validate timeout
        if timeout < 1 or timeout > 120:
            raise ValueError("timeout must be 1-120 seconds")

        # Run subfinder with JSON output
        cmd = ["subfinder", "-d", domain, "-json"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        subdomains = []
        sources_used = set()

        # Parse JSON output (one JSON object per line)
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if "subdomain" in data:
                        subdomains.append(data["subdomain"])
                    if "source" in data:
                        sources_used.add(data["source"])
                except json.JSONDecodeError:
                    logger.warning("Failed to parse subfinder output line: %s", line)

        return {
            "domain": domain,
            "subdomains": sorted(list(set(subdomains))),  # Deduplicate and sort
            "count": len(set(subdomains)),
            "sources_used": sorted(list(sources_used)),
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "domain": domain,
            "error": f"subfinder timed out after {timeout} seconds",
            "count": 0,
            "subdomains": [],
        }
    except Exception as exc:
        logger.exception("subfinder execution failed")
        return {
            "domain": domain,
            "error": f"subfinder execution failed: {str(exc)}",
            "count": 0,
            "subdomains": [],
        }


def research_katana_crawl(
    url: str,
    depth: int = 3,
    max_pages: int = 100,
    timeout: int = 60,
) -> dict[str, Any]:
    """Crawl a URL using Katana web crawler (ProjectDiscovery).

    Next-generation web crawler with JavaScript rendering support,
    automatic subdomain discovery, and intelligent crawl depth management.

    Args:
        url: target URL to crawl (e.g., "https://example.com")
        depth: crawl depth (0-5, default 3)
        max_pages: maximum pages to crawl (1-1000, default 100)
        timeout: subprocess timeout in seconds (1-300, default 60)

    Returns:
        Dict with:
        - url: the queried URL
        - pages_crawled: total pages crawled
        - urls_found: list of discovered URLs
        - depth_reached: actual depth achieved
        - error: error message if crawl failed
        - warning: warning message if binary not found
    """
    try:
        url = validate_url(url)
    except ValueError as exc:
        return {
            "url": url,
            "error": str(exc),
            "pages_crawled": 0,
            "urls_found": [],
            "depth_reached": 0,
        }

    # Check binary exists
    exists, binary_path = _check_binary_exists("katana")
    if not exists:
        return {
            "url": url,
            "warning": "katana binary not found in PATH",
            "pages_crawled": 0,
            "urls_found": [],
            "depth_reached": 0,
            "error": "katana not installed",
        }

    try:
        # Validate parameters
        if depth < 0 or depth > 5:
            raise ValueError("depth must be 0-5")
        if max_pages < 1 or max_pages > 1000:
            raise ValueError("max_pages must be 1-1000")
        if timeout < 1 or timeout > 300:
            raise ValueError("timeout must be 1-300 seconds")

        # Run katana with JSON output
        cmd = [
            "katana",
            "-u", url,
            "-d", str(depth),
            "-p", str(max_pages),
            "-json",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        urls_found = []
        max_depth_reached = 0

        # Parse JSON output (one JSON object per line)
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if "url" in data:
                        urls_found.append(data["url"])
                    if "depth" in data and isinstance(data["depth"], int):
                        max_depth_reached = max(max_depth_reached, data["depth"])
                except json.JSONDecodeError:
                    logger.warning("Failed to parse katana output line: %s", line)

        unique_urls = sorted(list(set(urls_found)))  # Deduplicate and sort
        response = {
            "url": url,
            "pages_crawled": len(unique_urls),
            "urls_found": unique_urls,
            "depth_reached": max_depth_reached,
            "returncode": result.returncode,
        }
        if result.returncode != 0 and result.stderr:
            response["error"] = f"katana exited with code {result.returncode}: {result.stderr}"
        return response

    except subprocess.TimeoutExpired:
        return {
            "url": url,
            "error": f"katana timed out after {timeout} seconds",
            "pages_crawled": 0,
            "urls_found": [],
            "depth_reached": 0,
        }
    except Exception as exc:
        logger.exception("katana execution failed")
        return {
            "url": url,
            "error": f"katana execution failed: {str(exc)}",
            "pages_crawled": 0,
            "urls_found": [],
            "depth_reached": 0,
        }


def research_httpx_probe(
    targets: list[str],
    ports: str = "80,443,8080,8443",
    timeout: int = 60,
) -> dict[str, Any]:
    """Probe targets for live HTTP services using httpx (ProjectDiscovery).

    Multi-purpose HTTP prober that detects live hosts, extracts response
    metadata (status code, title, technology stack), and supports
    certificate-based host discovery.

    Args:
        targets: list of target URLs or IPs (max 100 items)
        ports: comma-separated ports to probe (default "80,443,8080,8443")
        timeout: subprocess timeout in seconds (1-300, default 60)

    Returns:
        Dict with:
        - targets_checked: total targets checked
        - alive: list of dicts with {url, status_code, title, server, tech}
        - count: number of alive hosts found
        - error: error message if probe failed
        - warning: warning message if binary not found
    """
    try:
        # Validate targets list
        if not targets or len(targets) > 100:
            raise ValueError("targets list must have 1-100 items")

        # Validate ports
        if not ports or not ports.strip():
            raise ValueError("ports cannot be empty")
        # Allow comma-separated port numbers
        if not re.match(r"^[0-9,]+$", ports):
            raise ValueError("ports must be comma-separated numbers")
        # Check each port is valid (1-65535)
        ports_list = [p.strip() for p in ports.split(",")]
        for port_str in ports_list:
            try:
                port = int(port_str)
                if port < 1 or port > 65535:
                    raise ValueError(f"port {port} out of range 1-65535")
            except ValueError as exc:
                raise ValueError(f"invalid port: {str(exc)}") from exc

        validated_targets = []
        for target in targets:
            try:
                validated_targets.append(validate_url(target))
            except ValueError:
                # If not a full URL, treat as domain or domain:port
                try:
                    target = _validate_domain_with_port(target)
                    # If it doesn't have a scheme, add http://
                    if not target.startswith(('http://', 'https://')):
                        validated_targets.append(f"http://{target}")
                    else:
                        validated_targets.append(target)
                except ValueError as exc:
                    logger.warning("Invalid target: %s - %s", target, exc)

        if not validated_targets:
            raise ValueError("no valid targets provided")

    except ValueError as exc:
        return {
            "targets_checked": 0,
            "alive": [],
            "count": 0,
            "error": str(exc),
        }

    # Check binary exists
    exists, binary_path = _check_binary_exists("httpx")
    if not exists:
        return {
            "targets_checked": len(targets),
            "warning": "httpx binary not found in PATH",
            "alive": [],
            "count": 0,
            "error": "httpx not installed",
        }

    try:
        # Validate parameters
        if timeout < 1 or timeout > 300:
            raise ValueError("timeout must be 1-300 seconds")

        # Create temporary file with targets
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
        ) as f:
            for target in validated_targets:
                f.write(target + "\n")
            targets_file = f.name

        try:
            # Run httpx with JSON output
            cmd = [
                "httpx",
                "-l", targets_file,
                "-ports", ports,
                "-json",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            alive_hosts = []

            # Parse JSON output (one JSON object per line)
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        tech = data.get("technology", [])
                        host_entry = {
                            "url": data.get("url", ""),
                            "status_code": data.get("status-code", 0),
                            "title": data.get("title", ""),
                            "server": data.get("server", ""),
                            "tech": tech if isinstance(tech, list) else [tech],
                        }
                        alive_hosts.append(host_entry)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse httpx output line: %s", line)

            response = {
                "targets_checked": len(validated_targets),
                "alive": alive_hosts,
                "count": len(alive_hosts),
                "returncode": result.returncode,
            }
            if result.returncode != 0 and result.stderr:
                response["error"] = f"httpx exited with code {result.returncode}: {result.stderr}"
            return response

        finally:
            # Clean up temporary file
            try:
                os.unlink(targets_file)
            except Exception as exc:
                logger.warning("Failed to clean up temp file: %s", exc)

    except subprocess.TimeoutExpired:
        return {
            "targets_checked": len(validated_targets),
            "error": f"httpx timed out after {timeout} seconds",
            "alive": [],
            "count": 0,
        }
    except Exception as exc:
        logger.exception("httpx execution failed")
        return {
            "targets_checked": len(validated_targets),
            "error": f"httpx execution failed: {str(exc)}",
            "alive": [],
            "count": 0,
        }


def research_nuclei_scan(
    target: str,
    templates: str = "cves,exposures",
    severity: str = "medium,high,critical",
    timeout: int = 120,
) -> dict[str, Any]:
    """Scan target for vulnerabilities using Nuclei (ProjectDiscovery).

    Template-based vulnerability scanner with extensive coverage of
    web vulnerabilities, CVEs, misconfigurations, and exposures.

    Args:
        target: target URL to scan (e.g., "https://example.com")
        templates: comma-separated template types (default "cves,exposures")
        severity: comma-separated severity filters (default "medium,high,critical")
        timeout: subprocess timeout in seconds (1-600, default 120)

    Returns:
        Dict with:
        - target: the scanned target
        - vulnerabilities: list of dicts with {template, severity, url, matched}
        - count: total vulnerabilities found
        - error: error message if scan failed
        - warning: warning message if binary not found
    """
    try:
        target = validate_url(target)
    except ValueError as exc:
        return {
            "target": target,
            "error": str(exc),
            "vulnerabilities": [],
            "count": 0,
        }

    # Check binary exists
    exists, binary_path = _check_binary_exists("nuclei")
    if not exists:
        return {
            "target": target,
            "warning": "nuclei binary not found in PATH",
            "vulnerabilities": [],
            "count": 0,
            "error": "nuclei not installed",
        }

    try:
        # Validate parameters
        if timeout < 1 or timeout > 600:
            raise ValueError("timeout must be 1-600 seconds")

        # Validate templates and severity (allow alphanumeric, hyphens, commas)
        if not re.match(r"^[a-z0-9,\-]+$", templates.lower()):
            raise ValueError("templates contains invalid characters")
        if not re.match(r"^[a-z0-9,\-]+$", severity.lower()):
            raise ValueError("severity contains invalid characters")

        # Run nuclei with JSON output
        cmd = [
            "nuclei",
            "-u", target,
            "-t", templates,
            "-s", severity,
            "-json",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        vulnerabilities = []

        # Parse JSON output (one JSON object per line)
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    vuln_entry = {
                        "template": data.get("template-id", ""),
                        "severity": data.get("severity", ""),
                        "url": data.get("matched-at", ""),
                        "matched": data.get("matcher-name", ""),
                        "type": data.get("type", ""),
                    }
                    vulnerabilities.append(vuln_entry)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse nuclei output line: %s", line)

        return {
            "target": target,
            "vulnerabilities": vulnerabilities,
            "count": len(vulnerabilities),
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "target": target,
            "error": f"nuclei timed out after {timeout} seconds",
            "vulnerabilities": [],
            "count": 0,
        }
    except Exception as exc:
        logger.exception("nuclei execution failed")
        return {
            "target": target,
            "error": f"nuclei execution failed: {str(exc)}",
            "vulnerabilities": [],
            "count": 0,
        }
