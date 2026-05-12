"""P3 research tools — LLM comparison, data poisoning detection, Wikipedia correlation, and FOIA tracking."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any
from urllib.parse import quote

import httpx

from loom.http_helpers import fetch_json, fetch_text
from loom.validators import validate_url

logger = logging.getLogger("loom.tools.p3_tools")

# Default Wikipedia API endpoint
_WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
_HACKERNEWS_SEARCH = "https://hn.algolia.com/api/v1/search"
_FOIA_GOV = "https://www.foia.gov"
_MUCKROCK_SEARCH = "https://www.muckrock.com"

# ReDoS protection: max XML/RSS content size before regex parsing
_MAX_RSS_CONTENT_SIZE = 100000


def _extract_word_set(text: str) -> set[str]:
	"""Extract normalized word set from text."""
	words = re.findall(r"\b[a-z0-9]+\b", text.lower())
	# Filter out common stop words
	stop_words = {
		"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
		"of", "with", "by", "from", "as", "is", "are", "be", "been", "being",
		"have", "has", "had", "do", "does", "did", "will", "would", "could",
		"should", "may", "might", "must", "can", "i", "you", "he", "she", "it",
		"we", "they", "what", "which", "who", "when", "where", "why", "how"
	}
	return {w for w in words if len(w) > 2 and w not in stop_words}


async def research_model_comparator(
	prompt: str,
	endpoints: list[str],
) -> dict[str, Any]:
	"""Compare multiple LLM API endpoints side-by-side.

	Sends the same prompt to each endpoint via POST and compares:
	response length, response time, and word overlap.

	Args:
		prompt: Query/prompt text to send to each endpoint
		endpoints: List of LLM API endpoints (e.g., ["https://api.openai.com/...", ...])

	Returns:
		Dict with ``prompt``, ``comparisons`` (list of dicts with endpoint,
		response_preview, response_time_ms, word_count), ``fastest`` (endpoint),
		and ``most_verbose`` (endpoint).
	"""
	try:

		async def _run() -> dict[str, Any]:
			comparisons: list[dict[str, Any]] = []
			response_times: dict[str, float] = {}
			word_counts: dict[str, int] = {}
			responses: dict[str, str] = {}
			response_words: dict[str, set[str]] = {}

			async with httpx.AsyncClient(
				timeout=30.0,
				headers={"User-Agent": "Loom-Research/1.0"},
			) as client:
				tasks = []
				for endpoint in endpoints:
					endpoint = validate_url(endpoint)
					tasks.append(_send_prompt(client, endpoint, prompt, response_times, responses))

				await asyncio.gather(*tasks, return_exceptions=True)

				# Extract word sets for overlap analysis
				for endpoint, response in responses.items():
					response_words[endpoint] = _extract_word_set(response)
					word_counts[endpoint] = len(response.split())

				# Build comparisons
				for endpoint in endpoints:
					endpoint = validate_url(endpoint)
					if endpoint not in response_times:
						continue

					response = responses.get(endpoint, "")
					preview = response[:150].replace("\n", " ")
					if len(response) > 150:
						preview += "..."

					comparisons.append({
						"endpoint": endpoint,
						"response_preview": preview,
						"response_time_ms": int(response_times[endpoint] * 1000),
						"word_count": word_counts.get(endpoint, 0),
					})

				# Find fastest and most verbose
				fastest = min(response_times.items(), key=lambda x: x[1])[0] if response_times else ""
				most_verbose = max(word_counts.items(), key=lambda x: x[1])[0] if word_counts else ""

				# Calculate word overlap (Jaccard similarity: common words / union of all words)
				if response_words and len(response_words) > 1:
					word_sets = list(response_words.values())
					intersection = set.intersection(*word_sets) if word_sets else set()
					union = set()
					for words in word_sets:
						union.update(words)
					overlap_score = len(intersection) / len(union) if len(union) > 0 else 0.0
				else:
					overlap_score = 0.0

				return {
					"prompt": prompt,
					"endpoint_count": len(endpoints),
					"comparisons": comparisons,
					"fastest": fastest,
					"fastest_time_ms": int(response_times.get(fastest, 0) * 1000),
					"most_verbose": most_verbose,
					"most_verbose_words": word_counts.get(most_verbose, 0),
					"word_overlap_score": round(overlap_score, 2),
				}

		return await _run()
	except Exception as exc:
		logger.error("research_model_comparator failed: %s", exc)
		return {
			"error": str(exc),
			"tool": "research_model_comparator",
		}


async def _send_prompt(
	client: httpx.AsyncClient,
	endpoint: str,
	prompt: str,
	response_times: dict[str, float],
	responses: dict[str, str],
) -> None:
	"""Send prompt to endpoint and record response time and content."""
	try:
		start = time.time()
		resp = await client.post(
			endpoint,
			json={"prompt": prompt, "max_tokens": 100},
			timeout=25.0,
		)
		elapsed = time.time() - start
		if resp.status_code == 200:
			try:
				data = resp.json()
				# Handle different response formats
				text = ""
				if isinstance(data, dict):
					# Check for standard response fields first
					text = data.get("response") or data.get("text") or ""
					# If not found, check choices array with safety check
					if not text:
						choices = data.get("choices", [])
						if choices:
							text = choices[0].get("text", "")
				else:
					text = str(data)
				responses[endpoint] = text
				response_times[endpoint] = elapsed
			except Exception as exc:
				logger.debug("failed to parse response from %s: %s", endpoint, exc)
	except Exception as exc:
		logger.debug("endpoint request failed %s: %s", endpoint, exc)


async def research_data_poisoning(
	target_url: str,
	canary_phrases: list[str] | None = None,
) -> dict[str, Any]:
	"""Detect training data contamination via canary phrase responses.

	Sends known canary phrases (from Wikipedia, famous quotes) to target LLM
	and checks if model completes them differently from expected, indicating
	potential training data exposure.

	Args:
		target_url: Target LLM API endpoint (e.g., "https://api.example.com/chat")
		canary_phrases: List of known canary phrases. Defaults to Wikipedia
				   first sentences and famous quotes.

	Returns:
		Dict with ``target``, ``tests_run``, ``contamination_signals`` (list of
		detected anomalies), ``clean_rate`` (percentage of expected responses),
		and ``risk_level`` (low/medium/high).
	"""
	try:

		async def _run() -> dict[str, Any]:
			target_url_safe = validate_url(target_url)

			# Default canaries: Wikipedia first sentences
			if canary_phrases is None:
				canaries = [
					"Python is a high-level, interpreted programming language",
					"Machine learning is a subset of artificial intelligence",
					"The Internet is a global system of interconnected networks",
					"Cryptography is the practice and study of techniques",
					"Data science is an inter-disciplinary field",
					"The famous quote: To be or not to be",
					"Another quote: All that glitters is not gold",
				]
			else:
				canaries = canary_phrases

			contamination_signals: list[dict[str, Any]] = []
			tests_run = 0
			matches = 0

			async with httpx.AsyncClient(
				timeout=30.0,
				headers={"User-Agent": "Loom-Research/1.0"},
			) as client:
				for phrase in canaries:
					tests_run += 1
					try:
						start = time.time()
						resp = await client.post(
							target_url_safe,
							json={"prompt": phrase[:50], "max_tokens": 50},
							timeout=20.0,
						)
						elapsed = time.time() - start

						if resp.status_code == 200:
							try:
								data = resp.json()
								response_text = ""
								if isinstance(data, dict):
									response_text = data.get("response", data.get("text", ""))
								else:
									response_text = str(data)

								# Check if response completes the canary phrase
								if phrase.lower() in response_text.lower():
									matches += 1
									contamination_signals.append({
										"phrase": phrase[:80],
										"found_in_response": True,
										"response_time_ms": int(elapsed * 1000),
										"risk": "high",
									})
							except Exception as exc:
								logger.debug("failed to parse response: %s", exc)
					except Exception as exc:
						logger.debug("canary test failed: %s", exc)

			clean_rate = round(((tests_run - len(contamination_signals)) / tests_run * 100), 1) if tests_run > 0 else 100.0

			# Determine risk level
			contamination_ratio = len(contamination_signals) / tests_run if tests_run > 0 else 0
			if contamination_ratio > 0.5:
				risk_level = "high"
			elif contamination_ratio > 0.2:
				risk_level = "medium"
			else:
				risk_level = "low"

			return {
				"target": target_url_safe,
				"tests_run": tests_run,
				"contamination_signals": contamination_signals,
				"signals_detected": len(contamination_signals),
				"clean_rate": clean_rate,
				"risk_level": risk_level,
			}

		return await _run()
	except Exception as exc:
		logger.error("research_data_poisoning failed: %s", exc)
		return {
			"error": str(exc),
			"tool": "research_data_poisoning",
		}


async def research_wiki_event_correlator(
	page_title: str,
	days_back: int = 30,
) -> dict[str, Any]:
	"""Monitor Wikipedia edit patterns and correlate with news events.

	Fetches recent revisions from Wikipedia page, detects edit bursts,
	and correlates with Hacker News stories for real-time signal detection.

	Args:
		page_title: Wikipedia page title (e.g., "Artificial intelligence")
		days_back: Number of days of edit history to analyze (default 30)

	Returns:
		Dict with ``page``, ``edit_count``, ``edit_bursts`` (list of time windows
		with high activity), ``correlated_events`` (HN stories matching burst times),
		and ``activity_trend``.
	"""
	try:

		async def _run() -> dict[str, Any]:
			page_title_safe = page_title[:200]  # Limit length

			# Fetch Wikipedia revisions
			wiki_params = {
				"action": "query",
				"titles": page_title_safe,
				"prop": "revisions",
				"rvlimit": 100,
				"rvprop": "timestamp|user|size",
				"format": "json",
			}

			edits: list[dict[str, Any]] = []
			edit_bursts: list[dict[str, Any]] = []
			correlated_events: list[dict[str, Any]] = []

			async with httpx.AsyncClient(
				timeout=30.0,
				headers={"User-Agent": "Loom-Research/1.0"},
			) as client:
				wiki_data = await fetch_json(
					client,
					f"{_WIKIPEDIA_API}?{_build_query_string(wiki_params)}",
				)

				if wiki_data and "query" in wiki_data:
					pages = wiki_data["query"].get("pages", {})
					for page_id, page_data in pages.items():
						revisions = page_data.get("revisions", [])
						for rev in revisions[:100]:
							timestamp = rev.get("timestamp", "")
							size = rev.get("size", 0)
							edits.append({
								"timestamp": timestamp,
								"size": size,
								"user": rev.get("user", "unknown"),
							})

				# Detect edit bursts (5+ edits in 1 hour window)
				if edits:
					for i in range(len(edits) - 4):
						window_edits = edits[i:i+5]
						# Assuming edits are time-sorted
						if window_edits:
							first_time = window_edits[0].get("timestamp", "")
							burst_size = sum(e.get("size", 0) for e in window_edits)
							edit_bursts.append({
								"time": first_time,
								"edits_in_window": len(window_edits),
								"total_size_changed": burst_size,
							})

				# Correlate with Hacker News
				hn_search_query = quote(page_title_safe[:50])
				hn_data = await fetch_json(
					client,
					f"{_HACKERNEWS_SEARCH}?query={hn_search_query}&hitsPerPage=20",
				)

				if hn_data and "hits" in hn_data:
					for hit in hn_data.get("hits", [])[:10]:
						correlated_events.append({
							"title": hit.get("title", "")[:100],
							"url": hit.get("url", "")[:200],
							"points": hit.get("points", 0),
							"date": hit.get("created_at", ""),
						})

				# Calculate trend
				activity_trend = "stable"
				if len(edits) > 10:
					recent = edits[:5]
					older = edits[-5:]
					recent_size = sum(e.get("size", 0) for e in recent)
					older_size = sum(e.get("size", 0) for e in older)
					if recent_size > older_size * 1.5:
						activity_trend = "increasing"
					elif recent_size < older_size * 0.7:
						activity_trend = "decreasing"

				return {
					"page": page_title_safe,
					"edit_count": len(edits),
					"edits_analyzed": min(len(edits), 100),
					"edit_bursts": edit_bursts[:20],
					"burst_count": len(edit_bursts),
					"correlated_events": correlated_events,
					"activity_trend": activity_trend,
					"days_analyzed": days_back,
				}

		return await _run()
	except Exception as exc:
		logger.error("research_wiki_event_correlator failed: %s", exc)
		return {
			"error": str(exc),
			"tool": "research_wiki_event_correlator",
		}


def _build_query_string(params: dict[str, Any]) -> str:
	"""Build URL query string from dict."""
	return "&".join(f"{k}={v}" for k, v in params.items())


async def research_foia_tracker(
	query: str,
) -> dict[str, Any]:
	"""Track FOIA requests and documents across multiple sources.

	Searches for FOIA-related documents via:
	- Google Dork (site:foia.gov OR site:muckrock.com)
	- Government RSS feeds
	- MuckRock API (if available)

	Args:
		query: FOIA search query (e.g., "surveillance", "AI policy")

	Returns:
		Dict with ``query``, ``documents_found`` (list of {source, title, url, date}),
		``total`` count, ``sources`` breakdown, and ``latest_date``.
	"""
	try:

		async def _run() -> dict[str, Any]:
			query_safe = query[:100]
			documents: list[dict[str, Any]] = []
			sources_breakdown: dict[str, int] = {}

			async with httpx.AsyncClient(
				timeout=30.0,
				headers={"User-Agent": "Loom-Research/1.0"},
			) as client:
				# Search MuckRock
				muckrock_docs = await _search_muckrock(client, query_safe)
				documents.extend(muckrock_docs)
				sources_breakdown["muckrock"] = len(muckrock_docs)

				# Search FOIA.gov via Google Dork simulation
				foia_dork = await _search_foia_dork(client, query_safe)
				documents.extend(foia_dork)
				sources_breakdown["foia.gov"] = len(foia_dork)

				# Check government RSS feeds
				rss_docs = await _search_govt_rss(client, query_safe)
				documents.extend(rss_docs)
				sources_breakdown["rss_feeds"] = len(rss_docs)

			# Sort by date and deduplicate
			seen_urls = set()
			deduped: list[dict[str, Any]] = []
			for doc in sorted(documents, key=lambda x: x.get("date", ""), reverse=True):
				url = doc.get("url", "")
				if url not in seen_urls:
					seen_urls.add(url)
					deduped.append(doc)

			latest_date = deduped[0].get("date", "") if deduped else ""

			return {
				"query": query_safe,
				"documents_found": deduped[:50],
				"total": len(deduped),
				"sources": sources_breakdown,
				"latest_date": latest_date,
			}

		return await _run()
	except Exception as exc:
		logger.error("research_foia_tracker failed: %s", exc)
		return {
			"error": str(exc),
			"tool": "research_foia_tracker",
		}


async def _search_muckrock(
	client: httpx.AsyncClient,
	query: str,
) -> list[dict[str, Any]]:
	"""Search MuckRock for FOIA documents."""
	documents: list[dict[str, Any]] = []
	try:
		search_url = f"{_MUCKROCK_SEARCH}/search/?q={quote(query)}&type=foia"
		html = await fetch_text(client, search_url)
		# Parse HTML to extract links (simplified)
		if html:
			# Extract document links with basic regex
			doc_links = re.findall(r'href="(/document/[^"]+)"', html)
			for link in doc_links[:10]:
				doc_url = f"{_MUCKROCK_SEARCH}{link}"
				documents.append({
					"source": "muckrock",
					"title": link.split("/")[-1][:100],
					"url": doc_url,
					"date": "",
				})
	except Exception as exc:
		logger.debug("muckrock search failed: %s", exc)
	return documents


async def _search_foia_dork(
	client: httpx.AsyncClient,
	query: str,
) -> list[dict[str, Any]]:
	"""Simulate FOIA.gov search via dork."""
	documents: list[dict[str, Any]] = []
	try:
		search_url = f"{_FOIA_GOV}/api/search/?q={quote(query)}"
		data = await fetch_json(client, search_url)
		if data and isinstance(data, dict):
			results = data.get("results", [])
			for result in results[:10]:
				documents.append({
					"source": "foia.gov",
					"title": result.get("title", "")[:100],
					"url": result.get("url", "")[:200],
					"date": result.get("date", ""),
				})
	except Exception as exc:
		logger.debug("foia.gov search failed: %s", exc)
	return documents


async def _search_govt_rss(
	client: httpx.AsyncClient,
	query: str,
) -> list[dict[str, Any]]:
	"""Search common government RSS feeds."""
	documents: list[dict[str, Any]] = []
	feeds = [
		"https://whitehouse.gov/feed/",
		"https://justice.gov/rss.xml",
		"https://state.gov/rss.xml",
	]

	for feed_url in feeds:
		try:
			feed_content = await fetch_text(client, feed_url)
			# Truncate content to prevent ReDoS on large feeds
			if len(feed_content) > _MAX_RSS_CONTENT_SIZE:
				feed_content = feed_content[:_MAX_RSS_CONTENT_SIZE]
			# Extract item titles and links with regex
			items = re.findall(r"<item>.*?<title>([^<]+)</title>.*?<link>([^<]+)</link>.*?</item>", feed_content, re.DOTALL)
			for title, link in items:
				if query.lower() in title.lower():
					documents.append({
						"source": "govt_rss",
						"title": title[:100],
						"url": link[:200],
						"date": "",
					})
		except Exception as exc:
			logger.debug("rss feed parse failed %s: %s", feed_url, exc)

	return documents
