"""Advanced document parsing tools — OCR, PDF extraction, and unified document analysis.

Uses EasyOCR for multilingual OCR and PyMuPDF for advanced PDF extraction.
"""

from __future__ import annotations

import io
import logging
import mimetypes
import os
import tempfile
import subprocess
from typing import Any

import httpx

from loom.validators import UrlSafetyError, validate_url

logger = logging.getLogger("loom.doc_parser")

# Max file size: 100 MB
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024

# Max extracted text length
MAX_EXTRACTED_TEXT = 100000


def research_ocr_advanced(
    image_path_or_url: str,
    languages: list[str] | None = None,
    detail: bool = True,
) -> dict[str, Any]:
    """Extract text from images using advanced OCR (EasyOCR).

    Supports 80+ languages with confidence scoring and bounding box detection.
    Auto-downloads images from URLs.

    Args:
        image_path_or_url: Local file path or HTTP(S) URL to image
        languages: List of language codes (e.g., ["en", "fr", "ar"])
                  Defaults to ["en"]. Supports 80+ languages.
        detail: If True, returns detailed block-level results with confidence
               and bounding boxes. If False, returns only full text.

    Returns:
        Dict with:
        - image: Input image path/URL
        - text: Full extracted text (concatenated from all blocks)
        - blocks: List of detected text blocks (if detail=True), each with:
          - text: detected text
          - confidence: confidence score (0-1)
          - bbox: bounding box coordinates (if available)
        - languages_detected: List of detected language codes
        - page_count: Always 1 for images
        - metadata: Image metadata (dimensions if available)
        - error: Error message if extraction failed
    """
    if languages is None:
        languages = ["en"]

    output: dict[str, Any] = {
        "image": image_path_or_url,
        "text": "",
        "blocks": [],
        "languages_detected": languages,
        "page_count": 1,
        "metadata": {},
    }

    try:
        # Validate if it's a URL
        is_url = image_path_or_url.startswith(("http://", "https://"))

        if is_url:
            try:
                validate_url(image_path_or_url)
            except UrlSafetyError as exc:
                return {**output, "error": str(exc)}

            # Download image from URL
            image_path = None
            try:
                with httpx.stream("GET", image_path_or_url, timeout=30.0) as response:
                    response.raise_for_status()

                    # Check content-type
                    content_type = response.headers.get("content-type", "").lower()
                    if not any(img_type in content_type for img_type in ["image", "jpeg", "png", "webp", "tiff"]):
                        logger.warning(
                            "ocr_download_wrong_type url=%s content_type=%s",
                            image_path_or_url,
                            content_type,
                        )

                    # Stream to temp file with size check
                    image_data = io.BytesIO()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        image_data.write(chunk)
                        if image_data.tell() > MAX_FILE_SIZE_BYTES:
                            return {
                                **output,
                                "error": f"Image exceeds max size ({MAX_FILE_SIZE_BYTES} bytes)",
                            }

                    image_bytes = image_data.getvalue()

                # Write to temp file
                with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tmp:
                    tmp.write(image_bytes)
                    image_path = tmp.name

                logger.info("ocr_image_downloaded url=%s size=%d", image_path_or_url, len(image_bytes))

            except httpx.HTTPError as exc:
                logger.warning("ocr_download_failed url=%s: %s", image_path_or_url, exc)
                return {**output, "error": f"HTTP error: {exc}"}
            except Exception as exc:
                logger.exception("ocr_image_download_failed url=%s", image_path_or_url)
                return {**output, "error": str(exc)}
        else:
            # Local file path
            if not os.path.exists(image_path_or_url):
                return {**output, "error": f"File not found: {image_path_or_url}"}

            if not os.path.isfile(image_path_or_url):
                return {**output, "error": f"Not a file: {image_path_or_url}"}

            image_path = image_path_or_url

        # Perform OCR using EasyOCR
        try:
            import easyocr
        except ImportError:
            logger.error("easyocr_not_installed")
            return {**output, "error": "EasyOCR not installed. Install: pip install easyocr"}

        try:
            # Initialize reader with specified languages
            reader = easyocr.Reader(languages, gpu=False)

            # Perform OCR
            results = reader.readtext(image_path)

            # Extract text and build blocks list
            text_parts = []
            blocks = []

            for detection in results:
                bbox, text, confidence = detection[0], detection[1], detection[2]

                text_parts.append(text)

                if detail:
                    block = {
                        "text": text,
                        "confidence": float(confidence),
                    }

                    # Convert bbox (list of points) to simple format
                    if bbox:
                        try:
                            bbox_list = [[float(x), float(y)] for x, y in bbox]
                            block["bbox"] = bbox_list
                        except (ValueError, TypeError):
                            pass

                    blocks.append(block)

            # Concatenate all text
            full_text = " ".join(text_parts)

            # Cap extracted text
            if len(full_text) > MAX_EXTRACTED_TEXT:
                full_text = full_text[:MAX_EXTRACTED_TEXT]
                logger.warning("ocr_text_truncated image=%s", image_path_or_url)

            output["text"] = full_text
            if detail:
                output["blocks"] = blocks

            logger.info("ocr_success image=%s languages=%s", image_path_or_url, languages)

            return output

        except Exception as exc:
            logger.exception("ocr_processing_failed image=%s", image_path_or_url)
            return {**output, "error": f"OCR processing failed: {str(exc)}"}

        finally:
            # Clean up temp file
            if is_url and image_path and os.path.exists(image_path):
                try:
                    os.unlink(image_path)
                except OSError:
                    pass

    except Exception as exc:
        logger.exception("ocr_advanced_failed image=%s", image_path_or_url)
        return {**output, "error": str(exc)}


