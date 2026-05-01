"""research_document_extract — Unified document extraction with layout preservation.

Extracts structured content from PDFs, DOCX, PPTX, images, HTML, emails, and more
using the Unstructured library. Preserves document layout including headers, tables,
and lists.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile
from typing import Any

import httpx

from loom.validators import UrlSafetyError, validate_url

logger = logging.getLogger("loom.tools.unstructured_backend")

# Max file size: 100 MB
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024

# Max extracted text length
MAX_EXTRACTED_TEXT = 100000

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt",
    ".html", ".htm", ".txt", ".md",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
    ".eml", ".msg", ".xlsx", ".xls", ".csv",
    ".json", ".xml", ".rtf",
}

# Extraction strategies
VALID_STRATEGIES = {"auto", "fast", "hi_res", "ocr_only"}


async def research_document_extract(
    file_path: str = "",
    url: str = "",
    strategy: str = "auto",
) -> dict[str, Any]:
    """Extract structured content from any document type.

    Supports PDF, DOCX, PPTX, HTML, images, emails, and more with layout
    preservation (headers, tables, lists).

    Args:
        file_path: Local file path to extract from
        url: URL to download and extract from
        strategy: Extraction strategy ('auto', 'fast', 'hi_res', 'ocr_only')
                  auto: Automatically select best strategy for document type
                  fast: Quick extraction without OCR
                  hi_res: High-resolution extraction for complex documents
                  ocr_only: Use OCR exclusively (for scanned documents)

    Returns:
        Dict with:
        - file_path: Input file path or downloaded URL
        - elements: List of extracted elements (paragraphs, headers, tables, etc.)
        - element_count: Total number of elements extracted
        - element_types: Dict mapping element type to count
        - text_content: Full concatenated text (max 100000 chars)
        - metadata: Document metadata (page count, file type, etc.)
        - extraction_method: Method used ('unstructured', 'fallback', etc.)
        - strategy_used: Strategy that was applied
        - error: Error message if extraction failed (optional)
    """
    # Validate inputs
    if not file_path and not url:
        return {
            "error": "Either file_path or url must be provided",
            "elements": [],
            "element_count": 0,
            "element_types": {},
            "text_content": "",
            "metadata": {},
        }

    if file_path and url:
        return {
            "error": "Only one of file_path or url may be provided",
            "elements": [],
            "element_count": 0,
            "element_types": {},
            "text_content": "",
            "metadata": {},
        }

    # Validate strategy
    strategy = strategy.lower().strip()
    if strategy not in VALID_STRATEGIES:
        return {
            "error": f"strategy must be one of {VALID_STRATEGIES}",
            "elements": [],
            "element_count": 0,
            "element_types": {},
            "text_content": "",
            "metadata": {},
        }

    output: dict[str, Any] = {
        "elements": [],
        "element_count": 0,
        "element_types": {},
        "text_content": "",
        "metadata": {},
        "strategy_used": strategy,
    }

    # Handle URL-based extraction
    if url:
        try:
            validate_url(url)
        except UrlSafetyError as exc:
            return {**output, "error": str(exc), "url": url}

        return await _extract_from_url(url, strategy, output)

    # Handle file path extraction
    if file_path:
        return await _extract_from_file(file_path, strategy, output)

    return {**output, "error": "No file_path or url provided"}


async def _extract_from_url(
    url: str,
    strategy: str,
    output: dict[str, Any],
) -> dict[str, Any]:
    """Download document from URL and extract content."""
    output["url"] = url

    try:
        # Download file
        logger.info("document_download_start url=%s", url)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            # Stream to temp file with size check
            file_data = io.BytesIO()
            async for chunk in response.aiter_bytes(chunk_size=65536):
                file_data.write(chunk)
                if file_data.tell() > MAX_FILE_SIZE_BYTES:
                    return {
                        **output,
                        "error": f"File exceeds max size ({MAX_FILE_SIZE_BYTES} bytes)",
                    }

            file_bytes = file_data.getvalue()
            output["file_size_bytes"] = len(file_bytes)

        logger.info("document_download_complete url=%s size=%d", url, len(file_bytes))

        # Determine file extension from URL
        url_path = url.split("?")[0]  # Remove query params
        file_ext = ""
        if "." in url_path:
            file_ext = "." + url_path.rsplit(".", 1)[-1].lower()

        # Create temp file and extract
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            return await _extract_from_file(tmp_path, strategy, output)

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    except httpx.ConnectError as e:
        logger.warning("document_download_connect_failed url=%s: %s", url, e)
        return {**output, "error": f"Connection failed: {str(e)}"}

    except httpx.TimeoutException as e:
        logger.warning("document_download_timeout url=%s: %s", url, e)
        return {**output, "error": "Download timeout (>60 seconds)"}

    except httpx.HTTPStatusError as e:
        logger.warning("document_download_http_error url=%s status=%d", url, e.response.status_code)
        return {**output, "error": f"HTTP {e.response.status_code}"}

    except Exception as e:
        logger.exception("document_download_failed url=%s", url)
        return {**output, "error": str(e)}


async def _extract_from_file(
    file_path: str,
    strategy: str,
    output: dict[str, Any],
) -> dict[str, Any]:
    """Extract content from local file."""
    output["file_path"] = file_path

    # Validate file exists
    if not os.path.exists(file_path):
        return {**output, "error": f"File not found: {file_path}"}

    # Validate file extension
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in SUPPORTED_EXTENSIONS:
        return {
            **output,
            "error": f"Unsupported file type: {ext}. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        }

    try:
        logger.info("document_extraction_start file=%s strategy=%s", file_path, strategy)

        # Try unstructured library
        try:
            elements = await _extract_with_unstructured(file_path, strategy)
            extraction_method = "unstructured"
        except ImportError:
            logger.warning("unstructured library not installed, providing error message")
            return {
                **output,
                "error": (
                    "unstructured library not installed. "
                    "Install with: pip install 'unstructured[pdf,docx,pptx]' "
                    "For OCR support also: pip install pytesseract python-magic"
                ),
                "extraction_method": "none",
            }

        if not elements:
            logger.warning("document_extraction_empty file=%s", file_path)
            return {
                **output,
                "elements": [],
                "element_count": 0,
                "element_types": {},
                "text_content": "",
                "extraction_method": extraction_method,
            }

        # Process elements
        processed_elements = []
        element_types: dict[str, int] = {}
        text_parts = []

        for element in elements:
            element_dict = _serialize_element(element)
            if element_dict:
                processed_elements.append(element_dict)

                # Track element type
                elem_type = element_dict.get("type", "unknown")
                element_types[elem_type] = element_types.get(elem_type, 0) + 1

                # Accumulate text
                text = element_dict.get("text", "")
                if text:
                    text_parts.append(text)

        text_content = "\n".join(text_parts)

        # Cap extracted text
        if len(text_content) > MAX_EXTRACTED_TEXT:
            text_content = text_content[:MAX_EXTRACTED_TEXT]
            logger.warning("document_text_truncated file=%s", file_path)

        # Get file metadata
        file_size = os.path.getsize(file_path)
        _, ext = os.path.splitext(file_path)

        output.update({
            "elements": processed_elements,
            "element_count": len(processed_elements),
            "element_types": element_types,
            "text_content": text_content,
            "metadata": {
                "file_type": ext.lower().lstrip("."),
                "file_size_bytes": file_size,
                "element_types_summary": element_types,
            },
            "extraction_method": extraction_method,
        })

        logger.info(
            "document_extraction_success file=%s method=%s elements=%d types=%s",
            file_path, extraction_method, len(processed_elements), list(element_types.keys()),
        )

        return output

    except Exception as e:
        logger.exception("document_extraction_failed file=%s", file_path)
        return {**output, "error": str(e)}


async def _extract_with_unstructured(
    file_path: str,
    strategy: str,
) -> list[Any]:
    """Extract content using unstructured library in thread pool."""
    def _do_extract() -> list[Any]:
        from unstructured.partition.auto import partition
        from unstructured.partition.strategy import Strategy

        # Map strategy string to unstructured Strategy enum
        strategy_map = {
            "auto": Strategy.AUTO,
            "fast": Strategy.FAST,
            "hi_res": Strategy.HI_RES,
            "ocr_only": Strategy.OCR_ONLY,
        }

        strat = strategy_map.get(strategy, Strategy.AUTO)

        # Call partition with appropriate strategy
        elements = partition(
            filename=file_path,
            strategy=strat,
            include_page_breaks=True,
        )

        return elements

    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    elements = await loop.run_in_executor(None, _do_extract)
    return elements


def _serialize_element(element: Any) -> dict[str, Any]:
    """Convert unstructured element to serializable dict."""
    try:
        # Get element type
        elem_type = type(element).__name__

        # Get text content
        text = ""
        if hasattr(element, "text"):
            text = str(element.text).strip()

        if not text:
            return {}

        # Build element dict
        elem_dict: dict[str, Any] = {
            "type": elem_type,
            "text": text,
        }

        # Add metadata if available
        if hasattr(element, "metadata"):
            metadata = element.metadata
            if hasattr(metadata, "to_dict"):
                elem_dict["metadata"] = metadata.to_dict()
            elif isinstance(metadata, dict):
                elem_dict["metadata"] = metadata

        # Handle table elements
        if elem_type == "Table" and hasattr(element, "text"):
            elem_dict["type"] = "Table"

        # Handle list elements
        if elem_type == "ListItem":
            elem_dict["type"] = "ListItem"

        return elem_dict

    except Exception as e:
        logger.debug("element_serialization_failed: %s", e)
        return {}
