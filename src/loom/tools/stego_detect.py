"""Steganography and covert channel detector — find hidden data in images and text."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.stego_detect")

_UNICODE_HOMOGLYPHS = {
    "А": "A", "В": "B", "С": "C", "Е": "E",
    "Н": "H", "К": "K", "М": "M", "О": "O",
    "Р": "P", "Т": "T", "Х": "X",
    "а": "a", "е": "e", "о": "o", "р": "p",
    "с": "c", "у": "y", "х": "x",
    "​": "ZWSP", "‌": "ZWNJ", "‍": "ZWJ",
    "⁠": "WJ", "﻿": "BOM",
}


def _check_lsb_anomaly(image_bytes: bytes) -> dict[str, Any]:
    """Check for LSB steganography anomalies (CPU-bound)."""
    try:
        import io

        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        lsb_layer = arr & 1
        lsb_mean = float(lsb_layer.mean())
        lsb_std = float(lsb_layer.std())
        entropy = -sum(
            p * (p and float(np.log2(p))) for p in [lsb_mean, 1 - lsb_mean] if p > 0
        )
        suspicious = abs(lsb_mean - 0.5) < 0.01 and lsb_std < 0.01
        return {
            "method": "lsb_analysis",
            "lsb_mean": round(lsb_mean, 6),
            "lsb_std": round(lsb_std, 6),
            "entropy": round(entropy, 4),
            "suspicious": suspicious,
            "description": "LSB layer shows uniform distribution — possible hidden data"
            if suspicious
            else "LSB layer appears normal",
        }
    except ImportError:
        return {"method": "lsb_analysis", "error": "numpy or Pillow not installed"}
    except Exception as exc:
        return {"method": "lsb_analysis", "error": str(exc)}


def _check_whitespace_stego(text: str) -> dict[str, Any]:
    """Check for whitespace/zero-width character steganography."""
    zero_width_chars = []
    for i, ch in enumerate(text):
        if ch in ("​", "‌", "‍", "⁠", "﻿"):
            zero_width_chars.append({"char": repr(ch), "position": i, "name": _UNICODE_HOMOGLYPHS.get(ch, "unknown")})
    trailing_spaces = sum(1 for line in text.splitlines() if line.endswith(" ") or line.endswith("\t"))
    return {
        "method": "whitespace_steganography",
        "zero_width_characters_found": len(zero_width_chars),
        "zero_width_details": zero_width_chars[:20],
        "trailing_whitespace_lines": trailing_spaces,
        "suspicious": len(zero_width_chars) >= 3 or trailing_spaces > 10,
        "description": "Multiple zero-width characters detected — possible hidden message"
        if len(zero_width_chars) >= 3
        else "No significant whitespace anomalies",
    }


def _check_homoglyphs(text: str) -> dict[str, Any]:
    """Check for homoglyph/lookalike character attacks."""
    found: list[dict[str, Any]] = []
    for i, ch in enumerate(text):
        if ch in _UNICODE_HOMOGLYPHS and ch not in ("​", "‌", "‍", "⁠", "﻿"):
            found.append({
                "char": ch,
                "looks_like": _UNICODE_HOMOGLYPHS[ch],
                "codepoint": f"U+{ord(ch):04X}",
                "position": i,
            })
    return {
        "method": "homoglyph_detection",
        "homoglyphs_found": len(found),
        "details": found[:30],
        "suspicious": len(found) > 3,
        "description": f"Found {len(found)} Unicode homoglyphs that look like ASCII but are different characters"
        if found
        else "No homoglyphs detected",
    }


def _check_exif_hidden(image_bytes: bytes) -> dict[str, Any]:
    """Check for hidden data in EXIF metadata (CPU-bound)."""
    try:
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        exif = img.getexif()
        suspicious_fields: list[dict[str, str]] = []
        for tag_id, value in exif.items():
            try:
                val_str = str(value)
                if len(val_str) > 100:
                    suspicious_fields.append({"tag_id": str(tag_id), "length": str(len(val_str)), "preview": val_str[:100]})
            except Exception as e:
                logger.debug("exif_field_parse_error: %s", e)

        comment = img.info.get("comment", b"")
        if isinstance(comment, bytes) and len(comment) > 10:
            suspicious_fields.append({"tag_id": "comment", "length": str(len(comment)), "preview": comment[:100].decode("utf-8", errors="replace")})

        return {
            "method": "exif_hidden_data",
            "suspicious_fields": suspicious_fields,
            "suspicious": len(suspicious_fields) > 0,
            "description": f"Found {len(suspicious_fields)} unusually large EXIF fields"
            if suspicious_fields
            else "No hidden EXIF data detected",
        }
    except ImportError:
        return {"method": "exif_hidden_data", "error": "Pillow not installed"}
    except Exception as exc:
        return {"method": "exif_hidden_data", "error": str(exc)}


async def research_stego_detect(
    content: str = "",
    image_url: str = "",
    check_whitespace: bool = True,
    check_homoglyphs: bool = True,
    check_lsb: bool = True,
    check_exif: bool = True,
) -> dict[str, Any]:
    """Detect steganography and hidden data in text content or images.

    Checks for: zero-width Unicode characters (whitespace steganography),
    Unicode homoglyphs (character substitution), LSB anomalies in images,
    and hidden data in EXIF metadata fields.

    CPU-intensive image analysis (LSB, EXIF) runs in the process pool
    to avoid blocking the async event loop.

    Args:
        content: text content to analyze for hidden data
        image_url: URL of image to download and analyze
        check_whitespace: check for zero-width character encoding
        check_homoglyphs: check for Unicode lookalike characters
        check_lsb: check image LSB layer for hidden data
        check_exif: check image EXIF for hidden fields

    Returns:
        Dict with analysis results per method, overall ``suspicious``
        flag, and ``total_anomalies`` count.
    """
    results: list[dict[str, Any]] = []
    total_anomalies = 0

    if content:
        if check_whitespace:
            ws = _check_whitespace_stego(content)
            results.append(ws)
            if ws.get("suspicious"):
                total_anomalies += 1
        if check_homoglyphs:
            hg = _check_homoglyphs(content)
            results.append(hg)
            if hg.get("suspicious"):
                total_anomalies += 1

    if image_url:
        image_bytes = b""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(image_url)
                if resp.status_code == 200:
                    image_bytes = resp.content[:10_000_000]
        except Exception as exc:
            logger.warning("stego_detect image fetch failed: %s", exc)

        if image_bytes:
            # Run CPU-intensive image analysis in executor
            try:
                from loom.cpu_executor import run_cpu_bound

                if check_lsb:
                    lsb = await run_cpu_bound(_check_lsb_anomaly, image_bytes)
                    results.append(lsb)
                    if lsb.get("suspicious"):
                        total_anomalies += 1

                if check_exif:
                    exif = await run_cpu_bound(_check_exif_hidden, image_bytes)
                    results.append(exif)
                    if exif.get("suspicious"):
                        total_anomalies += 1

            except Exception as exc:
                logger.error("stego_detect cpu_executor failed: %s", exc)
                results.append({
                    "method": "cpu_executor_error",
                    "error": str(exc)[:100],
                })

    return {
        "content_analyzed": bool(content),
        "image_analyzed": bool(image_url),
        "analyses": results,
        "total_anomalies": total_anomalies,
        "suspicious": total_anomalies > 0,
    }
