"""Deep metadata forensics — extract hidden metadata from web pages, images, and documents."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import urljoin

import httpx

from loom.http_helpers import fetch_text
from loom.error_responses import handle_tool_errors
from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.metadata_forensics")


async def _fetch_bytes(
	client: httpx.AsyncClient, url: str, max_bytes: int = 5_000_000
) -> bytes:
	try:
		resp = await client.get(url, timeout=30.0, follow_redirects=True)
		if resp.status_code == 200:
			return resp.content[:max_bytes]
		return b""
	except httpx.HTTPError as exc:
		logger.debug("metadata_forensics fetch failed: %s", exc)
		return b""
	except Exception as exc:
		logger.error("metadata_forensics unexpected fetch error: %s", exc)
		return b""


def _extract_json_ld(html: str) -> list[dict[str, Any]]:
	results: list[dict[str, Any]] = []
	import json

	for match in re.finditer(
		r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
		html,
		re.DOTALL | re.IGNORECASE,
	):
		try:
			data = json.loads(match.group(1))
			if isinstance(data, list):
				results.extend(data)
			else:
				results.append(data)
		except (json.JSONDecodeError, ValueError):
			pass
	return results


def _extract_open_graph(html: str) -> dict[str, str]:
	og: dict[str, str] = {}
	for match in re.finditer(
		r'<meta\s+[^>]*property\s*=\s*["\']og:([^"\']+)["\'][^>]*content\s*=\s*["\']([^"\']*)["\']',
		html,
		re.IGNORECASE,
	):
		og[match.group(1)] = match.group(2)
	for match in re.finditer(
		r'<meta\s+[^>]*content\s*=\s*["\']([^"\']*)["\'][^>]*property\s*=\s*["\']og:([^"\']+)["\']',
		html,
		re.IGNORECASE,
	):
		og[match.group(2)] = match.group(1)
	return og


def _extract_twitter_cards(html: str) -> dict[str, str]:
	tc: dict[str, str] = {}
	for match in re.finditer(
		r'<meta\s+[^>]*name\s*=\s*["\']twitter:([^"\']+)["\'][^>]*content\s*=\s*["\']([^"\']*)["\']',
		html,
		re.IGNORECASE,
	):
		tc[match.group(1)] = match.group(2)
	return tc


def _extract_meta_tags(html: str) -> dict[str, str]:
	meta: dict[str, str] = {}
	for match in re.finditer(
		r'<meta\s+[^>]*name\s*=\s*["\']([^"\']+)["\'][^>]*content\s*=\s*["\']([^"\']*)["\']',
		html,
		re.IGNORECASE,
	):
		name = match.group(1).lower()
		if name not in ("viewport", "charset"):
			meta[name] = match.group(2)
	return meta


def _extract_link_relations(html: str) -> list[dict[str, str]]:
	links: list[dict[str, str]] = []
	for match in re.finditer(
		r'<link\s+[^>]*rel\s*=\s*["\']([^"\']+)["\'][^>]*href\s*=\s*["\']([^"\']+)["\']',
		html,
		re.IGNORECASE,
	):
		links.append({"rel": match.group(1), "href": match.group(2)})
	return links


def _extract_feeds(html: str, base_url: str) -> list[dict[str, str]]:
	feeds: list[dict[str, str]] = []
	for match in re.finditer(
		r'<link\s+[^>]*type\s*=\s*["\']application/(?:rss|atom)\+xml["\'][^>]*href\s*=\s*["\']([^"\']+)["\']',
		html,
		re.IGNORECASE,
	):
		feeds.append({"type": "rss/atom", "url": urljoin(base_url, match.group(1))})
	return feeds


def _extract_image_urls(html: str, base_url: str) -> list[str]:
	urls: list[str] = []
	for match in re.finditer(r'<img[^>]+src\s*=\s*["\']([^"\']+)["\']', html):
		img_url = urljoin(base_url, match.group(1))
		try:
			validate_url(img_url)
			urls.append(img_url)
		except UrlSafetyError as exc:
			logger.debug("image URL failed validation: %s: %s", img_url, exc)
	return urls[:10]


def _extract_exif(image_bytes: bytes) -> dict[str, Any]:
	"""Extract EXIF data from image bytes (blocking I/O)."""
	try:
		import io

		from PIL import Image
		from PIL.ExifTags import TAGS

		img = Image.open(io.BytesIO(image_bytes))
		exif_data = img.getexif()
		if not exif_data:
			return {}
		result: dict[str, Any] = {}
		for tag_id, value in exif_data.items():
			tag = TAGS.get(tag_id, str(tag_id))
			try:
				if isinstance(value, bytes):
					value = value.decode("utf-8", errors="replace")[:100]
				else:
					value = str(value)[:200]
				result[tag] = value
			except Exception as e:
				logger.debug("exif_value_parse_error: %s", e)
		return result
	except ImportError:
		return {"error": "Pillow not installed"}
	except Exception as exc:
		return {"error": str(exc)}


@handle_tool_errors("research_metadata_forensics")
async def research_metadata_forensics(
	url: str,
	extract_exif: bool = True,
	max_images: int = 3,
) -> dict[str, Any]:
	"""Extract all hidden metadata from a web page and its resources.

	Parses JSON-LD structured data, Open Graph tags, Twitter Cards,
	meta tags, link relations, RSS/Atom feeds, and optionally extracts
	EXIF data from images found on the page.

	Args:
		url: the page URL to analyze
		extract_exif: download images and extract EXIF metadata
		max_images: max images to download for EXIF analysis

	Returns:
		Dict with ``json_ld``, ``open_graph``, ``twitter_cards``,
		``meta_tags``, ``link_relations``, ``feeds``, ``image_exif``,
		and ``generator`` (CMS/framework detection from meta generator tag).
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
					return {"url": url, "error": "failed to fetch page"}

				json_ld = _extract_json_ld(html)
				open_graph = _extract_open_graph(html)
				twitter_cards = _extract_twitter_cards(html)
				meta_tags = _extract_meta_tags(html)
				link_relations = _extract_link_relations(html)
				feeds = _extract_feeds(html, url)

				generator = meta_tags.get("generator", "")

				image_exif: list[dict[str, Any]] = []
				if extract_exif:
					image_urls = _extract_image_urls(html, url)[:max_images]
					image_data = await asyncio.gather(
						*[_fetch_bytes(client, img_url) for img_url in image_urls],
						return_exceptions=True,
					)
					for img_url, data in zip(
						image_urls, image_data, strict=False
					):
						if isinstance(data, bytes) and len(data) > 100:
							# Run blocking EXIF extraction in executor
							exif = await asyncio.to_thread(_extract_exif, data)
							if exif:
								image_exif.append({"url": img_url, "exif": exif})

				return {
					"url": url,
					"json_ld": json_ld,
					"open_graph": open_graph,
					"twitter_cards": twitter_cards,
					"meta_tags": meta_tags,
					"link_relations": link_relations[:20],
					"feeds": feeds,
					"generator": generator,
					"image_exif": image_exif,
					"structured_data_found": bool(json_ld or open_graph),
				}

		return await _run()
	except UrlSafetyError as exc:
		logger.warning("research_metadata_forensics URL validation failed: %s", exc)
		return {
			"error": f"invalid url: {exc}",
			"tool": "research_metadata_forensics",
		}
	except Exception as exc:
		logger.error("research_metadata_forensics failed: %s", exc)
		return {
			"error": "failed to extract metadata",
			"tool": "research_metadata_forensics",
		}
