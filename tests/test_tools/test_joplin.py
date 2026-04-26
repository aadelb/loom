"""Tests for Joplin note saving tools."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _clear_joplin_module():
    sys.modules.pop("loom.tools.joplin", None)
    yield
    sys.modules.pop("loom.tools.joplin", None)


@pytest.mark.asyncio
class TestResearchSaveNote:
    async def test_missing_token(self):
        """Test returns error when JOPLIN_TOKEN is not set."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.tools.joplin import research_save_note

            result = await research_save_note(
                title="Test Note",
                body="Test content",
            )

            assert result["error"] == "missing JOPLIN_TOKEN environment variable"
            assert result["status"] == "failed"

    async def test_empty_title(self):
        """Test returns error with empty title."""
        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token123"}):
            from loom.tools.joplin import research_save_note

            result = await research_save_note(
                title="",
                body="Test content",
            )

            assert "title required" in result["error"]
            assert result["status"] == "failed"

    async def test_empty_body(self):
        """Test returns error with empty body."""
        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token123"}):
            from loom.tools.joplin import research_save_note

            result = await research_save_note(
                title="Test",
                body="",
            )

            assert "body required" in result["error"]
            assert result["status"] == "failed"

    async def test_title_exceeds_max_length(self):
        """Test returns error when title exceeds max length."""
        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token123"}):
            from loom.tools.joplin import research_save_note

            long_title = "x" * 501
            result = await research_save_note(
                title=long_title,
                body="Test content",
            )

            assert "title required and must be <=" in result["error"]
            assert result["status"] == "failed"

    async def test_body_exceeds_max_length(self):
        """Test returns error when body exceeds max length."""
        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token123"}):
            from loom.tools.joplin import research_save_note

            long_body = "x" * 100001
            result = await research_save_note(
                title="Test",
                body=long_body,
            )

            assert "body required and must be <=" in result["error"]
            assert result["status"] == "failed"

    async def test_invalid_notebook_id(self):
        """Test returns error with invalid notebook ID format."""
        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token123"}):
            from loom.tools.joplin import research_save_note

            result = await research_save_note(
                title="Test",
                body="Content",
                notebook="invalid-id",
            )

            assert "invalid notebook ID format" in result["error"]
            assert result["status"] == "failed"

    async def test_success(self):
        """Test successful note creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token123"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_save_note

            result = await research_save_note(
                title="Test Note",
                body="Test content here",
            )

            assert result["status"] == "saved"
            assert result["note_id"] == "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
            assert result["title"] == "Test Note"

    async def test_success_with_notebook(self):
        """Test successful note creation with notebook."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token123"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_save_note

            result = await research_save_note(
                title="Test Note",
                body="Content",
                notebook="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
            )

            assert result["status"] == "saved"
            # Verify notebook was included in request
            call_kwargs = mock_instance.post.call_args.kwargs
            assert call_kwargs["json"]["parent_id"] == "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"

    async def test_http_error_401(self):
        """Test handling of 401 authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=mock_response
            )
        )

        with patch.dict("os.environ", {"JOPLIN_TOKEN": "invalid"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_save_note

            result = await research_save_note(
                title="Test",
                body="Content",
            )

            assert "authentication failed" in result["error"]
            assert result["status"] == "failed"

    async def test_http_error_404(self):
        """Test handling of 404 not found (notebook not found)."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_response
            )
        )

        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_save_note

            result = await research_save_note(
                title="Test",
                body="Content",
                notebook="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
            )

            assert "notebook not found" in result["error"]

    async def test_connection_error(self):
        """Test handling of connection error."""
        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_save_note

            result = await research_save_note(
                title="Test",
                body="Content",
            )

            assert "Could not connect to Joplin" in result["error"]
            assert result["status"] == "failed"

    async def test_timeout_error(self):
        """Test handling of timeout error."""
        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_save_note

            result = await research_save_note(
                title="Test",
                body="Content",
            )

            assert "timeout" in result["error"]


@pytest.mark.asyncio
class TestResearchListNotebooks:
    async def test_missing_token(self):
        """Test returns error when JOPLIN_TOKEN is not set."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.tools.joplin import research_list_notebooks

            result = await research_list_notebooks()

            assert result["error"] == "missing JOPLIN_TOKEN environment variable"
            assert result["notebooks"] == []

    async def test_success(self):
        """Test successful notebook listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
                    "title": "Research",
                },
                {
                    "id": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6a1",
                    "title": "Projects",
                },
                {
                    "id": "c3d4e5f6a7b8c9d0e1f2a3b4c5d6a1b2",
                    "title": "Notes",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token123"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_list_notebooks

            result = await research_list_notebooks()

            assert "error" not in result
            assert len(result["notebooks"]) == 3
            assert result["notebooks"][0]["title"] == "Research"
            assert result["notebooks"][1]["title"] == "Projects"
            assert result["total"] == 3

    async def test_http_error_401(self):
        """Test handling of 401 authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=mock_response
            )
        )

        with patch.dict("os.environ", {"JOPLIN_TOKEN": "invalid"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_list_notebooks

            result = await research_list_notebooks()

            assert "authentication failed" in result["error"]
            assert result["notebooks"] == []

    async def test_connection_error(self):
        """Test handling of connection error."""
        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_list_notebooks

            result = await research_list_notebooks()

            assert "Could not connect to Joplin" in result["error"]
            assert result["notebooks"] == []

    async def test_timeout_error(self):
        """Test handling of timeout error."""
        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_list_notebooks

            result = await research_list_notebooks()

            assert "timeout" in result["error"]
            assert result["notebooks"] == []

    async def test_empty_notebooks_list(self):
        """Test handling of empty notebooks list."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_list_notebooks

            result = await research_list_notebooks()

            assert result["notebooks"] == []
            assert result["total"] == 0

    async def test_filter_notebooks_without_id(self):
        """Test that notebooks without ID are filtered out."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
                    "title": "Research",
                },
                {
                    "id": None,
                    "title": "Invalid",
                },
                {
                    "title": "Also Invalid",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"JOPLIN_TOKEN": "token"}), patch(
            "loom.tools.joplin.httpx.AsyncClient"
        ) as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_instance

            from loom.tools.joplin import research_list_notebooks

            result = await research_list_notebooks()

            assert len(result["notebooks"]) == 1
            assert result["notebooks"][0]["title"] == "Research"