def research_pdf_advanced(
    pdf_path_or_url: str,
    extract_images: bool = False,
    extract_tables: bool = True,
) -> dict[str, Any]:
    """Extract text, tables, metadata, and TOC from PDFs (PyMuPDF).

    Advanced PDF processing with table extraction, image counting, and
    table of contents extraction.

    Args:
        pdf_path_or_url: Local file path or HTTP(S) URL to PDF
        extract_images: If True, extracts and counts embedded images
        extract_tables: If True, extracts tables using table detection

    Returns:
        Dict with:
        - pdf: Input PDF path/URL
        - pages: Total number of pages
        - text: Full extracted text from all pages
        - tables: List of extracted tables (if extract_tables=True), each with:
          - page: page number (1-indexed)
          - data: table rows (list of lists)
        - images_count: Number of embedded images (if extract_images=True)
        - metadata: PDF metadata dict with author, title, creation_date, etc.
        - toc: Table of contents as list of dicts with title and page
        - extraction_method: "pymupdf" or "pdftotext"
        - file_size_bytes: Downloaded file size
        - error: Error message if extraction failed
    """
    output: dict[str, Any] = {
        "pdf": pdf_path_or_url,
        "pages": 0,
        "text": "",
        "tables": [],
        "images_count": 0,
        "metadata": {},
        "toc": [],
    }

    try:
        # Validate if it's a URL
        is_url = pdf_path_or_url.startswith(("http://", "https://"))

        if is_url:
            try:
                validate_url(pdf_path_or_url)
            except UrlSafetyError as exc:
                return {**output, "error": str(exc)}

            # Download PDF from URL
            pdf_path = None
            try:
                with httpx.stream("GET", pdf_path_or_url, timeout=30.0) as response:
                    response.raise_for_status()

                    # Check content-type
                    content_type = response.headers.get("content-type", "").lower()
                    if "pdf" not in content_type:
                        logger.warning(
                            "pdf_advanced_download_wrong_type url=%s content_type=%s",
                            pdf_path_or_url,
                            content_type,
                        )

                    # Stream to temp file with size check
                    pdf_data = io.BytesIO()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        pdf_data.write(chunk)
                        if pdf_data.tell() > MAX_FILE_SIZE_BYTES:
                            return {
                                **output,
                                "error": f"PDF exceeds max size ({MAX_FILE_SIZE_BYTES} bytes)",
                            }

                    pdf_bytes = pdf_data.getvalue()
                    output["file_size_bytes"] = len(pdf_bytes)

                # Write to temp file
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(pdf_bytes)
                    pdf_path = tmp.name

                logger.info("pdf_advanced_downloaded url=%s size=%d", pdf_path_or_url, len(pdf_bytes))

            except httpx.HTTPError as exc:
                logger.warning("pdf_advanced_download_failed url=%s: %s", pdf_path_or_url, exc)
                return {**output, "error": f"HTTP error: {exc}"}
            except Exception as exc:
                logger.exception("pdf_advanced_download_failed url=%s", pdf_path_or_url)
                return {**output, "error": str(exc)}
        else:
            # Local file path
            if not os.path.exists(pdf_path_or_url):
                return {**output, "error": f"File not found: {pdf_path_or_url}"}

            if not os.path.isfile(pdf_path_or_url):
                return {**output, "error": f"Not a file: {pdf_path_or_url}"}

            pdf_path = pdf_path_or_url
            output["file_size_bytes"] = os.path.getsize(pdf_path)

        # Try PyMuPDF first
        extracted_text = None
        extraction_method = None
        page_count = None
        metadata_dict = {}
        toc_list = []
        tables_list = []
        images_count = 0

        try:
            import fitz  # PyMuPDF

            # Open PDF document
            doc = fitz.open(pdf_path)
            page_count = len(doc)

            # Extract metadata
            try:
                meta = doc.metadata
                if meta:
                    metadata_dict = {
                        "author": meta.get("author"),
                        "title": meta.get("title"),
                        "subject": meta.get("subject"),
                        "creator": meta.get("creator"),
                        "producer": meta.get("producer"),
                        "creation_date": str(meta.get("creationDate", "")),
                        "modification_date": str(meta.get("modDate", "")),
                    }
            except Exception as exc:
                logger.debug("pdf_metadata_extraction_failed: %s", exc)

            # Extract table of contents
            try:
                toc = doc.get_toc()
                if toc:
                    for item in toc:
                        level, title, page = item[0], item[1], item[2]
                        toc_list.append({
                            "level": level,
                            "title": title,
                            "page": page,
                        })
            except Exception as exc:
                logger.debug("pdf_toc_extraction_failed: %s", exc)

            # Extract text and tables page by page
            text_parts = []

            for page_num in range(page_count):
                page = doc[page_num]

                # Extract text from page
                try:
                    text = page.get_text()
                    if text:
                        text_parts.append(text)
                except Exception as exc:
                    logger.debug("pdf_page_text_extraction_failed page=%d: %s", page_num, exc)

                # Extract tables if requested
                if extract_tables:
                    try:
                        tables = page.find_tables()
                        if tables:
                            for table in tables:
                                try:
                                    table_data = table.extract()
                                    if table_data:
                                        tables_list.append({
                                            "page": page_num + 1,
                                            "data": table_data,
                                        })
                                except Exception as exc:
                                    logger.debug("pdf_table_extraction_failed page=%d: %s", page_num, exc)
                    except Exception as exc:
                        logger.debug("pdf_tables_search_failed page=%d: %s", page_num, exc)

                # Count images if requested
                if extract_images:
                    try:
                        image_list = page.get_images()
                        if image_list:
                            images_count += len(image_list)
                    except Exception as exc:
                        logger.debug("pdf_images_count_failed page=%d: %s", page_num, exc)

            extracted_text = "\n".join(text_parts)
            extraction_method = "pymupdf"

            doc.close()

            logger.info(
                "pdf_advanced_extraction_success url=%s pages=%d tables=%d",
                pdf_path_or_url,
                page_count,
                len(tables_list),
            )

        except ImportError:
            logger.debug("PyMuPDF not available, falling back to pdftotext")
        except Exception as exc:
            logger.debug("PyMuPDF extraction failed: %s", exc)

        # Fall back to pdftotext CLI
        if extracted_text is None:

            try:
                cmd = ["pdftotext", pdf_path, "-"]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    logger.warning(
                        "pdftotext_failed url=%s returncode=%d",
                        pdf_path_or_url,
                        result.returncode,
                    )
                    return {
                        **output,
                        "error": f"pdftotext failed: {result.stderr}",
                    }

                extracted_text = result.stdout
                extraction_method = "pdftotext"

                # pdftotext doesn't give us page count or tables
                page_count = page_count or 0

                logger.info("pdf_advanced_extraction_pdftotext_success url=%s", pdf_path_or_url)

            except FileNotFoundError:
                logger.error("pdftotext_not_found")
                return {
                    **output,
                    "error": "pdftotext command not found (install poppler-utils)",
                }
            except subprocess.TimeoutExpired:
                logger.warning("pdftotext_timeout url=%s", pdf_path_or_url)
                return {**output, "error": "pdftotext command timed out (>30s)"}
            except Exception as exc:
                logger.exception("pdf_advanced_extraction_failed url=%s", pdf_path_or_url)
                return {**output, "error": str(exc)}

        # Cap extracted text
        if len(extracted_text) > MAX_EXTRACTED_TEXT:
            extracted_text = extracted_text[:MAX_EXTRACTED_TEXT]
            logger.warning("pdf_text_truncated url=%s", pdf_path_or_url)

        output["text"] = extracted_text
        output["pages"] = page_count or 0
        output["extraction_method"] = extraction_method or "unknown"
        output["metadata"] = metadata_dict
        output["toc"] = toc_list
        if extract_tables:
            output["tables"] = tables_list
        if extract_images:
            output["images_count"] = images_count

        logger.info(
            "pdf_advanced_success url=%s method=%s pages=%s",
            pdf_path_or_url,
            extraction_method,
            page_count,
        )

        return output

    except Exception as exc:
        logger.exception("pdf_advanced_failed url=%s", pdf_path_or_url)
        return {**output, "error": str(exc)}

    finally:
        # Clean up temp file
        if is_url and pdf_path and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except OSError:
                pass


