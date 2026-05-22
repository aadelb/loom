"""Steganography encoder/analyzer — text-based hiding methods."""

from __future__ import annotations

import base64
from typing import Any, Literal

from loom.error_responses import handle_tool_errors

@handle_tool_errors("research_stego_encode")
def research_stego_encode(
    message: str,
    method: Literal["lsb", "whitespace", "unicode_zero_width", "metadata_exif", "audio_lsb", "video_lsb", "pdf_whitespace"] = "lsb",
    output_format: str = "description",
) -> dict[str, Any]:
    """Describe steganography encoding (no image creation)."""
    if isinstance(message, list):
        message = " ".join(str(x) for x in message)
    if isinstance(message, dict):
        message = str(message)
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
            "audio_lsb": {
                "description": "Hide data in LSB of WAV/FLAC audio samples (16-bit PCM)",
                "capacity": f"{msg_bits} bits (~{msg_bits / 44100:.2f}s of 44.1kHz mono audio)",
                "detection": "Low (spectral analysis may detect, human ear cannot)",
                "pros": ["Inaudible", "High capacity in WAV", "Survives format conversion if lossless"],
                "cons": ["MP3/AAC compression destroys payload", "Large carrier files", "Requires lossless format"],
                "implementation": "Modify LSB of each 16-bit PCM sample. Use wave module for WAV files.",
                "carrier_requirement": f"WAV file with >= {msg_bits} samples ({msg_bits / 44100:.2f}s at 44.1kHz)",
            },
            "video_lsb": {
                "description": "Hide data in LSB of video frame pixels (I-frames only)",
                "capacity": f"{msg_bits} bits (~{msg_bits / (1920 * 1080 * 3):.4f} frames at 1080p)",
                "detection": "Medium (frame diff analysis reveals, but spread across frames is harder)",
                "pros": ["Massive capacity", "Multiple embedding layers (spatial + temporal)", "Robust with I-frames"],
                "cons": ["Re-encoding destroys", "Requires raw/lossless", "Complex extraction", "Large files"],
                "implementation": "Extract I-frames via ffmpeg, embed in pixel LSBs, re-mux. Use only keyframes.",
                "carrier_requirement": f"Video with >= {max(1, msg_bits // (1920 * 1080 * 3) + 1)} I-frames at 1080p",
            },
            "pdf_whitespace": {
                "description": "Hide data in PDF whitespace: extra spaces between words, trailing spaces, font size micro-variation",
                "capacity": f"~{msg_bits} bits (~{msg_len} chars) in a 1-page PDF",
                "detection": "Low-Medium (PDF text extraction normalizes whitespace, but raw bytes reveal)",
                "pros": ["Works with any PDF", "Survives printing if font-based", "Common format"],
                "cons": ["OCR re-extraction loses payload", "PDF optimization strips whitespace", "Limited capacity"],
                "implementation": "Insert U+2003 (em space) for 1, U+2002 (en space) for 0 between words.",
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


@handle_tool_errors("research_stego_analyze")
def research_stego_analyze(text: str) -> dict[str, Any]:
    """Analyze text for hidden steganographic content."""
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, dict):
        text = str(text)
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
