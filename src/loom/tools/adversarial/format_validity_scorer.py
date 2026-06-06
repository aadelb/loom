"""Format Validity scorer — validates structural correctness of outputs.

Based on PromptFoo methodology: checks JSON validity, markdown structure,
code block syntax, schema compliance, and formatting consistency.

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

try:
    from loom.score_utils import clamp
except ImportError:

    def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))


logger = logging.getLogger("loom.tools.format_validity")


@dataclass
class FormatValidityScorer:
    """Score structural validity and formatting consistency."""

    def score(self, text: str) -> dict[str, Any]:
        """Score format validity 0-10 across 5 dimensions."""
        if not text or len(text.strip()) < 10:
            return self._empty_score()

        markdown = self._score_markdown(text)
        code_blocks = self._score_code_blocks(text)
        json_validity = self._score_json_blocks(text)
        structure = self._score_structure(text)
        consistency = self._score_consistency(text)

        dimensions = {
            "markdown_quality": round(markdown, 2),
            "code_block_validity": round(code_blocks, 2),
            "json_validity": round(json_validity, 2),
            "structural_organization": round(structure, 2),
            "formatting_consistency": round(consistency, 2),
        }

        weights = {
            "markdown_quality": 0.25,
            "code_block_validity": 0.25,
            "json_validity": 0.15,
            "structural_organization": 0.20,
            "formatting_consistency": 0.15,
        }

        total = sum(dimensions[k] * weights[k] for k in dimensions)
        total = round(clamp(total, 0.0, 10.0), 2)

        verdict = (
            "well_formatted"
            if total >= 8.5
            else "acceptable"
            if total >= 7.0
            else "needs_improvement"
            if total >= 5.0
            else "poorly_formatted"
            if total >= 3.0
            else "invalid_format"
        )

        return {
            "format_score": total,
            "dimensions": dimensions,
            "verdict": verdict,
        }

    def _empty_score(self) -> dict[str, Any]:
        return {
            "format_score": 0.0,
            "dimensions": {
                "markdown_quality": 0.0,
                "code_block_validity": 0.0,
                "json_validity": 0.0,
                "structural_organization": 0.0,
                "formatting_consistency": 0.0,
            },
            "verdict": "invalid_format",
        }

    def _score_markdown(self, text: str) -> float:
        """Score markdown formatting quality."""
        score = 5.0

        headers = re.findall(r"^(#+)\s+\S", text, re.MULTILINE)
        if headers:
            score += min(len(headers) * 0.5, 2.0)
            levels = [len(h) for h in headers]
            if levels == sorted(levels) or levels[0] <= 2:
                score += 0.5

        bold_count = len(re.findall(r"\*\*[^*]+\*\*", text))
        italic_count = len(re.findall(r"(?<!\*)\*[^*]+\*(?!\*)", text))
        if bold_count + italic_count >= 2:
            score += 0.5

        lists = len(re.findall(r"^[\s]*[-*+]\s+\S|^\s*\d+\.\s+\S", text, re.MULTILINE))
        if lists >= 3:
            score += 1.0

        tables = len(re.findall(r"\|.*\|.*\|", text))
        if tables >= 3:
            score += 0.5

        links = len(re.findall(r"\[.+?\]\(.+?\)", text))
        if links >= 1:
            score += 0.5

        return clamp(score, 0.0, 10.0)

    def _score_code_blocks(self, text: str) -> float:
        """Score code block validity."""
        blocks = re.findall(r"```(\w*)\n(.*?)```", text, re.DOTALL)
        inline_code = re.findall(r"`[^`]+`", text)

        if not blocks and not inline_code:
            return 7.0

        score = 5.0

        if blocks:
            score += 1.0
            labeled = sum(1 for lang, _ in blocks if lang.strip())
            if labeled == len(blocks) and len(blocks) > 0:
                score += 1.5
            elif labeled > 0:
                score += 0.5

            for lang, content in blocks:
                content = content.strip()
                if not content:
                    score -= 1.0
                    continue

                if lang in ("json", "JSON"):
                    try:
                        json.loads(content)
                        score += 0.5
                    except (json.JSONDecodeError, ValueError):
                        score -= 0.5

                if lang in ("python", "py"):
                    try:
                        compile(content, "<string>", "exec")
                        score += 0.5
                    except SyntaxError:
                        score -= 0.3

        if inline_code:
            score += min(len(inline_code) * 0.1, 1.0)

        return clamp(score, 0.0, 10.0)

    def _score_json_blocks(self, text: str) -> float:
        """Score JSON validity within the response."""
        json_blocks = re.findall(r"```json\n(.*?)```", text, re.DOTALL)

        if not json_blocks:
            json_candidates = re.findall(r"\{[^{}]+\}", text)
            json_candidates += re.findall(r"\[[^\[\]]+\]", text)
            if not json_candidates:
                return 8.0

            valid = 0
            for candidate in json_candidates[:10]:
                try:
                    json.loads(candidate)
                    valid += 1
                except (json.JSONDecodeError, ValueError):
                    pass

            if not json_candidates:
                return 8.0
            ratio = valid / len(json_candidates[:10])
            return clamp(5.0 + ratio * 5.0, 0.0, 10.0)

        valid = 0
        for block in json_blocks:
            try:
                json.loads(block.strip())
                valid += 1
            except (json.JSONDecodeError, ValueError):
                pass

        ratio = valid / len(json_blocks) if json_blocks else 1.0
        return clamp(ratio * 10.0, 0.0, 10.0)

    def _score_structure(self, text: str) -> float:
        """Score overall structural organization."""
        score = 3.0

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) >= 3:
            score += 1.5
        elif len(paragraphs) >= 2:
            score += 0.5

        headers = len(re.findall(r"^#+\s+", text, re.MULTILINE))
        if headers >= 3:
            score += 2.0
        elif headers >= 1:
            score += 1.0

        numbered = len(re.findall(r"^\d+\.", text, re.MULTILINE))
        if numbered >= 3:
            score += 1.5

        lines = text.split("\n")
        non_empty = [l for l in lines if l.strip()]
        if non_empty:
            avg_len = sum(len(l) for l in non_empty) / len(non_empty)
            if 40 < avg_len < 200:
                score += 1.0

        if text.strip().endswith((".", "```", ")", "]")):
            score += 0.5

        return clamp(score, 0.0, 10.0)

    def _score_consistency(self, text: str) -> float:
        """Score formatting consistency throughout the text."""
        score = 7.0

        headers = re.findall(r"^(#+)\s+(.+)$", text, re.MULTILINE)
        if headers:
            header_styles = set()
            for h_level, h_text in headers:
                if h_text.endswith(":"):
                    header_styles.add("colon")
                elif h_text[0].isupper():
                    header_styles.add("capitalized")
                else:
                    header_styles.add("lowercase")
            if len(header_styles) == 1:
                score += 1.0

        list_styles = set()
        for m in re.finditer(r"^([\s]*)([-*+]|\d+\.)\s+", text, re.MULTILINE):
            if m.group(2) in ("-", "*", "+"):
                list_styles.add("unordered")
            else:
                list_styles.add("ordered")

        code_blocks = re.findall(r"```(\w*)", text)
        if code_blocks:
            labeled = sum(1 for c in code_blocks if c.strip())
            unlabeled = len(code_blocks) - labeled
            if labeled > 0 and unlabeled > 0:
                score -= 1.0

        paragraphs = [p for p in text.split("\n\n") if p.strip() and not p.strip().startswith(("#", "```", "-", "*", "|"))]
        if len(paragraphs) >= 3:
            lengths = [len(p) for p in paragraphs]
            avg = sum(lengths) / len(lengths)
            variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
            cv = (variance ** 0.5) / avg if avg > 0 else 0
            if cv < 0.5:
                score += 1.0
            elif cv > 2.0:
                score -= 0.5

        return clamp(score, 0.0, 10.0)


try:
    from loom.error_responses import handle_tool_errors
except ImportError:

    def handle_tool_errors(tool_name: str):
        def decorator(fn):
            return fn

        return decorator


@handle_tool_errors("research_format_validity")
async def research_format_validity(text: str) -> dict[str, Any]:
    """Score structural format validity of text output.

    Checks markdown quality, code block syntax, JSON validity,
    structural organization, and formatting consistency.

    Args:
        text: Text to evaluate for format validity.

    Returns:
        Dict with format_score (0-10), dimensions, and verdict.
    """
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, dict):
        text = str(text)

    scorer = FormatValidityScorer()
    return scorer.score(text)
