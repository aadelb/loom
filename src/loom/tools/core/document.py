"""research_convert_document — Document conversion using Pandoc."""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import Any
import httpx

from loom.cli_checker import is_available
from loom.error_responses import handle_tool_errors
from loom.subprocess_helpers import run_command

logger = logging.getLogger("loom.tools.document")

# Path to pandoc executable (uses is_available for cross-platform support)
PANDOC_PATH = "pandoc"  # Will be resolved via PATH using is_available()

# Max file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Supported source formats
SUPPORTED_SOURCES = ("pdf", "docx", "doc", "html", "epub", "rtf", "odt", "tex")

# Supported output formats
SUPPORTED_OUTPUTS = ("markdown", "md", "txt", "html", "rst", "latex")


@handle_tool_errors("research_convert_document")
async def research_convert_document(
    url: str,
    output_format: str = "markdown",
) -> dict[str, Any]:
    """Convert documents (PDF, DOCX, HTML, etc.) to markdown or text.

    Uses Pandoc for format conversion. Falls back to text extraction if
    Pandoc is unavailable. Supports up to 10MB files.

    Args:
        url: document URL (PDF, DOCX, HTML, EPUB, RTF, etc.)
        output_format: target format ('markdown'/'md' or 'txt')

    Returns:
        Dict with keys:
        - content: converted document content
        - format: output format used
        - source_url: original URL
        - source_type: detected source document type
        - page_count: number of pages (if detected)
        - error: error message if conversion failed
    """
    # Normalize output format
    output_format = output_format.lower().strip()
    if output_format == "md":
        output_format = "markdown"
    if output_format not in ("markdown", "txt"):
        return {
            "error": f"Unsupported output_format: {output_format}. "
            "Supported: markdown, md, txt",
            "source_url": url,
        }

    # Validate URL
    from loom.validators import validate_url

    try:
        url = validate_url(url)
    except ValueError as e:
        return {"error": str(e), "source_url": url}

    logger.info("document_convert_start url=%s format=%s", url[:80], output_format)

    temp_file = None
    try:
        # Download document
        temp_file = await _download_document(url)
        if not temp_file:
            return {"error": "Failed to download document", "source_url": url}

        # Detect source type
        source_type = _detect_source_type(url, temp_file)

        # Convert using Pandoc
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _convert_with_pandoc,
            temp_file,
            output_format,
            source_type,
        )

        if isinstance(result, dict) and "error" in result:
            return {**result, "source_url": url, "source_type": source_type}

        return {
            "content": result.get("content"),
            "format": output_format,
            "source_url": url,
            "source_type": source_type,
            "page_count": result.get("page_count"),
        }

    except TimeoutError:
        return {"error": "Document conversion timed out", "source_url": url}
    except Exception as e:
        logger.error("document_convert_failed url=%s error=%s", url[:80], type(e).__name__)
        return {
            "error": f"Document conversion failed: {type(e).__name__}",
            "source_url": url,
        }
    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except OSError:
                pass


