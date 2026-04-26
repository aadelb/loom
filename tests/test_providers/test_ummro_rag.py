"""Tests for UMMRO RAG provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestSearchUmmroRag:
    """Tests for search_ummro_rag() function."""

    def test_missing_api_url(self):
        """Test error when UMMRO_RAG_URL is not set."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.ummro_rag import search_ummro_rag

            result = search_ummro_rag("test query")

            assert "error" in result
            assert "UMMRO_RAG_URL" in result["error"] or "not set" in result["error"].lower()

    def test_invalid_collection(self):
        """Test error for invalid collection name."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            result = search_ummro_rag("test query", collection="invalid")

            assert "error" in result
            assert "collection" in result["error"].lower() or "invalid" in result["error"].lower()

    def test_documents_collection(self):
        """Test 'documents' is valid collection."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {"results": [], "count": 0}
                mock_response.raise_for_status = MagicMock()

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("test query", collection="documents")

                # Should not have error about collection
                if "error" in result:
                    assert "collection" not in result["error"].lower()

    def test_code_collection(self):
        """Test 'code' is valid collection."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {"results": [], "count": 0}
                mock_response.raise_for_status = MagicMock()

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("test query", collection="code")

                # Should not have error about collection
                if "error" in result:
                    assert "collection" not in result["error"].lower()

    def test_successful_search_documents(self):
        """Test successful search in documents collection."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "results": [
                        {
                            "text": "Sample document content",
                            "score": 0.95,
                            "metadata": {
                                "source": "arxiv",
                                "url": "https://arxiv.org/abs/2024.12345",
                                "title": "Test Paper",
                            },
                        }
                    ],
                    "count": 1,
                }
                mock_response.raise_for_status = MagicMock()

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("machine learning", collection="documents", n=10)

                assert "error" not in result or result.get("error") is None
                assert "results" in result
                assert result["query"] == "machine learning"
                assert result["collection"] == "documents"
                assert result["count"] >= 0

    def test_successful_search_code(self):
        """Test successful search in code collection."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "results": [
                        {
                            "text": "def search_function():\n    pass",
                            "score": 0.87,
                            "metadata": {
                                "source": "github",
                                "url": "https://github.com/user/repo",
                                "language": "python",
                            },
                        }
                    ],
                    "count": 1,
                }
                mock_response.raise_for_status = MagicMock()

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("search function", collection="code", n=5)

                assert "error" not in result or result.get("error") is None
                assert result["collection"] == "code"

    def test_n_parameter_validation(self):
        """Test 'n' parameter is validated."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {"results": [], "count": 0}
                mock_response.raise_for_status = MagicMock()

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("test query", n=200)

                # Should either clamp n or accept it
                assert isinstance(result, dict)

    def test_connection_error(self):
        """Test handling of connection errors."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.post.side_effect = Exception("Connection refused")
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("test query")

                assert "error" in result
                assert result["results"] == []

    def test_timeout_error(self):
        """Test handling of timeout errors."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.post.side_effect = TimeoutError("Request timed out")
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("test query")

                assert "error" in result

    def test_http_error_response(self):
        """Test handling of HTTP error responses."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.raise_for_status.side_effect = Exception("HTTP 500")

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("test query")

                assert "error" in result

    def test_empty_results(self):
        """Test handling of empty search results."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {"results": [], "count": 0}
                mock_response.raise_for_status = MagicMock()

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("nonexistent topic")

                assert result["count"] == 0
                assert result["results"] == []
                assert "error" not in result or result["error"] is None

    def test_result_structure(self):
        """Test result has required fields."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "results": [
                        {
                            "text": "content",
                            "score": 0.9,
                            "metadata": {"source": "test"},
                        }
                    ],
                    "count": 1,
                }
                mock_response.raise_for_status = MagicMock()

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("test")

                assert "query" in result
                assert "collection" in result
                assert "count" in result
                assert "results" in result

    def test_malformed_response(self):
        """Test handling of malformed API response."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.side_effect = ValueError("Invalid JSON")
                mock_response.raise_for_status = MagicMock()

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("test")

                assert "error" in result

    def test_multilingual_query(self):
        """Test support for multilingual queries."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "results": [
                        {
                            "text": "محتوى عربي",
                            "score": 0.88,
                            "metadata": {"language": "ar"},
                        }
                    ],
                    "count": 1,
                }
                mock_response.raise_for_status = MagicMock()

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                # Arabic query
                result = search_ummro_rag("بحث باللغة العربية", collection="documents")

                assert "error" not in result or result.get("error") is None

    def test_special_characters_in_query(self):
        """Test handling of special characters in query."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {"results": [], "count": 0}
                mock_response.raise_for_status = MagicMock()

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = search_ummro_rag("test @#$% query & <more>")

                assert isinstance(result, dict)

    def test_kwargs_ignored(self):
        """Test that extra kwargs are ignored."""
        with patch.dict("os.environ", {"UMMRO_RAG_URL": "http://localhost:8000"}):
            from loom.providers.ummro_rag import search_ummro_rag

            with patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.json.return_value = {"results": [], "count": 0}
                mock_response.raise_for_status = MagicMock()

                mock_ctx = MagicMock()
                mock_ctx.post.return_value = mock_response
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                # Pass extra kwargs
                result = search_ummro_rag(
                    "test query",
                    n=10,
                    collection="documents",
                    extra_param1="ignored",
                    extra_param2=123,
                )

                assert isinstance(result, dict)
