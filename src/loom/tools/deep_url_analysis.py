"""Deep URL Analysis — fetch N URLs on a topic, analyze with Gemini 1M context.

Forces finding, fetching, and analysis of multiple URLs related to a research
topic, then passes all content to a long-context model (Gemini 3.1 Pro, 1M tokens)
for comprehensive synthesis.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
from typing import Any

logger = logging.getLogger("loom.tools.deep_url_analysis")


_FREE_PROVIDERS = ["ddgs", "arxiv", "wikipedia", "hn_reddit"]
_PAID_PROVIDERS = ["exa", "tavily", "brave", "firecrawl"]
_ALL_PROVIDERS = _FREE_PROVIDERS + _PAID_PROVIDERS


async def research_deep_url_analysis(
    topic: str,
    num_urls: int = 10,
    search_provider: str = "exa",
    analysis_prompt: str = "",
    max_chars_per_url: int = 50000,
    use_free_only: bool = False,
    model: str = "gemini-3.1-pro-preview",
) -> dict[str, Any]:
    """Force-find, fetch, and analyze multiple URLs with Gemini 1M context.

    Pipeline:
    1. Search for relevant URLs on the topic
    2. Fetch full content from each URL (stealthy mode with escalation)
    3. Convert to clean markdown
    4. Concatenate all content
    5. Send to long-context model (Gemini 3.1 Pro 1M) for deep analysis

    Args:
        topic: Research topic to find URLs about
        num_urls: Number of URLs to find and fetch (1-100, default 10)
        search_provider: Search engine to use. Options:
            FREE: ddgs, arxiv, wikipedia, hn_reddit
            PAID: exa, tavily, brave, firecrawl
            Use "multi" to search across multiple providers
        analysis_prompt: Custom analysis instructions for Gemini (optional)
        max_chars_per_url: Max characters to extract per URL (default 50K)
        use_free_only: If True, only use free search providers (ddgs, arxiv, wikipedia)
        model: Gemini model to use (default: gemini-3.1-pro-preview with 1M context)

    Returns:
        Dict with:
        - topic: Original topic
        - urls_found: Number of URLs discovered
        - urls_fetched: Number successfully fetched
        - total_content_chars: Total content size sent to Gemini
        - gemini_analysis: Full Gemini response
        - sources: List of {url, title, chars_extracted}
        - errors: List of {url, error} for failed fetches
    """
    from loom.tools.search import research_search
    from loom.tools.markdown import research_markdown

    if not topic or len(topic.strip()) < 3:
        return {"error": "Topic too short (min 3 chars)", "topic": topic}

    num_urls = max(1, min(num_urls, 100))
    max_chars_per_url = max(5000, min(max_chars_per_url, 200000))

    # Provider selection
    if use_free_only:
        search_provider = "ddgs"
    if search_provider == "multi":
        providers_to_use = _FREE_PROVIDERS if use_free_only else _ALL_PROVIDERS
    else:
        providers_to_use = [search_provider]

    # Stage 1: Find relevant URLs (multi-provider if requested)
    logger.info("deep_url_analysis stage=search topic=%s num_urls=%d providers=%s", topic[:100], num_urls, providers_to_use)

    urls = []
    seen_urls: set[str] = set()

    for provider in providers_to_use:
        if len(urls) >= num_urls:
            break
        try:
            search_result = await research_search(
                query=topic,
                provider=provider,
                n=min(num_urls * 2, 50),
            )
            if isinstance(search_result, dict) and "results" in search_result:
                for r in search_result["results"]:
                    if isinstance(r, dict) and r.get("url") and r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        urls.append({"url": r["url"], "title": r.get("title", ""), "provider": provider})
        except Exception as e:
            logger.warning("deep_url_analysis search_error provider=%s error=%s", provider, str(e)[:100])

    urls = urls[:num_urls]

    if not urls:
        return {
            "error": "No URLs found for topic",
            "topic": topic,
            "search_provider": search_provider,
            "urls_found": 0,
        }

    logger.info("deep_url_analysis stage=fetch urls_found=%d", len(urls))

    # Stage 2: Fetch and convert to markdown (parallel, with semaphore)
    sem = asyncio.Semaphore(5)
    sources: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    async def _fetch_one(url_info: dict[str, str]) -> dict[str, Any] | None:
        async with sem:
            try:
                result = await research_markdown(
                    url=url_info["url"],
                    timeout=30,
                )
                if isinstance(result, dict) and result.get("markdown"):
                    content = result["markdown"][:max_chars_per_url]
                    return {
                        "content": content,
                        "url": url_info["url"],
                        "title": url_info.get("title", ""),
                        "chars_extracted": len(content),
                    }
                elif isinstance(result, dict) and result.get("error"):
                    errors.append({"url": url_info["url"], "error": result["error"]})
                    return None
            except Exception as e:
                errors.append({"url": url_info["url"], "error": str(e)[:200]})
                return None
        return None

    tasks = [_fetch_one(u) for u in urls]
    results = await asyncio.gather(*tasks)
    fetched = [r for r in results if r]

    if not fetched:
        return {
            "error": "Failed to fetch any URLs",
            "topic": topic,
            "urls_found": len(urls),
            "urls_fetched": 0,
            "errors": errors,
        }

    sources = [{"url": f["url"], "title": f["title"], "chars_extracted": f["chars_extracted"]} for f in fetched]
    contents = [f["content"] for f in fetched]

    # Stage 3: Build combined document
    combined = f"# Research: {topic}\n\n"
    combined += f"Sources analyzed: {len(contents)}\n\n---\n\n"
    for i, (content, src) in enumerate(zip(contents, sources)):
        combined += f"## Source {i+1}: {src['title']}\n"
        combined += f"URL: {src['url']}\n\n"
        combined += content
        combined += "\n\n---\n\n"

    total_chars = len(combined)
    logger.info(
        "deep_url_analysis stage=gemini total_chars=%d sources=%d",
        total_chars,
        len(contents),
    )

    # Stage 4: Send to Gemini 3.1 Pro (1M context) via CLI
    if not analysis_prompt:
        analysis_prompt = (
            f"Analyze these {len(contents)} sources about '{topic}'. Provide:\n"
            "1. Key findings and consensus across sources\n"
            "2. Contradictions or disagreements between sources\n"
            "3. Gaps in coverage (what's missing)\n"
            "4. Critical assessment of source quality and reliability\n"
            "5. Actionable synthesis and recommendations\n"
            "Be comprehensive — you have the full text of all sources."
        )

    full_prompt = f"{analysis_prompt}\n\n---\n\nFULL SOURCE CONTENT ({total_chars} chars, {len(contents)} sources):\n\n{combined}"

    # Write to temp file (avoids shell arg length limits)
    gemini_response = ""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(full_prompt)
            tmp_path = f.name

        result = subprocess.run(
            ["gemini", "-m", model, "--approval-mode", "yolo", "-f", tmp_path],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=300,
        )

        if result.returncode == 0:
            gemini_response = result.stdout.strip()
        else:
            gemini_response = f"Gemini CLI error (exit {result.returncode}): {result.stderr[:500]}"

    except subprocess.TimeoutExpired:
        gemini_response = "Gemini CLI timed out after 300s"
    except FileNotFoundError:
        gemini_response = "Gemini CLI not found — install with: pip install gemini-cli"
    except Exception as e:
        gemini_response = f"Gemini CLI error: {str(e)[:200]}"
    finally:
        if tmp_path:
            import os
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    return {
        "topic": topic,
        "urls_found": len(urls),
        "urls_fetched": len(contents),
        "total_content_chars": total_chars,
        "gemini_analysis": gemini_response[:100000],
        "sources": sources,
        "errors": errors,
        "search_providers": providers_to_use,
        "model": model,
        "use_free_only": use_free_only,
    }
