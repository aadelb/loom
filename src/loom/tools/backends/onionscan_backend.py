"""research_onionscan — Check .onion services for misconfigurations via OnionScan.

OnionScan is a forensic analysis tool for Tor hidden services that detects
security misconfigurations, information leaks, and weak configurations.
This module wraps the onionscan binary for automated vulnerability detection
on .onion domains.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from typing import Any

from loom.cli_checker import is_available
from loom.error_responses import handle_tool_errors
from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.onionscan_backend")

# Tor SOCKS5 proxy endpoint
DEFAULT_SOCKS5_PROXY = "127.0.0.1:9050"


def _validate_onion_url(url: str) -> str:
	"""Validate .onion URL.

	Args:
		url: .onion URL or hostname

	Returns:
		The validated URL

	Raises:
		ValueError: if URL is invalid
	"""
	url = url.strip() if isinstance(url, str) else ""

	if not url or len(url) > 256:
		raise ValueError("onion_url must be 1-256 characters")

	# Check if it's a valid .onion address
	# v2 onions: 16 characters (0-9, a-z)
	# v3 onions: 56 characters (0-9, a-z)
	if ".onion" in url:
		# Full URL format
		if not url.startswith(("http://", "https://")):
			# Add default http:// prefix
			url = f"http://{url}"
	else:
		# Assume it's a hostname, add .onion suffix if not present
		if not url.endswith(".onion"):
			raise ValueError("URL must be a .onion domain or include .onion suffix")

	# Strict allowlist validation for command-line safety
	# Allow only alphanumeric, dots, hyphens, colons (for port), slashes, and @ (for userinfo)
	import re
	if not re.match(r"^https?://[a-z0-9:/@\-\.]+\.onion(:\d+)?(/[a-z0-9\-._~:/?#\[\]@!$&'()*+,;=]*)?$", url):
		raise ValueError("URL contains disallowed characters or invalid format")

	return url


def _validate_timeout(timeout: int) -> int:
	"""Validate timeout parameter.

	Args:
		timeout: Timeout in seconds

	Returns:
		The validated timeout

	Raises:
		ValueError: if timeout is invalid
	"""
	if not isinstance(timeout, int) or timeout < 10 or timeout > 300:
		raise ValueError("timeout must be an integer between 10 and 300 seconds")
	return timeout


def _check_onionscan_available() -> tuple[bool, str]:
	"""Check if onionscan binary is available.

	Returns:
		Tuple of (available: bool, message: str)
	"""
	if is_available("onionscan"):
		return True, "onionscan binary found"
	return False, "onionscan not installed. Install from: https://github.com/s-rah/onionscan"


def _check_tor_available() -> tuple[bool, str]:
	"""Check if Tor is running and accessible via SOCKS5.

	Returns:
		Tuple of (available: bool, message: str)
	"""
	try:
		# Try to connect to Tor SOCKS5 proxy
		import socket

		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			sock.settimeout(5)
			host, port_str = DEFAULT_SOCKS5_PROXY.split(":")
			result = sock.connect_ex((host, int(port_str)))

			if result == 0:
				return True, "Tor SOCKS5 proxy available"
			else:
				return False, f"Tor SOCKS5 proxy not responding at {DEFAULT_SOCKS5_PROXY}"
		finally:
			sock.close()

	except Exception as e:
		return False, f"Tor check failed: {type(e).__name__}: {e}"


@handle_tool_errors("research_onionscan")
async def research_onionscan(
	onion_url: str,
	timeout: int = 60,
) -> dict[str, Any]:
	"""Scan .onion service for misconfigurations and information leaks.

	Uses the onionscan tool to audit Tor hidden services for security issues,
	leaked hostnames, SSL/TLS problems, and other misconfigurations. Requires
	Tor to be running locally on SOCKS5 port 9050.

	Args:
		onion_url: .onion domain or URL (e.g., "example.onion" or "http://example.onion")
		timeout: Scan timeout in seconds (10-300). Default 60.

	Returns:
		Dict with keys:
		- url: the scanned .onion URL
		- success: whether the scan completed
		- misconfigurations: list of identified security issues
		- leaked_hostnames: list of hostnames leaked via reverse DNS or certs
		- ssl_issues: list of SSL/TLS problems (weak ciphers, expired certs, etc.)
		- server_info: detected server software and banner info
		- scan_score: overall security score (0-100)
		- tor_available: whether Tor was accessible
		- onionscan_available: whether onionscan tool was available
		- error: error message if scan failed (optional)
	"""
	validate_url(onion_url)

	# Validate inputs
	try:
		onion_url = _validate_onion_url(onion_url)
		timeout = _validate_timeout(timeout)
	except ValueError as e:
		return {
			"url": onion_url,
			"success": False,
			"error": str(e),
			"onionscan_available": False,
			"tor_available": False,
		}

	logger.info("onionscan_scan url=%s", onion_url)

	# Check prerequisites
	onionscan_available, onionscan_msg = _check_onionscan_available()
	tor_available, tor_msg = _check_tor_available()

	if not onionscan_available:
		return {
			"url": onion_url,
			"success": False,
			"error": onionscan_msg,
			"onionscan_available": False,
			"tor_available": tor_available,
		}

	if not tor_available:
		return {
			"url": onion_url,
			"success": False,
			"error": f"Tor not available: {tor_msg}",
			"onionscan_available": True,
			"tor_available": False,
		}

	# Run onionscan
	try:
		# Build onionscan command with JSON output
		cmd = [
			"onionscan",
			"--jsonreport",
			"--socks",
			DEFAULT_SOCKS5_PROXY,
			onion_url,
		]

		result = await asyncio.to_thread(
			subprocess.run,
			cmd,
			capture_output=True,
			text=True,
			timeout=timeout,
			check=False,
		)

		if result.returncode != 0:
			logger.warning("onionscan_failed returncode=%d stderr=%s", result.returncode, result.stderr)
			return {
				"url": onion_url,
				"success": False,
				"error": f"onionscan exited with code {result.returncode}",
				"stderr": result.stderr[:500],
				"onionscan_available": True,
				"tor_available": True,
			}

		# Try to parse JSON output
		try:
			output = json.loads(result.stdout)
		except json.JSONDecodeError:
			logger.warning("onionscan_json_parse_failed")
			return {
				"url": onion_url,
				"success": False,
				"error": "Failed to parse onionscan JSON output",
				"raw_output": result.stdout[:1000],
				"onionscan_available": True,
				"tor_available": True,
			}

		# Extract and structure findings
		misconfigurations = []
		leaked_hostnames = []
		ssl_issues = []
		server_info = {}
		scan_score = 100

		# Parse misconfigurations
		if "Misconfigurations" in output:
			misconfigurations = output.get("Misconfigurations", [])
			# Each misconfiguration reduces score
			scan_score -= min(len(misconfigurations) * 5, 30)

		# Parse leaked hostnames
		if "LeakedHostnames" in output:
			leaked_hostnames = output.get("LeakedHostnames", [])
			scan_score -= min(len(leaked_hostnames) * 3, 20)

		# Parse SSL/TLS issues
		if "SSLIssues" in output:
			ssl_issues = output.get("SSLIssues", [])
			scan_score -= min(len(ssl_issues) * 4, 20)

		# Parse server info
		if "ServerInfo" in output:
			server_info = output.get("ServerInfo", {})

		# Additional info extraction
		hostname = output.get("Hostname", "")
		port = output.get("Port", 80)
		protocol = output.get("Protocol", "http")

		return {
			"url": onion_url,
			"hostname": hostname,
			"port": port,
			"protocol": protocol,
			"success": True,
			"misconfigurations": misconfigurations,
			"leaked_hostnames": leaked_hostnames,
			"ssl_issues": ssl_issues,
			"server_info": server_info,
			"scan_score": max(0, scan_score),  # Ensure score is 0-100
			"onionscan_available": True,
			"tor_available": True,
		}

	except TimeoutError:
		return {
			"url": onion_url,
			"success": False,
			"error": "onionscan scan timeout",
			"onionscan_available": True,
			"tor_available": True,
		}
	except FileNotFoundError:
		return {
			"url": onion_url,
			"success": False,
			"error": "onionscan binary not found in PATH",
			"onionscan_available": False,
			"tor_available": True,
		}
	except Exception as e:
		logger.exception("onionscan_subprocess_error")
		return {
			"url": onion_url,
			"success": False,
			"error": f"onionscan subprocess error: {type(e).__name__}: {e}",
			"onionscan_available": True,
			"tor_available": True,
		}
