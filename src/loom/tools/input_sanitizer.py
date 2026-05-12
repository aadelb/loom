"""Input sanitization and validation tools for Loom."""
from __future__ import annotations
from loom.error_responses import handle_tool_errors
import logging
import re
import unicodedata
from typing import Any

logger = logging.getLogger("loom.tools.input_sanitizer")


@handle_tool_errors("research_sanitize_input")
async def research_sanitize_input(text: str, rules: list[str] | None = None) -> dict[str, Any]:
    """Sanitize text input. Rules: strip_nulls, normalize_unicode, limit_length, remove_control_chars, strip_html, escape_special."""
    try:
        if rules is None:
            rules = ["strip_nulls", "normalize_unicode", "limit_length", "remove_control_chars"]
        original_len, changes = len(text), []
        if "strip_nulls" in rules and "\x00" in text:
            b = len(text)
            text = text.replace("\x00", "")
            changes.append(f"strip_nulls: {b - len(text)}")
        if "normalize_unicode" in rules:
            b = text
            text = unicodedata.normalize("NFKC", text)
            if text != b:
                changes.append("normalize_unicode")
        if "limit_length" in rules and len(text) > 10000:
            changes.append(f"limit_length: {len(text)} -> 10000")
            text = text[:10000]
        if "remove_control_chars" in rules:
            b = len(text)
            text = "".join(c for c in text if ord(c) >= 32 or c in "\n\t")
            if len(text) < b:
                changes.append(f"remove_control_chars: {b - len(text)}")
        if "strip_html" in rules:
            b = len(text)
            text = re.sub(r"<[^>]+>", "", text)
            if len(text) < b:
                changes.append(f"strip_html: {b - len(text)}")
        if "escape_special" in rules:
            b = len(text)
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")
            if len(text) > b:
                changes.append("escape_special")
        return {"original_length": original_len, "sanitized_length": len(text), "rules_applied": rules, "changes_made": changes, "sanitized_text": text}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_sanitize_input"}


@handle_tool_errors("research_validate_params")
async def research_validate_params(params: dict[str, Any], schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate params against schema. Schema: {"field": {"type": str, "required": True, "min": 1, "max": 100}}."""
    try:
        if schema is None:
            schema = {}
        errors, warnings = [], []
        for field, rules in schema.items():
            if rules.get("required") and field not in params:
                tname = getattr(rules.get("type"), "__name__", str(rules.get("type")))
                errors.append({"field": field, "error": "required", "expected": tname, "got": None})
        for field, value in params.items():
            if field not in schema:
                warnings.append(f"unknown: {field}")
                continue
            rules = schema[field]
            tpe = rules.get("type")
            if tpe and not isinstance(value, tpe):
                errors.append({"field": field, "error": "type", "expected": tpe.__name__, "got": type(value).__name__})
                continue
            if isinstance(value, (int, float)):
                if "min" in rules and value < rules["min"]:
                    errors.append({"field": field, "error": "min", "expected": rules["min"], "got": value})
                if "max" in rules and value > rules["max"]:
                    errors.append({"field": field, "error": "max", "expected": rules["max"], "got": value})
            if isinstance(value, (str, list)):
                if "min_len" in rules and len(value) < rules["min_len"]:
                    errors.append({"field": field, "error": "min_len", "expected": rules["min_len"], "got": len(value)})
                if "max_len" in rules and len(value) > rules["max_len"]:
                    errors.append({"field": field, "error": "max_len", "expected": rules["max_len"], "got": len(value)})
            if "enum" in rules and value not in rules["enum"]:
                errors.append({"field": field, "error": "enum", "expected": rules["enum"], "got": value})
        return {"valid": not errors, "errors": errors, "warnings": warnings}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_validate_params"}