async def _download_document(url: str) -> str | None:
    """Download document to temp file.

    Args:
        url: document URL

    Returns:
        Path to temp file, or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Check file size
            file_size = len(response.content)
            if file_size > MAX_FILE_SIZE:
                logger.warning(
                    "document_too_large url=%s size=%d",
                    url[:80],
                    file_size,
                )
                return None

            # Determine file extension from content-type or URL
            content_type = response.headers.get("content-type", "").lower()
            suffix = _get_file_extension(url, content_type)

            # Write to temp file
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, dir=tempfile.gettempdir()
            ) as f:
                f.write(response.content)
                return f.name

    except Exception as e:
        logger.error(
            "document_download_failed url=%s error=%s",
            url[:80],
            type(e).__name__,
        )
        return None


def _detect_source_type(url: str, file_path: str) -> str:
    """Detect document source type from URL or file extension.

    Args:
        url: original document URL
        file_path: path to downloaded file

    Returns:
        Document type (pdf, docx, html, epub, rtf, etc.)
    """
    # Check file extension from URL
    url_lower = url.lower()
    for ext in SUPPORTED_SOURCES:
        if url_lower.endswith(f".{ext}"):
            return ext

    # Check file extension of saved file
    file_lower = file_path.lower()
    for ext in SUPPORTED_SOURCES:
        if file_lower.endswith(f".{ext}"):
            return ext

    # Try magic bytes
    try:
        with open(file_path, "rb") as f:
            magic = f.read(512)  # Read more for proper detection

        # PDF magic bytes
        if magic.startswith(b"%PDF"):
            return "pdf"
        # EPUB magic bytes (ZIP with "mimetype" as first entry)
        # Check before generic ZIP/DOCX since EPUB is a special ZIP variant
        if magic.startswith(b"PK\x03\x04") and b"mimetype" in magic[:100]:
            return "epub"
        # DOCX magic bytes (zip format, but not EPUB)
        if magic.startswith(b"PK\x03\x04"):
            return "docx"
        # RTF magic bytes
        if magic.startswith(b"{\\rtf"):
            return "rtf"
    except Exception:
        logger.exception("Failed to detect file type from magic bytes")
        pass

    # Default to binary
    return "binary"


def _convert_with_pandoc(
    file_path: str, output_format: str, source_type: str
) -> dict[str, Any]:
    """Convert document using Pandoc (blocking).

    Args:
        file_path: path to source document
        output_format: target format (markdown or txt)
        source_type: source document type

    Returns:
        Dict with converted content and metadata.
    """
    # Check if pandoc is available
    if not is_available("pandoc"):
        logger.warning("pandoc not found in PATH, falling back to text extraction")
        return _fallback_text_extraction(file_path)

    # Map output format to Pandoc format
    pandoc_output = "markdown" if output_format == "markdown" else "plain"

    # Validate source_type is in allowed list
    if source_type not in SUPPORTED_SOURCES and source_type != "binary":
        logger.error("invalid source_type=%s (not in allowlist)", source_type)
        return {"error": f"Invalid source type: {source_type}"}

    try:
        # Build pandoc command
        cmd = [
            "pandoc",
            f"--from={source_type}",
            f"--to={pandoc_output}",
            "--wrap=none",  # Don't rewrap lines
            file_path,
        ]

        # Run pandoc
        result = run_command(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if not result["success"]:
            logger.warning(
                "pandoc_error file=%s stderr=%s",
                file_path,
                result["stderr"][:200],
            )
            return _fallback_text_extraction(file_path)

        content = result["stdout"].strip()
        if not content:
            return {"error": "Pandoc produced empty output"}

        # Cap content size (1MB for safety)
        if len(content) > 1024 * 1024:
            content = content[:1024 * 1024]
            logger.info("document_truncated file=%s", file_path)

        return {"content": content}

    except subprocess.TimeoutExpired:
        logger.error("pandoc_timeout file=%s", file_path)
        return {"error": "Pandoc timed out"}
    except Exception as e:
        logger.error("pandoc_failed file=%s error=%s", file_path, type(e).__name__)
        return {"error": f"Pandoc failed: {type(e).__name__}"}


def _fallback_text_extraction(file_path: str) -> dict[str, Any]:
    """Fallback text extraction if Pandoc is unavailable.

    Attempts to use pdfplumber for PDFs, or falls back to basic text reading.

    Args:
        file_path: path to document file

    Returns:
        Dict with extracted text or error.
    """
    file_lower = file_path.lower()

    # Try pdfplumber for PDFs
    if file_lower.endswith(".pdf"):
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

                content = "\n\n".join(text_parts)
                return {
                    "content": content[:1024 * 1024],
                    "page_count": len(pdf.pages),
                }
        except ImportError:
            pass
        except Exception as e:
            logger.error("pdfplumber_failed file=%s error=%s", file_path, type(e).__name__)

    # Try docx for DOCX files
    if file_lower.endswith(".docx"):
        try:
            from docx import Document

            doc = Document(file_path)
            text_parts = [para.text for para in doc.paragraphs]
            content = "\n".join(text_parts)
            return {"content": content[:1024 * 1024]}
        except ImportError:
            pass
        except Exception as e:
            logger.error("docx_failed file=%s error=%s", file_path, type(e).__name__)

    # Default: try to read as text
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read(1024 * 1024)  # Read max 1MB
            if content:
                return {"content": content}
    except Exception:
        logger.exception("Failed to read document as text")
        pass

    return {"error": "Could not extract text from document"}


def _get_file_extension(url: str, content_type: str) -> str:
    """Map URL/content-type to file extension.

    Args:
        url: document URL
        content_type: HTTP content-type header

    Returns:
        File extension with leading dot.
    """
    # Check URL
    url_lower = url.lower()
    for ext in SUPPORTED_SOURCES:
        if url_lower.endswith(f".{ext}"):
            return f".{ext}"

    # Map content-type to extension
    content_type_lower = content_type.lower()

    if "pdf" in content_type_lower:
        return ".pdf"
    elif "word" in content_type_lower or "document" in content_type_lower:
        return ".docx"
    elif "html" in content_type_lower:
        return ".html"
    elif "epub" in content_type_lower:
        return ".epub"
    elif "rtf" in content_type_lower:
        return ".rtf"
    elif "odt" in content_type_lower or "opendocument" in content_type_lower:
        return ".odt"
    elif "text" in content_type_lower or "plain" in content_type_lower:
        return ".txt"
    else:
        return ".bin"
