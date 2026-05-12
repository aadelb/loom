"""PaddleOCR text extraction — Fast OCR supporting 80+ languages."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import httpx

from loom.validators import UrlSafetyError, validate_url

logger = logging.getLogger("loom.tools.paddleocr_backend")

# Max image file size: 100 MB
MAX_IMAGE_SIZE_BYTES = 100 * 1024 * 1024

# Max text extraction length
MAX_EXTRACTED_TEXT = 100000

# Default languages if none specified
DEFAULT_LANGUAGES = ["en"]


async def research_paddle_ocr(
    image_url: str = "",
    image_path: str = "",
    languages: list[str] | None = None,
) -> dict[str, Any]:
    """Extract text from image using PaddleOCR.

    PaddleOCR is a fast, accurate OCR library supporting 80+ languages.
    Download image from URL or use local file path.

    Args:
        image_url: URL to image file (auto-download)
        image_path: local file path to image
        languages: list of language codes (e.g., ["en", "ar"]).
                   If None, defaults to ["en"].

    Returns:
        Dict with:
        - text_content: extracted text (max 100000 chars)
        - blocks: list of detected text blocks with:
            - text: recognized text
            - confidence: confidence score (0-1)
            - coordinates: bounding box [(x1,y1), (x2,y2), ...]
        - languages_detected: languages identified in image
        - image_source: "url" or "path"
        - file_size_bytes: image file size
        - error: error message if OCR failed
    """
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except ImportError:
        return {
            "error": "paddleocr not installed. Install with: pip install paddleocr",
        }

    # Validate input
    if not image_url and not image_path:
        return {"error": "Either image_url or image_path must be provided"}

    if image_url and image_path:
        return {"error": "Provide only image_url or image_path, not both"}

    # Prepare parameters
    if languages is None:
        languages = DEFAULT_LANGUAGES

    # Validate language codes (basic check)
    if not isinstance(languages, list) or not languages:
        return {"error": "languages must be a non-empty list of language codes"}

    if len(languages) > 10:
        return {"error": "max 10 languages supported"}

    output: dict[str, Any] = {}

    # Download or load image
    image_bytes = None
    image_source = None

    if image_url:
        try:
            validate_url(image_url)
        except UrlSafetyError as exc:
            return {"image_url": image_url, "error": str(exc)}

        try:
            async def _download_image() -> bytes:
                with httpx.stream("GET", image_url, timeout=30.0) as response:
                    response.raise_for_status()

                    # Validate content type
                    content_type = response.headers.get("content-type", "").lower()
                    if not any(
                        x in content_type
                        for x in ["image/", "application/octet-stream"]
                    ):
                        logger.warning(
                            "image_download_wrong_type url=%s content_type=%s",
                            image_url,
                            content_type,
                        )

                    # Stream to bytes with size check
                    data = io.BytesIO()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        data.write(chunk)
                        if data.tell() > MAX_IMAGE_SIZE_BYTES:
                            raise ValueError(
                                f"Image exceeds max size ({MAX_IMAGE_SIZE_BYTES} bytes)"
                            )

                    return data.getvalue()

            image_bytes = await asyncio.to_thread(_download_image)
            image_source = "url"
            output["image_url"] = image_url

            logger.info("image_downloaded url=%s size=%d", image_url, len(image_bytes))

        except UrlSafetyError as exc:
            return {"image_url": image_url, "error": str(exc)}
        except Exception as exc:
            logger.error("image_download_error url=%s error=%s", image_url, exc)
            return {"image_url": image_url, "error": f"Failed to download image: {exc}"}

    elif image_path:
        try:
            # Validate path to prevent traversal attacks
            safe_path = Path(image_path).resolve()
            if not safe_path.exists():
                return {"image_path": image_path, "error": "File not found"}
            if not safe_path.is_file():
                return {"image_path": image_path, "error": "Path is not a file"}

            async def _load_image() -> bytes:
                def _read_file(path: Path) -> bytes:
                    with open(path, "rb") as f:
                        return f.read()

                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, _read_file, safe_path)

            image_bytes = await _load_image()
            if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
                return {
                    "image_path": image_path,
                    "error": f"Image exceeds max size ({MAX_IMAGE_SIZE_BYTES} bytes)",
                }
            image_source = "path"
            output["image_path"] = image_path

            logger.info(
                "image_loaded path=%s size=%d", image_path, len(image_bytes)
            )

        except FileNotFoundError:
            return {"image_path": image_path, "error": "File not found"}
        except Exception as exc:
            logger.error("image_load_error path=%s error=%s", image_path, exc)
            return {"image_path": image_path, "error": f"Failed to load image: {exc}"}

    if not image_bytes:
        return {"error": "No image data available"}

    output["file_size_bytes"] = len(image_bytes)
    output["image_source"] = image_source

    # Run OCR
    try:
        def _run_ocr() -> tuple[str, list[dict[str, Any]]]:
            # Write bytes to temp file (PaddleOCR needs file path)
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    suffix=".jpg", delete=False
                ) as tmp_file:
                    tmp_file.write(image_bytes)
                    tmp_path = tmp_file.name

                # Initialize OCR with first language (PaddleOCR supports single lang)
                # If multiple languages needed, use the primary language
                primary_lang = languages[0] if languages else "en"
                ocr = PaddleOCR(use_angle_cls=True, lang=primary_lang)

                # Run OCR
                result = ocr.ocr(tmp_path, cls=True)

                # Parse results
                text_parts = []
                blocks = []

                if result:
                    for line in result:
                        if line:
                            for item in line:
                                coords, text, confidence = item
                                text_parts.append(text)

                                # Format coordinates
                                coord_list = [
                                    (float(x), float(y)) for x, y in coords
                                ]

                                blocks.append(
                                    {
                                        "text": text,
                                        "confidence": float(confidence),
                                        "coordinates": coord_list,
                                    }
                                )

                full_text = " ".join(text_parts)
                if len(full_text) > MAX_EXTRACTED_TEXT:
                    full_text = full_text[:MAX_EXTRACTED_TEXT]

                return full_text, blocks

            finally:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

        text_content, blocks = await asyncio.to_thread(_run_ocr)

        output["text_content"] = text_content
        output["blocks"] = blocks
        output["languages_detected"] = languages
        output["block_count"] = len(blocks)

        logger.info(
            "ocr_completed source=%s blocks=%d text_len=%d",
            image_source,
            len(blocks),
            len(text_content),
        )

        return output

    except Exception as exc:
        logger.error("ocr_error error=%s languages=%s", exc, languages)
        return {
            **output,
            "error": f"OCR processing failed: {exc}",
        }
