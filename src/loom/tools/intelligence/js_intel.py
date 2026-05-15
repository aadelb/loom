"""JavaScript intelligence extraction — find API keys, endpoints, secrets in JS bundles."""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import asyncio
import logging
import re
from typing import Any
from urllib.parse import urljoin

import httpx

from loom.http_helpers import fetch_text
from loom.validators import validate_url

logger = logging.getLogger("loom.tools.js_intel")

_SECRET_PATTERNS: list[tuple[str, str]] = [
	("aws_access_key", r"AKIA[A-Z0-9]{16}"),
	("openai_key", r"sk-[a-zA-Z0-9-]{10,}"),
	("github_token", r"ghp_[a-zA-Z0-9]{32,}"),
	("github_oauth", r"gho_[a-zA-Z0-9]{36}"),
	("stripe_key", r"sk_live_[a-zA-Z0-9]{24,}"),
	("stripe_publishable", r"pk_live_[a-zA-Z0-9]{24,}"),
	("slack_token", r"xox[bporas]-[a-zA-Z0-9-]{10,}"),
	("google_api", r"AIzaSy[a-zA-Z0-9_-]{33}"),
	("firebase_key", r"AAAA[a-zA-Z0-9_-]{7}:[a-zA-Z0-9_-]{140}"),
	("bearer_token", r"""[\"']Bearer\s+[a-zA-Z0-9._~+/=-]{20,}[\"']"""),
	("jwt_token", r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),
	("private_key", r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
	("anthropic_key", r"sk-ant-[a-zA-Z0-9-]{20,}"),
	("sendgrid_key", r"SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}"),
	("twilio_sid", r"AC[a-f0-9]{32}"),
]

_ENDPOINT_PATTERNS: list[tuple[str, str]] = [
	("fetch_url", r"""fetch\s*\(\s*[\"'`]([^\"'`]+/api/[^\"'`]+)[\"'`]"""),
	("axios_url", r"""axios\.\w+\s*\(\s*[\"'`]([^\"'`]+/api/[^\"'`]+)[\"'`]"""),
	("api_path", r"""[\"'`](/api/v\d+/[a-zA-Z0-9/_-]+)[\"'`]"""),
	("graphql_endpoint", r"""[\"'`]((?:https?://)?[^\"'`]*/graphql)[\"'`]"""),
	("websocket_url", r"""[\"'`](wss?://[^\"'`]+)[\"'`]"""),
	("internal_url", r"""[\"'`](https?://(?:staging|dev|internal|test|api)\.[^\"'`]+)[\"'`]"""),
]

_FEATURE_FLAG_PATTERNS: list[str] = [
	r"""[\"'](?:feature[_-]?flag|experiment|variant|toggle|feature[_-]?gate)[\"']\s*:\s*[\"']([^\"']+)[\"']""",
	r"""(?:isEnabled|isFeatureOn|hasFeature)\s*\(\s*[\"']([^\"']+)[\"']""",
]

_ENV_VAR_PATTERNS: list[str] = [
	r"""process\.env\.([A-Z_][A-Z0-9_]+)""",
	r"""import\.meta\.env\.([A-Z_][A-Z0-9_]+)""",
]


def _extract_js_urls(html: str, base_url: str) -> list[str]:
	js_urls: list[str] = []
	for match in re.findall(r"""<script[^>]+src\s*=\s*[\"']([^\"']+)[\"']""", html):
		full_url = urljoin(base_url, match)
		if full_url.endswith(".js") or ".js?" in full_url:
			js_urls.append(full_url)
	return js_urls


def _scan_for_secrets(content: str) -> list[dict[str, str]]:
	found: list[dict[str, str]] = []
	for name, pattern in _SECRET_PATTERNS:
		for match in re.finditer(pattern, content):
			value = match.group(0)[:80]
			found.append({"type": name, "value": value, "risk": "HIGH"})
	return found


def _scan_for_endpoints(content: str) -> list[dict[str, str]]:
	found: list[dict[str, str]] = []
	seen: set[str] = set()
	for name, pattern in _ENDPOINT_PATTERNS:
		for match in re.finditer(pattern, content):
			endpoint = match.group(1)
			if endpoint not in seen:
				seen.add(endpoint)
				found.append({"type": name, "endpoint": endpoint})
	return found


def _scan_for_feature_flags(content: str) -> list[str]:
	flags: set[str] = set()
	for pattern in _FEATURE_FLAG_PATTERNS:
		for match in re.finditer(pattern, content, re.IGNORECASE):
			flags.add(match.group(1))
	return list(flags)


def _scan_for_env_vars(content: str) -> list[str]:
	env_vars: set[str] = set()
	for pattern in _ENV_VAR_PATTERNS:
		for match in re.finditer(pattern, content):
			env_vars.add(match.group(1))
	return list(env_vars)


@handle_tool_errors("research_js_intel")
async def research_js_intel(
	url: str,
	max_js_files: int = 20,
	check_source_maps: bool = True,
) -> dict[str, Any]:
	"""Extract intelligence from JavaScript bundles on a web page.

	Downloads all JS files referenced by the page, then scans for:
	API keys and secrets, internal API endpoints, feature flags,
	environment variables, GraphQL endpoints, WebSocket URLs,
	and staging/development URLs.

	Args:
		url: the page URL to analyze
		max_js_files: maximum number of JS files to download and scan
		check_source_maps: also check for .map source map files

	Returns:
		Dict with ``js_files_found``, ``source_maps_found``,
		``secrets``, ``endpoints``, ``feature_flags``, ``env_vars``,
		``graphql_endpoints``, ``websocket_urls``.
	"""
	try:
		validate_url(url)

		async def _run() -> dict[str, Any]:
			async with httpx.AsyncClient(
				follow_redirects=True,
				headers={"User-Agent": "Loom-Research/1.0"},
				timeout=30.0,
			) as client:
				html = await fetch_text(client, url, timeout=20.0)
				if not html:
					return {"url": url, "error": "failed to fetch page", "js_files_found": 0}

				js_urls = _extract_js_urls(html, url)[:max_js_files]

				all_secrets: list[dict[str, str]] = []
				all_endpoints: list[dict[str, str]] = []
				all_flags: list[str] = []
				all_env_vars: list[str] = []
				source_maps_found = 0

				html_secrets = _scan_for_secrets(html)
				html_endpoints = _scan_for_endpoints(html)
				all_secrets.extend(html_secrets)
				all_endpoints.extend(html_endpoints)

				js_contents = await asyncio.gather(
					*[fetch_text(client, js_url, timeout=20.0) for js_url in js_urls],
					return_exceptions=True,
				)

				for _js_url, content in zip(js_urls, js_contents, strict=False):
					if isinstance(content, str) and content:
						all_secrets.extend(_scan_for_secrets(content))
						all_endpoints.extend(_scan_for_endpoints(content))
						all_flags.extend(_scan_for_feature_flags(content))
						all_env_vars.extend(_scan_for_env_vars(content))

				if check_source_maps:
					map_urls = [f"{js_url}.map" for js_url in js_urls]
					map_checks = await asyncio.gather(
						*[fetch_text(client, m, timeout=20.0) for m in map_urls],
						return_exceptions=True,
					)
					for _map_url, content in zip(map_urls, map_checks, strict=False):
						if isinstance(content, str) and content and content.startswith("{"):
							source_maps_found += 1
							all_secrets.extend(_scan_for_secrets(content))
							all_endpoints.extend(_scan_for_endpoints(content))

				seen_secrets: set[str] = set()
				unique_secrets: list[dict[str, str]] = []
				for s in all_secrets:
					key = f"{s['type']}:{s['value']}"
					if key not in seen_secrets:
						seen_secrets.add(key)
						unique_secrets.append(s)

				seen_endpoints: set[str] = set()
				unique_endpoints: list[dict[str, str]] = []
				for e in all_endpoints:
					if e["endpoint"] not in seen_endpoints:
						seen_endpoints.add(e["endpoint"])
						unique_endpoints.append(e)

				return {
					"url": url,
					"js_files_found": len(js_urls),
					"source_maps_found": source_maps_found,
					"secrets": unique_secrets,
					"endpoints": unique_endpoints,
					"feature_flags": list(set(all_flags)),
					"env_vars": list(set(all_env_vars)),
				}

		return await _run()
	except Exception as exc:
		return {"error": str(exc), "tool": "research_js_intel"}
