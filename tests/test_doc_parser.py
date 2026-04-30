"""Unit tests for doc_parser module — OCR and PDF extraction tools."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from loom.doc_parser import (
    research_document_analyze,
    research_ocr_advanced,
    research_pdf_advanced,
)


class TestOCRAdvanced:
    """research_ocr_advanced function."""

    def test_ocr_advanced_invalid_url(self) -> None:
        """Invalid URL returns error."""
        result = research_ocr_advanced("ht!tp://invalid")
        assert "error" in result

    def test_ocr_advanced_local_file_not_found(self) -> None:
        """Non-existent local file returns error."""
        result = research_ocr_advanced("/nonexistent/image.png")
        assert "error" in result
        assert "File not found" in result["error"]

    def test_ocr_advanced_local_file_is_directory(self) -> None:
        """Directory instead of file returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = research_ocr_advanced(tmpdir)
            assert "error" in result
            assert "Not a file" in result["error"]

    def test_ocr_advanced_local_file_success(self) -> None:
        """Successful OCR extraction from local file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Mock EasyOCR
            mock_reader = MagicMock()
            mock_results = [
                ([[0, 0], [100, 0], [100, 50], [0, 50]], "Hello", 0.95),
                ([[0, 60], [100, 60], [100, 110], [0, 110]], "World", 0.92),
            ]
            mock_reader.readtext.return_value = mock_results

            mock_easyocr = MagicMock()
            mock_easyocr.Reader = MagicMock(return_value=mock_reader)

            with patch.dict("sys.modules", {"easyocr": mock_easyocr}):
                # Re-import to pick up mocked module
                import importlib
                import loom.doc_parser
                importlib.reload(loom.doc_parser)

                result = loom.doc_parser.research_ocr_advanced(tmp_path, languages=["en"], detail=True)

            assert "error" not in result
            assert result["text"] == "Hello World"
            assert result["languages_detected"] == ["en"]
            assert result["page_count"] == 1
            assert len(result["blocks"]) == 2
            assert result["blocks"][0]["text"] == "Hello"
            assert result["blocks"][0]["confidence"] == 0.95
            assert "bbox" in result["blocks"][0]

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_ocr_advanced_url_download_failure(self) -> None:
        """Failed URL download returns error."""
        with patch("loom.doc_parser.httpx.stream") as mock_stream:
            mock_stream.side_effect = httpx.ConnectError("Connection failed")
            result = research_ocr_advanced("https://example.com/image.png")

            assert "error" in result
            assert "HTTP error" in result["error"]

    def test_ocr_advanced_detail_false(self) -> None:
        """With detail=False, returns only full text."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Mock EasyOCR with proper structure
            mock_reader = MagicMock()
            mock_results = [
                ([[0, 0], [100, 0], [100, 50], [0, 50]], "Hello", 0.95),
            ]
            mock_reader.readtext.return_value = mock_results

            mock_easyocr = MagicMock()
            mock_easyocr.Reader = MagicMock(return_value=mock_reader)

            with patch.dict("sys.modules", {"easyocr": mock_easyocr}):
                import importlib
                import loom.doc_parser
                importlib.reload(loom.doc_parser)

                result = loom.doc_parser.research_ocr_advanced(tmp_path, detail=False)

            assert "error" not in result
            assert result["text"] == "Hello"
            assert result["blocks"] == []

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestPDFAdvanced:
    """research_pdf_advanced function."""

    def test_pdf_advanced_invalid_url(self) -> None:
        """Invalid URL returns error."""
        result = research_pdf_advanced("ht!tp://invalid")
        assert "error" in result

    def test_pdf_advanced_local_file_not_found(self) -> None:
        """Non-existent local file returns error."""
        result = research_pdf_advanced("/nonexistent/file.pdf")
        assert "error" in result
        assert "File not found" in result["error"]

    def test_pdf_advanced_local_file_is_directory(self) -> None:
        """Directory instead of file returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = research_pdf_advanced(tmpdir)
            assert "error" in result
            assert "Not a file" in result["error"]

    def test_pdf_advanced_local_file_size(self) -> None:
        """PDF file size is recorded."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF test content")
            tmp_path = tmp.name

        try:
            # Mock fitz to fail so we fallback to pdftotext
            mock_fitz = MagicMock()
            mock_fitz.open = MagicMock(side_effect=ImportError)

            with patch.dict("sys.modules", {"fitz": mock_fitz}):
                with patch("loom.doc_parser.subprocess.run") as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_result.stdout = "Extracted text"
                    mock_run.return_value = mock_result

                    result = research_pdf_advanced(tmp_path)

            assert "error" not in result
            assert result["file_size_bytes"] > 0

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_pdf_advanced_pdftotext_fallback(self) -> None:
        """Falls back to pdftotext when PyMuPDF unavailable."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF test")
            tmp_path = tmp.name

        try:
            with patch("loom.doc_parser.subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "Extracted text from pdftotext"
                mock_run.return_value = mock_result

                result = research_pdf_advanced(tmp_path)

            assert "error" not in result
            assert result["extraction_method"] == "pdftotext"
            assert "Extracted text" in result["text"]

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_pdf_advanced_pdftotext_not_found(self) -> None:
        """Missing pdftotext command returns error."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF test")
            tmp_path = tmp.name

        try:
            with patch("loom.doc_parser.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("pdftotext not found")

                result = research_pdf_advanced(tmp_path)

            assert "error" in result
            assert "pdftotext command not found" in result["error"]

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_pdf_advanced_pdftotext_timeout(self) -> None:
        """pdftotext timeout returns error."""
        import subprocess

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF test")
            tmp_path = tmp.name

        try:
            with patch("loom.doc_parser.subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("pdftotext", 30)

                result = research_pdf_advanced(tmp_path)

            assert "error" in result
            assert "timed out" in result["error"]

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_pdf_advanced_url_download_failure(self) -> None:
        """Failed URL download returns error."""
        with patch("loom.doc_parser.httpx.stream") as mock_stream:
            mock_stream.side_effect = httpx.ConnectError("Connection failed")
            result = research_pdf_advanced("https://example.com/file.pdf")

            assert "error" in result
            assert "HTTP error" in result["error"]


class TestDocumentAnalyze:
    """research_document_analyze function."""

    def test_document_analyze_invalid_url(self) -> None:
        """Invalid URL returns error."""
        result = research_document_analyze("ht!tp://invalid")
        assert "error" in result

    def test_document_analyze_local_file_not_found(self) -> None:
        """Non-existent local file returns error."""
        result = research_document_analyze("/nonexistent/file.pdf")
        assert "error" in result

    def test_document_analyze_pdf_by_extension(self) -> None:
        """Detects PDF by file extension."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF")
            tmp_path = tmp.name

        try:
            with patch("loom.doc_parser.subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "PDF content"
                mock_run.return_value = mock_result

                result = research_document_analyze(tmp_path)

            assert result["file_type"] == "pdf"

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_document_analyze_image_by_extension(self) -> None:
        """Detects image by file extension."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"\x89PNG")
            tmp_path = tmp.name

        try:
            mock_reader = MagicMock()
            mock_results = [
                ([[0, 0], [100, 0], [100, 50], [0, 50]], "Image text", 0.95),
            ]
            mock_reader.readtext.return_value = mock_results

            mock_easyocr = MagicMock()
            mock_easyocr.Reader = MagicMock(return_value=mock_reader)

            with patch.dict("sys.modules", {"easyocr": mock_easyocr}):
                import importlib
                import loom.doc_parser
                importlib.reload(loom.doc_parser)

                result = loom.doc_parser.research_document_analyze(tmp_path)

            assert result["file_type"] == "image"

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_document_analyze_analysis_level_fast(self) -> None:
        """With analysis='fast', skips tables."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF")
            tmp_path = tmp.name

        try:
            with patch("loom.doc_parser.subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "Content"
                mock_run.return_value = mock_result

                result = research_document_analyze(tmp_path, analysis="fast")

            assert result["file_type"] == "pdf"
            assert result["tables"] == []

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_document_analyze_analysis_level_text(self) -> None:
        """With analysis='text', returns only text without tables."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF")
            tmp_path = tmp.name

        try:
            with patch("loom.doc_parser.subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "Text only"
                mock_run.return_value = mock_result

                result = research_document_analyze(tmp_path, analysis="text")

            assert result["file_type"] == "pdf"
            assert result["tables"] == []

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_document_analyze_output_fields_pdf(self) -> None:
        """PDF analysis includes expected fields."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF")
            tmp_path = tmp.name

        try:
            with patch("loom.doc_parser.subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "PDF content"
                mock_run.return_value = mock_result

                result = research_document_analyze(tmp_path)

            assert "file_path" in result
            assert "file_type" in result
            assert "text" in result
            assert "page_count" in result
            assert "metadata" in result
            assert "extraction_method" in result

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_document_analyze_output_fields_image(self) -> None:
        """Image analysis includes expected fields."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"\xff\xd8\xff")  # JPEG magic bytes
            tmp_path = tmp.name

        try:
            mock_reader = MagicMock()
            mock_results = [
                ([[0, 0], [100, 0], [100, 50], [0, 50]], "Text", 0.95),
            ]
            mock_reader.readtext.return_value = mock_results

            mock_easyocr = MagicMock()
            mock_easyocr.Reader = MagicMock(return_value=mock_reader)

            with patch.dict("sys.modules", {"easyocr": mock_easyocr}):
                import importlib
                import loom.doc_parser
                importlib.reload(loom.doc_parser)

                result = loom.doc_parser.research_document_analyze(tmp_path)

            assert "file_path" in result
            assert "file_type" in result
            assert result["file_type"] == "image"
            assert "ocr_text" in result
            assert "languages_detected" in result

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
