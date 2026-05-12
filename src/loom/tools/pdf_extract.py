"""PDF extraction tools — Extract text from PDF URLs and search within PDFs."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import subprocess
import tempfile
from typing import Any

import httpx

from loom.validators import UrlSafetyError, validate_url
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.pdf_extract")

# Max PDF file size: 50 MB
MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024

# Max extracted text length
MAX_EXTRACTED_TEXT = 50000


def _extract_pdf_text_sync(pdf_bytes: bytes, start_page: int | None, end_page: int | None) -> tuple[str | None, str | None, int | None]:
    """Extract text from PDF bytes using PyPDF2 (CPU-bound sync function).

    Args:
        pdf_bytes: Raw PDF file bytes
        start_page: 1-indexed start page or None
        end_page: 1-indexed end page or None

    Returns:
        Tuple of (extracted_text, extraction_method, page_count) or (None, None, None) on failure
    """
    try:
        from PyPDF2 import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(pdf_bytes))
        page_count = len(reader.pages)

        # Determine which pages to extract
        if start_page is not None:
            # Convert 1-indexed to 0-indexed
            pages_to_extract = range(start_page - 1, min(end_page, page_count))
        else:
            pages_to_extract = range(page_count)

        text_parts = []
        for page_num in pages_to_extract:
            page = reader.pages[page_num]
            text = page.extract_text()
            if text:
                text_parts.append(text)

        extracted_text = "\n".join(text_parts)
        logger.info("pdf_extraction_pypdf2_success pages=%d", len(pages_to_extract))
        return extracted_text, "pypdf2", page_count

    except ImportError:
        logger.debug("PyPDF2 not available")
        return None, None, None
    except Exception as exc:
        logger.debug("PyPDF2 extraction failed: %s", exc)
        return None, None, None


def _extract_pdf_text_pdftotext(pdf_bytes: bytes, start_page: int | None, end_page: int | None) -> tuple[str | None, str | None, int | None]:
    """Extract text from PDF using pdftotext CLI (CPU-bound sync function).

    Args:
        pdf_bytes: Raw PDF file bytes
        start_page: 1-indexed start page or None
        end_page: 1-indexed end page or None

    Returns:
        Tuple of (extracted_text, extraction_method, page_count) or (None, None, None) on failure
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        cmd = ["pdftotext"]

        # Add page range if specified
        if start_page is not None and end_page is not None:
            cmd.extend(["-f", str(start_page), "-l", str(end_page)])

        cmd.extend([tmp_path, "-"])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.warning("pdftotext_failed returncode=%d", result.returncode)
            return None, None, None

        logger.info("pdf_extraction_pdftotext_success")
        # pdftotext doesn't report page count
        return result.stdout, "pdftotext", None

    except FileNotFoundError:
        logger.error("pdftotext_not_found")
        return None, None, None
    except subprocess.TimeoutExpired:
        logger.warning("pdftotext_timeout")
        return None, None, None
    except Exception as exc:
        logger.error("pdftotext_extraction_error: %s", exc)
        return None, None, None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@handle_tool_errors("research_pdf_extract")
async def research_pdf_extract(
    url: str, pages: str | None = None
) -> dict[str, Any]:
    """Extract text from a PDF URL.

    Downloads the PDF, extracts text using PyPDF2 or pdftotext CLI.
    Optionally extracts only specified pages. CPU-intensive parsing
    runs in the process pool to avoid blocking the event loop.

    Args:
        url: URL to PDF file
        pages: page range to extract, e.g., "1-5" or "1" (1-indexed)
               If None, extracts all pages.

    Returns:
        Dict with:
        - url: the input URL
        - text: extracted text (max 50000 chars)
        - page_count: total pages in PDF
        - pages_extracted: "all" or range like "1-5"
        - extraction_method: "pypdf2" or "pdftotext"
        - file_size_bytes: downloaded file size
        - error: error message if extraction failed
    """
    try:
        validate_url(url)
    except UrlSafetyError as exc:
        return {"url": url, "error": str(exc)}

    try:
        start_page, end_page = _parse_pages_arg(pages)
    except ValueError as exc:
        return {"url": url, "error": str(exc)}

    output: dict[str, Any] = {"url": url}

    try:
        # Download PDF
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url, timeout=30.0) as response:
                response.raise_for_status()

                # Check content-type
                content_type = response.headers.get("content-type", "").lower()
                if "pdf" not in content_type:
                    logger.warning(
                        "pdf_download_wrong_type url=%s content_type=%s",
                        url, content_type
                    )
                    # Continue anyway, might still be a PDF

                # Stream to temp file with size check
                pdf_data = io.BytesIO()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    pdf_data.write(chunk)
                    if pdf_data.tell() > MAX_PDF_SIZE_BYTES:
                        return {
                            **output,
                            "error": f"PDF exceeds max size ({MAX_PDF_SIZE_BYTES} bytes)",
                        }

                pdf_bytes = pdf_data.getvalue()
                output["file_size_bytes"] = len(pdf_bytes)

        logger.info("pdf_downloaded url=%s size=%d", url, len(pdf_bytes))

        # Try PyPDF2 first (CPU-bound, run in executor)
        extracted_text = None
        extraction_method = None
        page_count = None

        try:
            from loom.cpu_executor import run_cpu_bound

            extracted_text, extraction_method, page_count = await run_cpu_bound(
                _extract_pdf_text_sync, pdf_bytes, start_page, end_page
            )

        except Exception as exc:
            logger.debug("cpu_executor failed for PyPDF2: %s, trying pdftotext", exc)

        # Fall back to pdftotext CLI if PyPDF2 failed
        if extracted_text is None:
            try:
                from loom.cpu_executor import run_cpu_bound

                extracted_text, extraction_method, page_count = await run_cpu_bound(
                    _extract_pdf_text_pdftotext, pdf_bytes, start_page, end_page
                )

            except Exception as exc:
                logger.error("cpu_executor failed for pdftotext: %s", exc)
                return {
                    **output,
                    "error": f"PDF extraction failed: {str(exc)[:100]}",
                }

        if extracted_text is None:
            return {
                **output,
                "error": "PDF extraction failed (PyPDF2 and pdftotext both unavailable)",
            }

        # Cap extracted text
        if len(extracted_text) > MAX_EXTRACTED_TEXT:
            extracted_text = extracted_text[:MAX_EXTRACTED_TEXT]
            logger.warning("pdf_text_truncated url=%s", url)

        output["text"] = extracted_text
        output["page_count"] = page_count or 0
        output["extraction_method"] = extraction_method or "unknown"

        # Set pages_extracted field
        if start_page is not None:
            if start_page == end_page:
                output["pages_extracted"] = str(start_page)
            else:
                output["pages_extracted"] = f"{start_page}-{end_page}"
        else:
            output["pages_extracted"] = "all"

        logger.info(
            "pdf_extract_success url=%s method=%s pages=%s",
            url, extraction_method, output["pages_extracted"]
        )

        return output

    except httpx.HTTPError as exc:
        logger.warning("pdf_download_failed url=%s: %s", url, exc)
        return {**output, "error": f"HTTP error: {exc}"}
    except Exception as exc:
        logger.exception("pdf_extract_failed url=%s", url)
        return {**output, "error": str(exc)}


