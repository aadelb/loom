"""research_supercookie_check — Detect supercookie and covert tracking vectors."""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from urllib.parse import urljoin

import httpx

from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.supercookie_backend")

# Common favicon paths and naming patterns
_FAVICON_PATHS = [
	"/favicon.ico",
	"/apple-touch-icon.png",
	"/apple-touch-icon-precomposed.png",
	"/.well-known/apple-touch-icon.png",
	"/icon.png",
	"/logo.png",
	"/favicon.png",
]


def _is_valid_domain(domain: str) -> bool:
	"""Validate domain format (basic check).

	Args:
		domain: Domain name to validate

	Returns:
		True if domain passes basic validation
	"""
	if not domain or len(domain) > 255:
		return False
	# Block localhost and private IPs
	if domain in ("localhost", "127.0.0.1", "::1"):
		return False
	# Must have a dot for valid domain (not strictly true but good heuristic)
	if "." not in domain and not domain.startswith("http"):
		return False
	return True


def _build_url(domain: str, path: str) -> str:
	"""Build URL from domain and path, handling http/https prefix.

	Args:
		domain: Domain name (with or without scheme)
		path: Path to append

	Returns:
		Full URL
	"""
	if not domain.startswith(("http://", "https://")):
		domain = f"https://{domain}"
	return urljoin(domain, path)


def _check_etag_tracking(domain: str, timeout: int = 10) -> dict[str, Any]:
	"""Check if domain uses ETag headers for tracking.

	ETags can be used as persistent supercookies if the server generates
	deterministic ETags based on client fingerprints.

	Args:
		domain: Domain to check
		timeout: HTTP request timeout

	Returns:
		Dict with etag_present, etag_values, etag_consistency
	"""
	result = {
		"etag_present": False,
		"etag_values": [],
		"etag_consistency": False,
		"suspicious": False,
	}

	try:
		with httpx.Client(timeout=timeout) as client:
			url = _build_url(domain, "/")

			# Make multiple requests to same resource
			etags = []
			for i in range(2):
				try:
					resp = client.get(url, follow_redirects=True)
					if "etag" in resp.headers:
						etag_value = resp.headers.get("etag", "")
						etags.append(etag_value)
						result["etag_present"] = True
				except Exception:
					pass

			result["etag_values"] = etags

			# If we got same ETag twice, it might be tracking (or legitimate caching)
			if len(set(etags)) == 1 and len(etags) > 1:
				result["etag_consistency"] = True
				# If ETag is deterministic, it could be used for tracking
				result["suspicious"] = True

	except Exception as exc:
		logger.debug("etag_tracking_check_failed domain=%s: %s", domain, exc)

	return result


def _check_cache_control_abuse(domain: str, timeout: int = 10) -> dict[str, Any]:
	"""Detect cache-control header abuse for supercookie behavior.

	Some websites use creative Cache-Control directives to create
	persistent cross-site identifiers.

	Args:
		domain: Domain to check
		timeout: HTTP request timeout

	Returns:
		Dict with suspicious_cache_patterns
	"""
	result = {
		"suspicious_patterns": [],
		"cache_control_present": False,
		"risk": False,
	}

	try:
		with httpx.Client(timeout=timeout) as client:
			url = _build_url(domain, "/")
			resp = client.head(url, follow_redirects=True)

			cache_control = resp.headers.get("cache-control", "").lower()
			if cache_control:
				result["cache_control_present"] = True

				# Check for unusual patterns
				suspicious_patterns = [
					"public",
					"immutable",
					"s-maxage",
				]

				for pattern in suspicious_patterns:
					if pattern in cache_control:
						result["suspicious_patterns"].append(pattern)

				# If using very long max-age with public + immutable, could be suspicious
				if "immutable" in cache_control and ("max-age" in cache_control or "s-maxage" in cache_control):
					result["risk"] = True

	except Exception as exc:
		logger.debug("cache_control_check_failed domain=%s: %s", domain, exc)

	return result


def _check_hsts_supercookie(domain: str, timeout: int = 10) -> dict[str, Any]:
	"""Detect HSTS header abuse for supercookie/covert channel.

	HSTS can be abused to leak information via state in HSTS preload lists.
	This checks for unusual HSTS configurations.

	Args:
		domain: Domain to check
		timeout: HTTP request timeout

	Returns:
		Dict with hsts_present, max_age, includes_subdomains
	"""
	result = {
		"hsts_present": False,
		"max_age": None,
		"includes_subdomains": False,
		"preload": False,
		"suspicious": False,
	}

	try:
		with httpx.Client(timeout=timeout) as client:
			url = _build_url(domain, "/")
			resp = client.get(url, follow_redirects=True)

			hsts_header = resp.headers.get("strict-transport-security", "")
			if hsts_header:
				result["hsts_present"] = True

				# Parse max-age
				if "max-age=" in hsts_header.lower():
					try:
						max_age_part = [
							p.strip() for p in hsts_header.split(";") if "max-age=" in p
						][0]
						max_age_value = int(max_age_part.split("=")[1])
						result["max_age"] = max_age_value
					except (ValueError, IndexError):
						pass

				result["includes_subdomains"] = "includeSubDomains" in hsts_header
				result["preload"] = "preload" in hsts_header

				# Very long HSTS max-age could be abuse vector
				if result["max_age"] and result["max_age"] > 31536000:  # > 1 year
					result["suspicious"] = True

	except Exception as exc:
		logger.debug("hsts_check_failed domain=%s: %s", domain, exc)

	return result


