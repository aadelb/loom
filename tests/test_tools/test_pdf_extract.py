"""Unit tests for PDF extraction tools."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from loom.tools.pdf_extract import (
    _parse_pages_arg,
    research_pdf_extract,
    research_pdf_search,
)
from loom.validators import validate_url as _validate_url


class TestValidateUrl:
    """URL validation for PDF extraction."""

    def test_valid_https_url(self) -> None:
        """Valid HTTPS URLs pass validation."""
        url = "https://example.com/document.pdf"
        assert _validate_url(url) == url

    def test_valid_http_url(self) -> None:
        """Valid HTTP URLs pass validation."""
        url = "http://example.com/document.pdf"
        assert _validate_url(url) == url

    def test_url_missing_scheme(self) -> None:
        """URLs without http(s) scheme raise error."""
        with pytest.raises(ValueError, match="scheme"):
            _validate_url("ftp://example.com/file.pdf")

    def test_url_missing_hostname(self) -> None:
        """URLs without hostname raise error."""
        with pytest.raises(ValueError, match="hostname"):
            _validate_url("https://")

    def test_url_too_long(self) -> None:
        """URLs exceeding 4096 chars raise error."""
        long_url = "https://example.com/" + "a" * 4100
        with pytest.raises(ValueError, match="too long"):
            _validate_url(long_url)

    def test_url_empty(self) -> None:
        """Empty URL raises error."""
        with pytest.raises(ValueError, match="scheme"):
            _validate_url("")


class TestParsePagesArg:
    """Page range argument parsing."""

    def test_parse_none(self) -> None:
        """None returns (None, None)."""
        assert _parse_pages_arg(None) == (None, None)

    def test_parse_empty_string(self) -> None:
        """Empty string returns (None, None)."""
        assert _parse_pages_arg("") == (None, None)

    def test_parse_single_page(self) -> None:
        """Single page number returns (page, page)."""
        assert _parse_pages_arg("5") == (5, 5)

    def test_parse_page_range(self) -> None:
        """Page range returns (start, end)."""
        assert _parse_pages_arg("1-10") == (1, 10)
        assert _parse_pages_arg("2-5") == (2, 5)

    def test_parse_invalid_range(self) -> None:
        """Invalid range format raises error."""
        with pytest.raises(ValueError):
            _parse_pages_arg("1-2-3")

    def test_parse_non_integer(self) -> None:
        """Non-integer pages raise error."""
        with pytest.raises(ValueError):
            _parse_pages_arg("abc")

    def test_parse_negative_page(self) -> None:
        """Negative page numbers raise error."""
        with pytest.raises(ValueError):
            _parse_pages_arg("-1")

    def test_parse_inverted_range(self) -> None:
        """Range with end < start raises error."""
        with pytest.raises(ValueError):
            _parse_pages_arg("10-1")


class TestPdfExtract:
    """research_pdf_extract with multiple backends."""

    @patch("httpx.stream")
    def test_extract_valid_pdf_pypdf2(self, mock_stream) -> None:
        """Extract PDF using PyPDF2 backend."""
        # Mock PDF response
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.iter_bytes.return_value = [b"%PDF-1.0\n", b"mock pdf data"]
        mock_response.headers.get.return_value = "application/pdf"
        mock_stream.return_value = mock_response

        with patch("PyPDF2.PdfReader") as mock_reader:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Test PDF content"
            mock_pdf.pages = [mock_page]
            mock_reader.return_value = mock_pdf

            result = research_pdf_extract(
                "https://example.com/document.pdf"
            )

            assert result["url"] == "https://example.com/document.pdf"
            assert "Test PDF content" in result.get("text", "")
            assert result["extraction_method"] == "pypdf2"

    @patch("httpx.stream")
    def test_extract_invalid_url(self, mock_stream) -> None:
        """Extract with invalid URL returns error."""
        result = research_pdf_extract("invalid@url")

        assert "error" in result

    @patch("httpx.stream")
    def test_extract_http_error(self, mock_stream) -> None:
        """HTTP errors return error."""
        import httpx

        mock_stream.side_effect = httpx.HTTPError("Connection failed")

        result = research_pdf_extract("https://example.com/notfound.pdf")

        assert "error" in result

    @patch("httpx.stream")
    def test_extract_oversized_pdf(self, mock_stream) -> None:
        """PDFs exceeding size limit return error."""
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        # Simulate large file
        mock_response.iter_bytes.return_value = [b"x" * (51 * 1024 * 1024)]
        mock_stream.return_value = mock_response

        result = research_pdf_extract("https://example.com/huge.pdf")

        assert "error" in result
        assert "exceeds max size" in result["error"]

    @patch("httpx.stream")
    def test_extract_text_truncation(self, mock_stream) -> None:
        """Extracted text is truncated to 50000 chars."""
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.iter_bytes.return_value = [b"%PDF-1.0\n"]
        mock_response.headers.get.return_value = "application/pdf"
        mock_stream.return_value = mock_response

        with patch("PyPDF2.PdfReader") as mock_reader:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            long_text = "x" * 100000
            mock_page.extract_text.return_value = long_text
            mock_pdf.pages = [mock_page]
            mock_reader.return_value = mock_pdf

            result = research_pdf_extract(
                "https://example.com/document.pdf"
            )

            assert len(result["text"]) <= 50000

    @patch("httpx.stream")
    def test_extract_with_page_range(self, mock_stream) -> None:
        """Extract specific page range."""
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.iter_bytes.return_value = [b"%PDF-1.0\n"]
        mock_response.headers.get.return_value = "application/pdf"
        mock_stream.return_value = mock_response

        with patch("PyPDF2.PdfReader") as mock_reader:
            mock_pdf = MagicMock()
            pages = [MagicMock() for _ in range(5)]
            for i, page in enumerate(pages):
                page.extract_text.return_value = f"Page {i+1}"
            mock_pdf.pages = pages
            mock_reader.return_value = mock_pdf

            result = research_pdf_extract(
                "https://example.com/document.pdf",
                pages="1-3"
            )

            assert result["pages_extracted"] == "1-3"
            assert "Page 1" in result["text"]


class TestPdfSearch:
    """research_pdf_search within PDF content."""

    @patch("httpx.stream")
    def test_search_found_matches(self, mock_stream) -> None:
        """Search returns matching lines with context."""
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.iter_bytes.return_value = [b"%PDF-1.0\n"]
        mock_response.headers.get.return_value = "application/pdf"
        mock_stream.return_value = mock_response

        with patch("PyPDF2.PdfReader") as mock_reader:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = (
                "First line about example\n"
                "Second line with EXAMPLE text\n"
                "Third line\n"
                "Another example here\n"
            )
            mock_pdf.pages = [mock_page]
            mock_reader.return_value = mock_pdf

            result = research_pdf_search(
                "https://example.com/document.pdf",
                "example"
            )

            assert result["url"] == "https://example.com/document.pdf"
            assert result["query"] == "example"
            assert result["total_matches"] >= 3
            assert len(result["matches"]) > 0
            assert "context" in result["matches"][0]

    @patch("httpx.stream")
    def test_search_no_matches(self, mock_stream) -> None:
        """Search with no matches returns empty results."""
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.iter_bytes.return_value = [b"%PDF-1.0\n"]
        mock_response.headers.get.return_value = "application/pdf"
        mock_stream.return_value = mock_response

        with patch("PyPDF2.PdfReader") as mock_reader:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Some random text here"
            mock_pdf.pages = [mock_page]
            mock_reader.return_value = mock_pdf

            result = research_pdf_search(
                "https://example.com/document.pdf",
                "notfound"
            )

            assert result["total_matches"] == 0
            assert len(result["matches"]) == 0

    def test_search_invalid_url(self) -> None:
        """Search with invalid URL returns error."""
        result = research_pdf_search("invalid@url", "query")

        assert "error" in result

    def test_search_empty_query(self) -> None:
        """Search with empty query returns error."""
        result = research_pdf_search("https://example.com/doc.pdf", "")

        assert "error" in result

    def test_search_query_too_long(self) -> None:
        """Search query exceeding 1000 chars returns error."""
        result = research_pdf_search(
            "https://example.com/doc.pdf",
            "x" * 1001
        )

        assert "error" in result

    @patch("httpx.stream")
    def test_search_case_insensitive(self, mock_stream) -> None:
        """Search is case-insensitive."""
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.iter_bytes.return_value = [b"%PDF-1.0\n"]
        mock_response.headers.get.return_value = "application/pdf"
        mock_stream.return_value = mock_response

        with patch("PyPDF2.PdfReader") as mock_reader:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "UPPER case and lowercase text"
            mock_pdf.pages = [mock_page]
            mock_reader.return_value = mock_pdf

            result = research_pdf_search(
                "https://example.com/document.pdf",
                "case"
            )

            assert result["total_matches"] > 0

    @patch("httpx.stream")
    def test_search_context_truncation(self, mock_stream) -> None:
        """Search context is truncated to reasonable length."""
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.iter_bytes.return_value = [b"%PDF-1.0\n"]
        mock_response.headers.get.return_value = "application/pdf"
        mock_stream.return_value = mock_response

        with patch("PyPDF2.PdfReader") as mock_reader:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            long_line = "a" * 1000 + " test " + "b" * 1000
            mock_page.extract_text.return_value = long_line
            mock_pdf.pages = [mock_page]
            mock_reader.return_value = mock_pdf

            result = research_pdf_search(
                "https://example.com/document.pdf",
                "test"
            )

            if result["matches"]:
                # Allow up to 550 for context joining overhead (" ... " separators)
                assert len(result["matches"][0]["context"]) <= 550