@handle_tool_errors("research_pdf_search")
async def research_pdf_search(url: str, query: str) -> dict[str, Any]:
    """Search for text within a PDF.

    Downloads and extracts all pages from the PDF, then searches for the
    query string (case-insensitive).

    Args:
        url: URL to PDF file
        query: text to search for (case-insensitive)

    Returns:
        Dict with:
        - url: the input URL
        - query: the search query
        - matches: list of dicts with page number and context
        - total_matches: total count of matches
        - error: error message if search failed
    """
    try:
        validate_url(url)
    except UrlSafetyError as exc:
        return {"url": url, "query": query, "error": str(exc)}

    if not query or len(query) > 1000:
        return {
            "url": url,
            "query": query,
            "error": "query must be 1-1000 characters",
        }

    output: dict[str, Any] = {
        "url": url,
        "query": query,
        "matches": [],
        "total_matches": 0,
    }

    try:
        # Download and extract PDF
        extract_result = await research_pdf_extract(url)

        if "error" in extract_result:
            return {**output, "error": extract_result["error"]}

        text = extract_result.get("text", "")
        if not text:
            logger.warning("pdf_search_empty_text url=%s", url)
            return output

        # Search for query (case-insensitive)
        query_lower = query.lower()
        matches = []
        total_matches = 0

        # Split text into lines for context
        lines = text.split("\n")

        # Simple context window: 200 chars before and after match
        context_window = 200

        for line_idx, line in enumerate(lines):
            line_lower = line.lower()
            if query_lower in line_lower:
                # Count occurrences in this line
                count = line_lower.count(query_lower)
                total_matches += count

                # Build context: previous line + this line + next line
                context_parts = []
                if line_idx > 0:
                    context_parts.append(lines[line_idx - 1][-context_window:])
                context_parts.append(line)
                if line_idx < len(lines) - 1:
                    context_parts.append(lines[line_idx + 1][:context_window])

                context = " ... ".join(context_parts)

                # Truncate context to reasonable length
                if len(context) > 500:
                    context = context[:500] + "..."

                matches.append({
                    "line": line_idx + 1,
                    "context": context,
                    "count": count,
                })

                # Limit matches returned
                if len(matches) >= 100:
                    break

        output["matches"] = matches
        output["total_matches"] = total_matches

        logger.info(
            "pdf_search_success url=%s query=%s matches=%d",
            url, query, total_matches
        )

        return output

    except Exception as exc:
        logger.exception("pdf_search_failed url=%s query=%s", url, query)
        return {**output, "error": str(exc)}


def _parse_pages_arg(pages: str | None) -> tuple[int | None, int | None]:
    """Parse page range string into (start, end) tuple.

    Args:
        pages: page range like "1-5" or "1" or None

    Returns:
        Tuple of (start_page, end_page) or (None, None) if pages is None
        Pages are 1-indexed.

    Raises:
        ValueError: if pages format is invalid
    """
    if pages is None:
        return None, None

    pages = pages.strip()
    if not pages:
        return None, None

    # Check for range format "1-5"
    if "-" in pages:
        parts = pages.split("-")
        if len(parts) != 2:
            raise ValueError("pages format must be 'N' or 'N-M'")

        try:
            start = int(parts[0].strip())
            end = int(parts[1].strip())
        except ValueError:
            raise ValueError("pages must be integers")

        if start < 1 or end < start:
            raise ValueError("pages must be positive and start <= end")

        return start, end
    else:
        # Single page
        try:
            page = int(pages)
        except ValueError:
            raise ValueError("pages must be an integer or range")

        if page < 1:
            raise ValueError("page must be positive")

        return page, page
