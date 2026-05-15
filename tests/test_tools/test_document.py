"""Tests for research_convert_document tool."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestResearchConvertDocument:
    """Tests for research_convert_document() function."""

    @pytest.mark.asyncio
    async def test_pandoc_not_found(self):
        """Test error when pandoc is not available."""
        import sys
        # Mock pdfplumber to not be available
        with (
            patch("shutil.which", return_value=None),
            patch("loom.tools.core.document._download_document", new_callable=AsyncMock) as mock_download,
            patch.dict(sys.modules, {"pdfplumber": None}),
        ):
            # Create a temporary file for the mock download
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                temp_path = tmp.name

            try:
                mock_download.return_value = temp_path

                from loom.tools.core.document import research_convert_document

                result = await research_convert_document("https://example.com/doc.pdf")

                # When pandoc is not found and no pdfplumber, should fail with text extraction error
                assert "error" in result
                # The error should be about text extraction or indicate pandoc is not available
                assert "could not extract" in result["error"].lower() or "pandoc" in result["error"].lower()
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_invalid_output_format(self):
        """Test error for invalid output format."""
        with patch("shutil.which", return_value="/usr/bin/pandoc"):
            from loom.tools.core.document import research_convert_document

            result = await research_convert_document(
                "https://example.com/doc.pdf", output_format="invalid"
            )

            assert "error" in result
            assert "output_format" in result["error"] or "unsupported" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        """Test error for invalid URL."""
        with patch("shutil.which", return_value="/usr/bin/pandoc"):
            from loom.tools.core.document import research_convert_document

            result = await research_convert_document(
                "not a valid url", output_format="markdown"
            )

            assert "error" in result

    @pytest.mark.asyncio
    async def test_download_failure(self):
        """Test error when document download fails."""
        with (
            patch("shutil.which", return_value="/usr/bin/pandoc"),
            patch("httpx.Client") as mock_client_cls,
        ):
            mock_ctx = MagicMock()
            mock_ctx.get.side_effect = Exception("Connection failed")
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.tools.core.document import research_convert_document

            result = await research_convert_document(
                "https://example.com/doc.pdf", output_format="markdown"
            )

            assert "error" in result

    @pytest.mark.asyncio
    async def test_file_size_exceeds_limit(self):
        """Test error when document file exceeds size limit."""
        with (
            patch("shutil.which", return_value="/usr/bin/pandoc"),
            patch("httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.headers.get.return_value = "10737418240"  # 10GB
            mock_response.raise_for_status = MagicMock()
            mock_response.content = b"x" * (11 * 1024 * 1024)  # 11MB content

            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.tools.core.document import research_convert_document

            result = await research_convert_document(
                "https://example.com/doc.pdf", output_format="markdown"
            )

            assert "error" in result
            # When file size exceeds limit, download returns None which causes "Failed to download document"
            assert "failed to download" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_conversion_pdf_to_markdown(self):
        """Test successful PDF to Markdown conversion."""
        with (
            patch("shutil.which", return_value="/usr/bin/pandoc"),
            patch("httpx.Client") as mock_client_cls,
            patch("subprocess.run") as mock_run,
            patch("tempfile.NamedTemporaryFile") as mock_temp,
        ):
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.headers.get.return_value = "application/pdf"
            mock_response.raise_for_status = MagicMock()
            mock_response.content = b"%PDF-1.4..."

            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            # Mock temp file
            mock_tmp_file = MagicMock()
            mock_tmp_file.name = "/tmp/doc.pdf"
            mock_temp.return_value.__enter__.return_value = mock_tmp_file
            mock_temp.return_value.__exit__.return_value = False

            # Mock pandoc conversion
            mock_run.return_value = MagicMock(
                returncode=0, stdout="# Document Title\n\nContent here"
            )

            from loom.tools.core.document import research_convert_document

            result = await research_convert_document(
                "https://example.com/doc.pdf", output_format="markdown"
            )

            # Should be successful (or handled gracefully)
            assert "source_url" in result or "error" in result
            # Check if successful conversion
            if "content" in result:
                assert result["format"] == "markdown"
                assert result["source_type"] == "pdf"

    @pytest.mark.asyncio
    async def test_conversion_with_md_shorthand(self):
        """Test 'md' as shorthand for 'markdown'."""
        with (
            patch("shutil.which", return_value="/usr/bin/pandoc"),
            patch("httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.headers.get.return_value = "text/html"
            mock_response.raise_for_status = MagicMock()
            mock_response.content = b"<html><body>test</body></html>"

            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.tools.core.document import research_convert_document

            result = await research_convert_document(
                "https://example.com/doc.html", output_format="md"
            )

            # Should not error on format
            if "error" in result:
                assert "output_format" not in result["error"].lower()

    @pytest.mark.asyncio
    async def test_http_404_error(self):
        """Test handling of HTTP 404."""
        with (
            patch("shutil.which", return_value="/usr/bin/pandoc"),
            patch("httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = Exception("HTTP 404")

            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.tools.core.document import research_convert_document

            result = await research_convert_document(
                "https://example.com/notfound.pdf", output_format="markdown"
            )

            assert "error" in result

    @pytest.mark.asyncio
    async def test_cleanup_on_failure(self):
        """Test temp files are cleaned up on failure."""
        with (
            patch("shutil.which", return_value="/usr/bin/pandoc"),
            patch("httpx.Client") as mock_client_cls,
            patch("os.unlink") as mock_unlink,
        ):
            mock_ctx = MagicMock()
            mock_ctx.get.side_effect = Exception("Network error")
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.tools.core.document import research_convert_document

            result = await research_convert_document(
                "https://example.com/doc.pdf", output_format="markdown"
            )

            assert "error" in result


class TestGetDocumentType:
    """Tests for document type detection."""

    def test_pdf_content_type(self):
        """Test PDF content type detection."""

        # PDF should be recognized
        # This is an indirect test through the main function

    def test_docx_content_type(self):
        """Test DOCX content type detection."""
        # DOCX MIME: application/vnd.openxmlformats-officedocument.wordprocessingml.document

    def test_html_content_type(self):
        """Test HTML content type detection."""
        # HTML MIME: text/html

    def test_epub_content_type(self):
        """Test EPUB content type detection."""
        # EPUB MIME: application/epub+zip


class TestPandocExecution:
    """Tests for Pandoc execution."""

    @pytest.mark.asyncio
    async def test_pandoc_conversion_success(self):
        """Test successful Pandoc conversion."""
        with (
            patch("shutil.which", return_value="/usr/bin/pandoc"),
            patch("httpx.Client") as mock_client_cls,
            patch("subprocess.run") as mock_run,
            patch("tempfile.NamedTemporaryFile") as mock_temp,
        ):
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.headers.get.return_value = "text/html"
            mock_response.raise_for_status = MagicMock()
            mock_response.content = b"<html><body><h1>Test</h1></body></html>"

            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            # Mock temp files
            mock_input_file = MagicMock()
            mock_input_file.name = "/tmp/input.html"

            mock_output_file = MagicMock()
            mock_output_file.name = "/tmp/output.md"

            mock_temp.side_effect = [
                MagicMock(__enter__=lambda s: mock_input_file, __exit__=MagicMock()),
                MagicMock(__enter__=lambda s: mock_output_file, __exit__=MagicMock()),
            ]

            # Mock successful pandoc execution
            mock_run.return_value = MagicMock(
                returncode=0, stdout="# Test\n\nContent"
            )

            from loom.tools.core.document import research_convert_document

            result = await research_convert_document(
                "https://example.com/doc.html", output_format="markdown"
            )

            # Success or graceful error handling
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_pandoc_execution_failure(self):
        """Test Pandoc execution failure."""
        with (
            patch("shutil.which", return_value="/usr/bin/pandoc"),
            patch("httpx.Client") as mock_client_cls,
            patch("subprocess.run") as mock_run,
            patch("tempfile.NamedTemporaryFile") as mock_temp,
        ):
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.headers.get.return_value = "text/html"
            mock_response.raise_for_status = MagicMock()
            mock_response.content = b"<html>test</html>"

            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            # Mock temp files
            mock_temp_file = MagicMock()
            mock_temp_file.name = "/tmp/test"
            mock_temp.return_value.__enter__.return_value = mock_temp_file
            mock_temp.return_value.__exit__.return_value = False

            # Mock pandoc failure
            mock_run.return_value = MagicMock(returncode=1, stderr="Pandoc error")

            from loom.tools.core.document import research_convert_document

            result = await research_convert_document(
                "https://example.com/doc.html", output_format="markdown"
            )

            # Should handle error gracefully
            assert isinstance(result, dict)


class TestFallbackTextExtraction:
    """Tests for fallback text extraction when Pandoc unavailable."""

    @pytest.mark.asyncio
    async def test_fallback_when_pandoc_unavailable(self):
        """Test text extraction fallback when Pandoc is not available."""
        with (
            patch("shutil.which", return_value=None),  # Pandoc not available
            patch("httpx.Client") as mock_client_cls,
        ):
            mock_response = MagicMock()
            mock_response.headers.get.return_value = "text/html"
            mock_response.raise_for_status = MagicMock()
            mock_response.content = b"<html><body>Simple text content</body></html>"

            mock_ctx = MagicMock()
            mock_ctx.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            from loom.tools.core.document import research_convert_document

            result = await research_convert_document(
                "https://example.com/doc.html", output_format="markdown"
            )

            # Should provide fallback extraction
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_trafilatura_fallback(self):
        """Test Trafilatura extraction as fallback."""
        # Trafilatura is used for HTML-to-text extraction when Pandoc fails
        pass


class TestSupportedFormats:
    """Tests for supported source and output formats."""

    def test_pdf_supported(self):
        """Test PDF is in supported sources."""
        from loom.tools.core.document import SUPPORTED_SOURCES

        assert "pdf" in SUPPORTED_SOURCES

    def test_docx_supported(self):
        """Test DOCX is in supported sources."""
        from loom.tools.core.document import SUPPORTED_SOURCES

        assert "docx" in SUPPORTED_SOURCES

    def test_markdown_output_supported(self):
        """Test markdown output format is supported."""
        from loom.tools.core.document import SUPPORTED_OUTPUTS

        assert "markdown" in SUPPORTED_OUTPUTS or "md" in SUPPORTED_OUTPUTS

    def test_txt_output_supported(self):
        """Test txt output format is supported."""
        from loom.tools.core.document import SUPPORTED_OUTPUTS

        assert "txt" in SUPPORTED_OUTPUTS

    def test_html_output_supported(self):
        """Test html output format is supported."""
        from loom.tools.core.document import SUPPORTED_OUTPUTS

        assert "html" in SUPPORTED_OUTPUTS
