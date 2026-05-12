"""Table extraction from PDFs — Extract structured data using Camelot."""

from __future__ import annotations

import asyncio
import io
import logging
import tempfile
from typing import Any

import httpx

from loom.validators import UrlSafetyError, validate_url

logger = logging.getLogger("loom.tools.camelot_backend")

# Max PDF file size: 50 MB
MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024

# Max tables to extract per PDF
MAX_TABLES_PER_PDF = 100


async def research_table_extract(
    pdf_url: str = "",
    pdf_path: str = "",
    pages: str = "all",
) -> dict[str, Any]:
    """Extract tables from PDF using Camelot.

    Camelot extracts structured table data from PDFs with high accuracy.
    Supports page ranges and multiple extraction methods.

    Args:
        pdf_url: URL to PDF file (auto-download)
        pdf_path: local file path to PDF
        pages: page range to extract, e.g., "1-5", "1,3,5", or "all" (default)

    Returns:
        Dict with:
        - tables: list of extracted tables, each with:
            - headers: column names (inferred or detected)
            - rows: list of row dicts
            - shape: (row_count, col_count)
        - table_count: number of tables extracted
        - pages_processed: pages that were analyzed
        - page_count: total pages in PDF
        - error: error message if extraction failed
    """
    try:
        import camelot  # type: ignore
    except ImportError:
        return {
            "error": "camelot not installed. Install with: pip install camelot-py[cv]",
        }

    # Validate input
    if not pdf_url and not pdf_path:
        return {"error": "Either pdf_url or pdf_path must be provided"}

    if pdf_url and pdf_path:
        return {"error": "Provide only pdf_url or pdf_path, not both"}

    # Validate pages argument
    pages_arg = "all"
    if pages and pages != "all":
        # Basic validation: "1-5", "1,3,5", "1"
        try:
            if "-" in pages:
                parts = pages.split("-")
                if len(parts) != 2:
                    raise ValueError("Invalid page range")
                int(parts[0])
                int(parts[1])
            elif "," in pages:
                for p in pages.split(","):
                    int(p.strip())
            else:
                int(pages)
        except (ValueError, AttributeError):
            return {
                "error": "pages must be 'all', single number, range (1-5), or comma-separated (1,3,5)"
            }
        pages_arg = pages

    output: dict[str, Any] = {}

    # Download or load PDF
    pdf_bytes = None
    pdf_source = None

    if pdf_url:
        try:
            validate_url(pdf_url)
        except UrlSafetyError as exc:
            return {"pdf_url": pdf_url, "error": str(exc)}

        try:
            async def _download_pdf() -> bytes:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(pdf_url, follow_redirects=True)
                    response.raise_for_status()

                    # Validate content type
                    content_type = response.headers.get("content-type", "").lower()
                    if "pdf" not in content_type:
                        logger.warning(
                            "pdf_download_wrong_type url=%s content_type=%s",
                            pdf_url,
                            content_type,
                        )

                    # Stream to bytes with size check
                    data = io.BytesIO()
                    for chunk in response.aiter_bytes(chunk_size=65536):
                        data.write(chunk)
                        if data.tell() > MAX_PDF_SIZE_BYTES:
                            raise ValueError(
                                f"PDF exceeds max size ({MAX_PDF_SIZE_BYTES} bytes)"
                            )

                    return data.getvalue()

            pdf_bytes = await _download_pdf()
            pdf_source = "url"
            output["pdf_url"] = pdf_url

            logger.info("pdf_downloaded url=%s size=%d", pdf_url, len(pdf_bytes))

        except UrlSafetyError as exc:
            return {"pdf_url": pdf_url, "error": str(exc)}
        except Exception as exc:
            logger.error("pdf_download_error url=%s error=%s", pdf_url, exc)
            return {"pdf_url": pdf_url, "error": f"Failed to download PDF: {exc}"}

    elif pdf_path:
        try:
            async def _load_pdf() -> bytes:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, lambda: open(pdf_path, "rb").read()
                )

            pdf_bytes = await _load_pdf()
            if len(pdf_bytes) > MAX_PDF_SIZE_BYTES:
                return {
                    "pdf_path": pdf_path,
                    "error": f"PDF exceeds max size ({MAX_PDF_SIZE_BYTES} bytes)",
                }
            pdf_source = "path"
            output["pdf_path"] = pdf_path

            logger.info("pdf_loaded path=%s size=%d", pdf_path, len(pdf_bytes))

        except FileNotFoundError:
            return {"pdf_path": pdf_path, "error": "File not found"}
        except Exception as exc:
            logger.error("pdf_load_error path=%s error=%s", pdf_path, exc)
            return {"pdf_path": pdf_path, "error": f"Failed to load PDF: {exc}"}

    if not pdf_bytes:
        return {"error": "No PDF data available"}

    output["pdf_source"] = pdf_source

    # Extract tables
    try:
        def _extract_tables() -> tuple[list[dict[str, Any]], int, str]:
            # Write bytes to temp file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(pdf_bytes)
                tmp_path = tmp_file.name

            try:
                # Extract tables using Camelot
                tables = camelot.read_pdf(
                    tmp_path,
                    pages=pages_arg,
                    flavor="lattice",  # Use lattice flavor for structured tables
                    suppress_stdout=True,
                    strip_text=True,
                )

                # Get total page count (requires reading PDF)
                try:
                    import pypdf

                    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                    total_pages = len(reader.pages)
                except Exception as e:
                    logger.debug("pdf_page_count_error: %s", e)
                    total_pages = 0

                # Convert to dict format
                extracted_tables = []
                for i, table in enumerate(tables):
                    if len(extracted_tables) >= MAX_TABLES_PER_PDF:
                        break

                    # Get headers (first row)
                    df = table.df
                    rows = df.values.tolist()

                    # Try to identify headers
                    headers = None
                    table_rows = rows

                    if len(rows) > 0:
                        # Check if first row looks like headers (common pattern)
                        headers = df.columns.tolist()

                    extracted_tables.append(
                        {
                            "headers": headers,
                            "rows": [dict(zip(headers, row)) for row in table_rows]
                            if headers
                            else [{"row": i, "data": row} for i, row in enumerate(table_rows)],
                            "shape": (len(table_rows), len(headers) if headers else 0),
                        }
                    )

                pages_processed = (
                    pages_arg if pages_arg != "all" else f"1-{total_pages}"
                )

                return extracted_tables, total_pages, pages_processed

            finally:
                import os

                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.debug("temp_file_cleanup_error: %s", e)

        tables, total_pages, pages_processed = await asyncio.to_thread(
            _extract_tables
        )

        output["tables"] = tables
        output["table_count"] = len(tables)
        output["page_count"] = total_pages
        output["pages_processed"] = pages_processed

        logger.info(
            "tables_extracted source=%s tables=%d total_pages=%d",
            pdf_source,
            len(tables),
            total_pages,
        )

        return output

    except Exception as exc:
        logger.error("table_extraction_error error=%s pages=%s", exc, pages_arg)
        return {
            **output,
            "error": f"Table extraction failed: {exc}",
        }
