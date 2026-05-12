"""LLM output parsing utilities.

Extracts structured data (JSON, lists, key-value pairs) from raw LLM
text output. Handles markdown fencing, trailing commas, partial JSON.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger("loom.llm_parsers")

_JSON_BLOCK_RE = re.compile(r'```(?:json)?\s*\n?(.*?)\n?```', re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r',\s*([}\]])')


def extract_json(text: str) -> Any | None:
    """Extract JSON from LLM output, handling markdown fencing and trailing commas.

    Tries in order:
    1. Parse the full text as JSON
    2. Extract from ```json ... ``` fenced blocks (fixes trailing commas)
    3. Find the first { } or [ ] boundaries in text

    Priority: Direct parse → Fenced blocks → Boundary extraction.
    Preference: Objects (dicts) over arrays when both present.
    Returns parsed JSON or None on failure.

    Note: When extracting by boundaries, prefers '{}' over '[]', so nested
    arrays inside objects are found before the array itself. Use markdown
    fencing (```json ... ```) for unambiguous extraction of top-level arrays.
    """
    # Try 1: Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try 2: Fenced code blocks
    for match in _JSON_BLOCK_RE.finditer(text):
        candidate = match.group(1).strip()
        candidate = _TRAILING_COMMA_RE.sub(r'\1', candidate)
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue

    # Try 3: Find { } or [ ] boundaries
    for opener, closer in [('{', '}'), ('[', ']')]:
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    candidate = _TRAILING_COMMA_RE.sub(r'\1', candidate)
                    try:
                        return json.loads(candidate)
                    except (json.JSONDecodeError, ValueError):
                        break
    return None


def extract_json_or_default(text: str, default: Any = None) -> Any:
    """Extract JSON from LLM output, returning default on failure.

    Args:
        text: Raw LLM output text
        default: Value to return if extraction fails (default: None)

    Returns:
        Parsed JSON or default value
    """
    result = extract_json(text)
    return result if result is not None else default


def extract_list(text: str) -> list[str]:
    """Extract a bullet/numbered list from LLM output.

    Matches patterns like:
    - item text
    * item text
    • item text
    1. item text
    1) item text

    Args:
        text: Raw LLM output text

    Returns:
        List of extracted items (strings), empty list if none found
    """
    lines = text.strip().splitlines()
    items: list[str] = []
    for line in lines:
        line = line.strip()
        m = re.match(r'^(?:[-*•]\s+|\d+[.)]\s+)(.*)', line)
        if m:
            items.append(m.group(1).strip())
    return items


def extract_score(text: str, *, scale: float = 10.0) -> float | None:
    """Extract a numeric score from LLM output.

    Looks for patterns like "Score: 7/10", "Rating: 8.5", "7 out of 10".
    Returns the score normalized to [0, scale], or None if not found.

    Args:
        text: Raw LLM output text
        scale: Maximum scale value (default: 10.0)

    Returns:
        Normalized score float or None if not found
    """
    patterns = [
        r'(?:score|rating|grade)[:\s]+(\d+(?:\.\d+)?)\s*/\s*(\d+)',
        r'(\d+(?:\.\d+)?)\s*(?:out of|/)\s*(\d+)',
        r'(?:score|rating|grade)[:\s]+(\d+(?:\.\d+)?)',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            groups = m.groups()
            value = float(groups[0])
            if len(groups) > 1 and groups[1]:
                max_val = float(groups[1])
                if max_val > 0:
                    return round(value / max_val * scale, 2)
            return min(value, scale)
    return None
