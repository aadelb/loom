"""Onion Spectra — Classify .onion site content by language and safety category.

Tool:
- research_onion_spectra: .onion page classification, language detection, safety categorization
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any
from urllib.parse import urlparse

from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.onion_spectra")

# Safety categories for .onion content
_SAFETY_CATEGORIES = [
	"benign",  # harmless content (blogs, forums, etc.)
	"suspicious",  # potentially problematic but not clearly illegal
	"harmful",  # content promoting harm/violence/exploitation
	"illegal",  # clearly illegal content (drugs, weapons, stolen goods, etc.)
]

# Common language codes for detection
_LANGUAGE_MAP = {
	"en": "English",
	"es": "Spanish",
	"fr": "French",
	"de": "German",
	"ru": "Russian",
	"zh": "Chinese",
	"ar": "Arabic",
	"ja": "Japanese",
	"pt": "Portuguese",
	"it": "Italian",
}

# Optional imports (for mocking in tests)
research_fetch = None
research_llm_classify = None

try:
	from loom.tools.fetch import research_fetch
except ImportError:
	pass

try:
	from loom.tools.llm import research_llm_classify
except ImportError:
	pass


async def _detect_language(text: str) -> dict[str, Any]:
	"""Detect language of text using LLM or simple heuristics.

	Args:
		text: content to analyze

	Returns:
		Dict with language_code and language_name
	"""
	# First try simple heuristic based on character sets
	if any("一" <= c <= "鿿" for c in text):
		return {"language_code": "zh", "language_name": "Chinese", "confidence": 0.7}
	if any("؀" <= c <= "ۿ" for c in text):
		return {"language_code": "ar", "language_name": "Arabic", "confidence": 0.7}
	if any("Ѐ" <= c <= "ӿ" for c in text):
		return {"language_code": "ru", "language_name": "Russian", "confidence": 0.7}

	# Use LLM to detect language (fallback to English if unavailable)
	if research_llm_classify is None:
		return {"language_code": "en", "language_name": "English", "confidence": 0.5}

	try:
		result = await research_llm_classify(
			text=text[:2000],  # First 2000 chars only
			labels=list(_LANGUAGE_MAP.keys()),
		)

		lang_code = result.get("classification", {}).get("label", "en")
		return {
			"language_code": lang_code,
			"language_name": _LANGUAGE_MAP.get(lang_code, "Unknown"),
			"confidence": result.get("classification", {}).get("confidence", 0.5),
		}
	except Exception as exc:
		logger.debug("language_detection_failed: %s", exc)
		return {"language_code": "en", "language_name": "English", "confidence": 0.5}


async def _classify_safety(
	title: str,
	content: str,
) -> dict[str, Any]:
	"""Classify .onion site content into safety categories.

	Args:
		title: page title
		content: page content (first 2000 chars)

	Returns:
		Dict with category, confidence, and reasoning
	"""
	if research_llm_classify is None:
		return {
			"category": "suspicious",
			"confidence": 0.5,
			"reasoning": "LLM unavailable",
		}

	categories_str = ", ".join(_SAFETY_CATEGORIES)
	prompt = (
		f"Classify this .onion website into one of these safety categories: "
		f"{categories_str}.\n\n"
		f"Title: {title}\n"
		f"Content: {content[:1000]}\n\n"
		f"Focus on the primary purpose and content type, not just presence on dark web.\n"
		f"Return classification label only."
	)

	try:
		result = await research_llm_classify(
			text=prompt,
			labels=_SAFETY_CATEGORIES,
		)

		category = result.get("classification", {}).get("label", "suspicious")
		confidence = result.get("classification", {}).get("confidence", 0.5)

		return {
			"category": category,
			"confidence": round(confidence, 2),
			"reasoning": _get_reasoning(category, title, content),
		}
	except Exception as exc:
		logger.debug("safety_classification_failed: %s", exc)
		return {
			"category": "suspicious",
			"confidence": 0.5,
			"reasoning": f"Classification failed: {str(exc)[:100]}",
		}


def _get_reasoning(category: str, title: str, content: str) -> str:
	"""Generate a brief reasoning for the safety classification.

	Args:
		category: safety category assigned
		title: page title
		content: page content sample

	Returns:
		Brief explanation string
	"""
	reasons: dict[str, str] = {
		"benign": f"Content appears to be informational/community-focused (title: {title[:50]})",
		"suspicious": "Content has ambiguous purpose, may require further review",
		"harmful": "Content includes references to harm, violence, or exploitation",
		"illegal": "Content appears to facilitate illegal activities (drugs, weapons, fraud, etc.)",
	}
	return reasons.get(category, "Unable to determine safety category")


def _is_onion_url(url: str) -> bool:
	"""Check if URL is a valid .onion address."""
	try:
		parsed = urlparse(url)
		return bool(parsed.hostname and parsed.hostname.endswith(".onion"))
	except Exception:
		return False


async def research_onion_spectra(
	url: str,
	fetch_content: bool = True,
	max_chars: int = 5000,
) -> dict[str, Any]:
	"""Classify .onion site content by language and safety category.

	Fetches content from a .onion URL (via Tor proxy from config), detects
	language, and classifies content into safety categories:
	- benign: harmless content (blogs, forums, privacy-focused services)
	- suspicious: potentially problematic content requiring further review
	- harmful: content promoting harm/violence/exploitation
	- illegal: clearly illegal content (drugs, weapons, stolen goods, etc.)

	Args:
		url: .onion URL to analyze
		fetch_content: whether to fetch and analyze page content (default True)
		max_chars: maximum characters to fetch for analysis

	Returns:
		Dict with:
		- url: analyzed URL
		- language: {code, name, confidence}
		- category: safety classification
		- confidence: classification confidence score
		- summary: brief description
		- error: error message if any
	"""
	validate_url(url)

	# Validate URL is a .onion address
	if not _is_onion_url(url):
		return {
			"url": url,
			"error": "URL must be a .onion address",
			"language": {},
			"category": "suspicious",
			"confidence": 0.0,
			"summary": "",
		}

	validated_url = url

	# Fetch page content
	title = ""
	content = ""

	if fetch_content and research_fetch is not None:
		try:
			# Use asyncio to run blocking fetch in executor
			loop = asyncio.get_event_loop()
			fetch_result = await loop.run_in_executor(
				None,
				partial(
					research_fetch,
					url=validated_url,
					mode="stealthy",  # Use stealthy mode for .onion
					max_chars=max_chars,
					timeout=30,
				),
			)

			content = fetch_result.get("content", "")[:max_chars]
			title = fetch_result.get("title", "")

			if not content:
				logger.warning("onion_spectra_empty_content url=%s", validated_url)
				content = fetch_result.get("html", "")[:max_chars]

		except Exception as exc:
			logger.warning("onion_spectra_fetch_failed url=%s error=%s", validated_url, exc)
			return {
				"url": validated_url,
				"error": f"Failed to fetch page: {str(exc)[:100]}",
				"language": {},
				"category": "suspicious",
				"confidence": 0.5,
				"summary": "Unable to analyze page content",
			}

	# Detect language
	language_result = await _detect_language(content or title)

	# Classify safety
	safety_result = await _classify_safety(title, content)

	# Generate summary
	lang_name = language_result.get("language_name", "Unknown")
	category = safety_result.get("category", "suspicious")
	confidence = safety_result.get("confidence", 0.5)

	summary = (
		f".onion site in {lang_name} classified as '{category}' "
		f"(confidence: {confidence})"
	)

	logger.info(
		"onion_spectra_complete url=%s category=%s language=%s",
		validated_url[:50],
		category,
		language_result.get("language_code"),
	)

	return {
		"url": validated_url,
		"language": {
			"code": language_result.get("language_code"),
			"name": language_result.get("language_name"),
			"confidence": language_result.get("confidence"),
		},
		"category": category,
		"confidence": confidence,
		"reasoning": safety_result.get("reasoning", ""),
		"summary": summary,
		"title": title[:100] if title else "",
		"content_preview": content[:200] if content else "",
	}
