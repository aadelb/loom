"""Steganography encoder/analyzer — text-based hiding methods."""
from __future__ import annotations
import base64
from typing import Any, Literal


def research_stego_encode(
    message: str,
    method: Literal["lsb", "whitespace", "unicode_zero_width", "metadata_exif"] = "lsb",
    output_format: str = "description",
) -> dict[str, Any]:
    """Describe steganography encoding (no image creation)."""
    try:
        if len(message) > 1000 or not message:
            raise ValueError("message must be 1-1000 characters")
        msg_len, msg_bits = len(message.encode()), len(message.encode()) * 8
        px_size = int((msg_bits**0.5))
        methods = {
            "lsb": {
                "description": "1 bit per RGB channel LSB in pixels",
                "capacity": f"{msg_bits} bits (~{px_size}×{px_size} px image)",
                "detection": "Low (spectrum analysis detects LSB noise)",
                "pros": ["Fast", "Low CPU", "Any format"],
                "cons": ["Lossy compression", "Steganalysis", "Linear capacity"],
            },
            "whitespace": {
                "description": "0→regular space, 1→non-breaking space (U+00A0)",
                "capacity": f"{msg_bits} bits (~{msg_len * 4} chars)",
                "detection": "Medium (byte-level inspection)",
                "pros": ["Text-native", "Invisible", "Simple"],
                "cons": ["Editor normalization", "Copy-paste loss"],
            },
            "unicode_zero_width": {
                "description": "ZWSP(U+200B)=0, ZWNJ(U+200C)=1, ZWJ(U+200D), BOM(U+FEFF)",
                "capacity": f"{msg_bits} bits in ~{msg_len * 2} carrier chars",
                "detection": "Low-Medium (regex reveals)",
                "pros": ["Copy-paste survives", "Invisible", "Unicode-native"],
                "cons": ["Regex detection", "Normalization", "Char count inflates"],
            },
            "metadata_exif": {
                "description": "Embed in EXIF: Author, UserComment, ImageDescription",
                "capacity": "Up to 65KB per field",
                "detection": "Very Low (exiftool reads instantly)",
                "pros": ["Large capacity", "Standard", "Survives sharing"],
                "cons": ["Online tools strip", "EXIF analysis detects", "No deniability"],
            },
        }
        if method not in methods:
            raise ValueError(f"method in {list(methods.keys())}")
        return {"method": method, "message_length": msg_len, "base64_encoded": base64.b64encode(message.encode()).decode(), **methods[method]}
    except Exception as exc:
        return {
            "error": str(exc),
            "tool": "research_stego_encode",
        }


def research_stego_analyze(text: str) -> dict[str, Any]:
    """Analyze text for hidden steganographic content."""
    try:
        if len(text) > 5000 or not text:
            raise ValueError("text must be 1-5000 characters")
        zw_map = {"​": "ZWSP", "‌": "ZWNJ", "‍": "ZWJ", "﻿": "BOM"}
        zw_chars = [zw_map[c] for c in text if c in zw_map]
        unusual_spaces = text.count(" ")
        valid_b64, b64_cand = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="), []
        for w in text.split():
            if 8 <= len(w) and all(c in valid_b64 for c in w):
                try:
                    base64.b64decode(w, validate=True)
                    b64_cand.append(w)
                except Exception:
                    pass
        homoglyphs = {c for c in text if c in "аеорсухы"}
        methods, scores = [], {}
        if zw_chars:
            methods.append("unicode_zero_width")
            scores["unicode_zero_width"] = min(100, 50 + len(zw_chars) * 10)
        if unusual_spaces:
            methods.append("whitespace")
            scores["whitespace"] = min(100, 30 + unusual_spaces * 5)
        if homoglyphs:
            methods.append("homoglyph")
            scores["homoglyph"] = 60
        if b64_cand:
            methods.append("base64")
            scores["base64"] = min(100, 40 + len(b64_cand) * 15)
        return {"hidden_content_found": bool(methods), "methods_detected": methods, "confidence_scores": scores, "text_length": len(text), "zero_width_count": len(zw_chars), "base64_count": len(b64_cand), "homoglyph_count": len(homoglyphs)}
    except Exception as exc:
        return {
            "error": str(exc),
            "tool": "research_stego_analyze",
        }