def research_document_analyze(
    file_path_or_url: str,
    analysis: str = "full",
) -> dict[str, Any]:
    """Unified document analysis — auto-detects file type and applies appropriate parser.

    Automatically detects PDF vs. image and calls the appropriate parser.
    Supports OCR for images and advanced extraction for PDFs.

    Args:
        file_path_or_url: Local file path or HTTP(S) URL to document
        analysis: Analysis level - "full" (all features), "text" (text only),
                 or "fast" (no tables/images)

    Returns:
        Dict with:
        - file_path: Input file path/URL
        - file_type: Detected type ("pdf" or "image")
        - text: Extracted text from document
        - page_count: Page count (for PDFs) or 1 (for images)
        - metadata: Document metadata (for PDFs)
        - tables: Extracted tables (if PDF and analysis != "text")
        - ocr_text: Extracted text via OCR (for images)
        - languages_detected: Detected languages (for images)
        - extraction_method: Method used ("pymupdf", "pdftotext", "easyocr")
        - error: Error message if analysis failed
    """
    output: dict[str, Any] = {
        "file_path": file_path_or_url,
        "file_type": "unknown",
        "text": "",
        "page_count": 0,
        "metadata": {},
        "tables": [],
        "extraction_method": "unknown",
    }

    try:
        # Determine file type
        is_url = file_path_or_url.startswith(("http://", "https://"))
        file_type = "unknown"

        if is_url:
            # For URLs, try to guess from URL or headers
            try:
                validate_url(file_path_or_url)
            except UrlSafetyError as exc:
                return {**output, "error": str(exc)}

            # Check if URL ends with .pdf
            if file_path_or_url.lower().endswith(".pdf"):
                file_type = "pdf"
            else:
                # Fetch headers to check content-type
                try:
                    with httpx.head(file_path_or_url, timeout=10.0) as response:
                        content_type = response.headers.get("content-type", "").lower()

                        if "pdf" in content_type:
                            file_type = "pdf"
                        elif "image" in content_type or any(
                            img_type in content_type for img_type in ["jpeg", "png", "webp", "tiff"]
                        ):
                            file_type = "image"
                        else:
                            # Default to trying PDF
                            file_type = "pdf"
                except Exception as exc:
                    logger.debug("document_analyze_content_type_check_failed: %s", exc)
                    file_type = "pdf"
        else:
            # Local file — use extension and MIME type
            _, ext = os.path.splitext(file_path_or_url)
            ext = ext.lower()

            if ext == ".pdf":
                file_type = "pdf"
            elif ext in [".png", ".jpg", ".jpeg", ".webp", ".tiff", ".gif", ".bmp"]:
                file_type = "image"
            else:
                # Try MIME type
                mime_type, _ = mimetypes.guess_type(file_path_or_url)
                if mime_type:
                    if "pdf" in mime_type:
                        file_type = "pdf"
                    elif "image" in mime_type:
                        file_type = "image"

                if file_type == "unknown":
                    return {**output, "error": f"Unknown file type: {ext or file_path_or_url}"}

        output["file_type"] = file_type

        # Apply appropriate parser
        if file_type == "pdf":
            extract_tables = analysis != "text"
            extract_images = analysis == "full"

            result = research_pdf_advanced(
                file_path_or_url,
                extract_images=extract_images,
                extract_tables=extract_tables,
            )

            if "error" in result:
                return {**output, "error": result["error"]}

            output["text"] = result.get("text", "")
            output["page_count"] = result.get("pages", 0)
            output["metadata"] = result.get("metadata", {})
            output["extraction_method"] = result.get("extraction_method", "unknown")

            if analysis != "text":
                output["tables"] = result.get("tables", [])

            if analysis == "full":
                output["images_count"] = result.get("images_count", 0)

        elif file_type == "image":
            detail = analysis != "text"

            result = research_ocr_advanced(
                file_path_or_url,
                languages=["en"],
                detail=detail,
            )

            if "error" in result:
                return {**output, "error": result["error"]}

            output["text"] = result.get("text", "")
            output["ocr_text"] = result.get("text", "")
            output["page_count"] = 1
            output["languages_detected"] = result.get("languages_detected", [])
            output["extraction_method"] = "easyocr"

            if detail:
                output["blocks"] = result.get("blocks", [])

        logger.info(
            "document_analyze_success file_path=%s type=%s",
            file_path_or_url,
            file_type,
        )

        return output

    except Exception as exc:
        logger.exception("document_analyze_failed file_path=%s", file_path_or_url)
        return {**output, "error": str(exc)}