def _check_favicon_supercookie(domain: str, timeout: int = 10) -> dict[str, Any]:
	"""Check for favicon-based supercookie tracking.

	Favicon ETags and cache behavior can be abused to track users
	across sites using favicon.ico as a persistent identifier.

	Args:
		domain: Domain to check
		timeout: HTTP request timeout

	Returns:
		Dict with favicon_found, etags, cache_behavior, suspicious
	"""
	result = {
		"favicon_found": False,
		"favicon_etags": [],
		"cache_directives": [],
		"suspicious": False,
	}

	try:
		with httpx.Client(timeout=timeout) as client:
			for favicon_path in _FAVICON_PATHS:
				favicon_url = _build_url(domain, favicon_path)

				try:
					resp = client.head(favicon_url, follow_redirects=True)

					if resp.status_code == 200:
						result["favicon_found"] = True

						# Collect ETags
						if "etag" in resp.headers:
							etag = resp.headers.get("etag", "")
							result["favicon_etags"].append(
								{
									"path": favicon_path,
									"etag": etag,
								}
							)

						# Check cache headers
						cache_control = resp.headers.get("cache-control", "")
						if cache_control and cache_control not in result["cache_directives"]:
							result["cache_directives"].append(cache_control)

				except Exception:
					pass

			# If favicon has ETags or unusual cache behavior, could be suspicious
			if result["favicon_etags"] and result["cache_directives"]:
				result["suspicious"] = True

	except Exception as exc:
		logger.debug("favicon_supercookie_check_failed domain=%s: %s", domain, exc)

	return result


def research_supercookie_check(
	domain: str,
	timeout: int = 30,
) -> dict[str, Any]:
	"""Check if a domain uses supercookie and covert tracking vectors.

	Supercookies bypass traditional cookie blocking using:
	- Favicon-based tracking (ETag + cache)
	- HSTS abuse
	- Cache-Control manipulation
	- Redirect tracking chains

	Args:
		domain: Domain to check (e.g., "example.com" or "https://example.com")
		timeout: HTTP request timeout in seconds (default 30, max 120)

	Returns:
		Dict with keys:
		- domain: Analyzed domain
		- success: Boolean indicating if analysis completed
		- favicon_supercookie: Favicon tracking detection
		- etag_tracking: ETag-based tracking detection
		- hsts_abuse: HSTS header abuse detection
		- cache_abuse: Cache-Control abuse detection
		- tracking_vectors: List of detected tracking methods
		- risk_level: String ("none", "low", "medium", "high")
		- recommendations: List of privacy recommendations
		- error: Error message if failed
	"""
	result: dict[str, Any] = {
		"domain": domain,
		"success": False,
		"favicon_supercookie": {},
		"etag_tracking": {},
		"hsts_abuse": {},
		"cache_abuse": {},
		"tracking_vectors": [],
		"risk_level": "none",
		"recommendations": [],
		"error": None,
	}

	# Validate domain
	if not _is_valid_domain(domain):
		result["error"] = "Invalid domain — must be valid domain name"
		return result

	# Validate URL if it includes a scheme
	if domain.startswith(("http://", "https://")):
		try:
			validate_url(domain)
		except UrlSafetyError as e:
			result["error"] = str(e)
			return result

	if timeout < 1 or timeout > 120:
		result["error"] = "timeout must be 1-120 seconds"
		return result

	try:
		logger.info("supercookie_check_start domain=%s", domain)

		# Check favicon supercookie
		result["favicon_supercookie"] = _check_favicon_supercookie(domain, timeout)

		# Check ETag tracking
		result["etag_tracking"] = _check_etag_tracking(domain, timeout)

		# Check HSTS abuse
		result["hsts_abuse"] = _check_hsts_supercookie(domain, timeout)

		# Check cache control abuse
		result["cache_abuse"] = _check_cache_control_abuse(domain, timeout)

		# Collect tracking vectors
		vectors = []

		if result["favicon_supercookie"].get("suspicious"):
			vectors.append("favicon_supercookie")

		if result["etag_tracking"].get("suspicious"):
			vectors.append("etag_tracking")

		if result["hsts_abuse"].get("suspicious"):
			vectors.append("hsts_abuse")

		if result["cache_abuse"].get("risk"):
			vectors.append("cache_control_abuse")

		result["tracking_vectors"] = vectors

		# Determine risk level
		if not vectors:
			result["risk_level"] = "none"
		elif len(vectors) == 1:
			result["risk_level"] = "low"
		elif len(vectors) <= 2:
			result["risk_level"] = "medium"
		else:
			result["risk_level"] = "high"

		# Generate recommendations
		recommendations = []

		if "favicon_supercookie" in vectors:
			recommendations.append(
				"Favicon supercookie detected. Disable favicon caching or use privacy extension."
			)

		if "etag_tracking" in vectors:
			recommendations.append(
				"ETag-based tracking detected. Clear cache regularly or use privacy mode."
			)

		if "hsts_abuse" in vectors:
			recommendations.append(
				"HSTS header abuse suspected. Review HSTS policy or use HSTS Preload exemption."
			)

		if "cache_control_abuse" in vectors:
			recommendations.append(
				"Cache-Control abuse detected. Use browser cache isolation features."
			)

		if not recommendations:
			recommendations.append("No supercookie vectors detected on this domain.")

		result["recommendations"] = recommendations
		result["success"] = True

		logger.info(
			"supercookie_check_complete domain=%s risk_level=%s vectors=%s",
			domain,
			result["risk_level"],
			len(vectors),
		)

	except Exception as exc:
		result["error"] = f"Check failed: {str(exc)}"
		logger.error(
			"supercookie_check_exception domain=%s: %s",
			domain,
			exc,
			exc_info=True,
		)

	return result
