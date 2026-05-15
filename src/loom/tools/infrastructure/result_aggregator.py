"""research_aggregate_results / research_aggregate_texts — Combine multiple tool outputs."""

from __future__ import annotations

import logging
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from loom.text_utils import truncate
except ImportError:
    def truncate(text, max_chars=500, *, suffix="..."):
        if len(text) <= max_chars: return text
        return text[:max_chars - len(suffix)] + suffix

logger = logging.getLogger("loom.tools.result_aggregator")

MAX_RESULTS, MAX_TEXTS, MAX_TEXT_LENGTH = 100, 50, 50000


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override dict into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _deduplicate_texts(texts: list[str]) -> list[str]:
    """Remove duplicate sentences/lines across texts."""
    seen = set()
    deduped = []
    for text in texts:
        for line in (l.strip() for l in text.split('\n') if l.strip()):
            norm = line.lower()
            if norm not in seen:
                seen.add(norm)
                deduped.append(line)
    return deduped


@handle_tool_errors("research_aggregate_results")
async def research_aggregate_results(
    results: list[dict],
    strategy: str = "merge",
) -> dict[str, Any]:
    """Combine multiple tool results into unified output.

    Args:
        results: list of dict results from multiple tools
        strategy: aggregation strategy ("merge", "concatenate", "summarize", "deduplicate", "rank")

    Returns:
        Dict with: {strategy, input_count, aggregated, fields_merged, conflicts_resolved}
    """
    if not results or not isinstance(results, list):
        return {"error": "results must be non-empty list", "input_count": 0}

    results = results[:MAX_RESULTS]
    aggregated: dict[str, Any] = {}
    fields_merged = conflicts_resolved = 0

    try:
        if strategy == "merge":
            aggregated = (results[0].copy() if results else {})
            for result in results[1:]:
                old_keys = set(aggregated.keys())
                aggregated = _deep_merge(aggregated, result)
                fields_merged += len(set(aggregated.keys()) - old_keys)
                conflicts_resolved += sum(1 for k in old_keys if k in result)

        elif strategy == "concatenate":
            all_keys = {k for r in results for k in r.keys()}
            for key in all_keys:
                values = [str(r.get(key, "")) for r in results if key in r and r[key]]
                if values:
                    aggregated[key] = " | ".join(values)
                    fields_merged += 1

        elif strategy == "summarize":
            aggregated["results"] = [
                {k: v for k, v in r.items() if isinstance(v, (str, int, float, bool))}
                for r in results
            ]
            fields_merged = sum(len(s) for s in aggregated["results"])

        elif strategy == "deduplicate":
            text_fields = {}
            non_text_fields = {}
            for result in results:
                for key, value in result.items():
                    if isinstance(value, str):
                        text_fields.setdefault(key, []).append(value)
                    else:
                        non_text_fields.setdefault(key, []).append(value)
            for key, texts in text_fields.items():
                aggregated[key] = "\n".join(_deduplicate_texts(texts))
                fields_merged += 1
            for key, values in non_text_fields.items():
                aggregated[key] = values[0] if len(values) == 1 else values
                fields_merged += 1

        elif strategy == "rank":
            aggregated["ranked_results"] = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
            fields_merged = len(results)

        logger.info("aggregate_results completed strategy=%s input_count=%d", strategy, len(results))
        return {"strategy": strategy, "input_count": len(results), "aggregated": aggregated,
                "fields_merged": fields_merged, "conflicts_resolved": conflicts_resolved}

    except Exception as e:
        logger.error("aggregate_results_error strategy=%s error=%s", strategy, e)
        return {"error": str(e), "strategy": strategy, "input_count": len(results)}


@handle_tool_errors("research_aggregate_texts")
async def research_aggregate_texts(
    texts: list[str],
    method: str = "concatenate",
    max_length: int = 5000,
) -> dict[str, Any]:
    """Aggregate multiple text outputs.

    Args:
        texts: list of text strings to aggregate
        method: "concatenate", "deduplicate", "summarize", or "bullet_points"
        max_length: max output length in chars (100-50000)

    Returns:
        Dict with: {method, input_count, output_text, output_length, compression_ratio}
    """
    if not texts or not isinstance(texts, list):
        return {"error": "texts must be non-empty list", "input_count": 0}

    texts = texts[:MAX_TEXTS]
    max_length = min(max_length, MAX_TEXT_LENGTH)
    input_chars = sum(len(t) for t in texts if isinstance(t, str))

    try:
        if method == "concatenate":
            output_text = "\n".join(str(t) for t in texts)
        elif method == "deduplicate":
            output_text = "\n".join(_deduplicate_texts(texts))
        elif method == "summarize":
            summaries = [t.split('.')[0].strip() + "." if (sentences := t.split('.')) else "" for t in texts]
            output_text = "\n".join(s for s in summaries if s)
        elif method == "bullet_points":
            output_text = "\n".join(f"- {str(t).strip()}" for t in texts)
        else:
            output_text = "\n".join(str(t) for t in texts)

        output_text = truncate(output_text, max_length)
        compression_ratio = round(len(output_text) / input_chars, 2) if input_chars > 0 else 0

        logger.info("aggregate_texts completed method=%s input_count=%d output_len=%d",
                   method, len(texts), len(output_text))

        return {"method": method, "input_count": len(texts), "output_text": output_text,
                "output_length": len(output_text), "compression_ratio": compression_ratio}

    except Exception as e:
        logger.error("aggregate_texts_error method=%s error=%s", method, e)
        return {"error": str(e), "method": method, "input_count": len(texts)}
