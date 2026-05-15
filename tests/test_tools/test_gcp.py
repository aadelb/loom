"""Tests for Google Cloud Platform integration (Vision and TTS)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.mark.asyncio
class TestResearchImageAnalyze:
    async def test_missing_image_url(self):
        """Test error when image_url is missing."""
        from loom.tools.infrastructure.gcp import research_image_analyze

        result = await research_image_analyze("")

        assert result["status"] == "failed"
        assert result["error"] == "image_url is required"

    async def test_invalid_max_results(self):
        """Test validation of max_results parameter."""
        from loom.tools.infrastructure.gcp import research_image_analyze

        result = await research_image_analyze("https://example.com/image.jpg", max_results=200)

        assert result["status"] == "failed"
        assert "max_results must be 1-100" in result["error"]

    async def test_missing_gcp_credentials(self):
        """Test error when GCP credentials are missing."""
        with patch.dict(os.environ, {}, clear=True):
            from loom.tools.infrastructure.gcp import research_image_analyze

            result = await research_image_analyze("https://example.com/image.jpg")

            assert result["status"] == "failed"
            assert "missing GCP credentials" in result["error"]

    async def test_successful_image_analysis(self):
        """Test successful image analysis."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "responses": [
                {
                    "labelAnnotations": [
                        {"description": "cat", "score": 0.98},
                        {"description": "animal", "score": 0.95},
                    ],
                    "textAnnotations": [
                        {"description": "Full text from image"}
                    ],
                    "safeSearchAnnotation": {
                        "adult": "VERY_UNLIKELY",
                        "spoof": "UNLIKELY",
                        "medical": "UNLIKELY",
                        "violence": "UNLIKELY",
                        "racy": "UNLIKELY",
                    },
                }
            ]
        }

        with patch.dict(os.environ, {"GOOGLE_AI_KEY": "test-key"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            from loom.tools.infrastructure.gcp import research_image_analyze

            result = await research_image_analyze(
                "https://example.com/cat.jpg",
                features=["LABEL_DETECTION", "TEXT_DETECTION", "SAFE_SEARCH_DETECTION"],
            )

            assert result["status"] == "success"
            assert "labels" in result
            assert "text" in result
            assert "safe_search" in result
            assert len(result["labels"]) == 2

    async def test_api_error_response(self):
        """Test handling of API errors."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid image",
                "code": 400,
            }
        }

        with patch.dict(os.environ, {"GOOGLE_AI_KEY": "test-key"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            from loom.tools.infrastructure.gcp import research_image_analyze

            result = await research_image_analyze("https://example.com/image.jpg")

            assert result["status"] == "failed"
            assert "error" in result

    async def test_http_error_response(self):
        """Test handling of HTTP errors."""
        mock_response = AsyncMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with patch.dict(os.environ, {"GOOGLE_AI_KEY": "test-key"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            from loom.tools.infrastructure.gcp import research_image_analyze

            result = await research_image_analyze("https://example.com/image.jpg")

            assert result["status"] == "failed"
            assert "HTTP 403" in result["error"]

    async def test_timeout_exception(self):
        """Test handling of timeout."""
        with patch.dict(os.environ, {"GOOGLE_AI_KEY": "test-key"}), patch(
            "httpx.AsyncClient.post",
            side_effect=httpx.TimeoutException("Timeout"),
        ):
            from loom.tools.infrastructure.gcp import research_image_analyze

            result = await research_image_analyze("https://example.com/image.jpg")

            assert result["status"] == "failed"
            assert "timeout" in result["error"].lower()

    async def test_local_file_analysis(self):
        """Test analyzing local file."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "responses": [
                {
                    "labelAnnotations": [
                        {"description": "document", "score": 0.9}
                    ]
                }
            ]
        }

        with patch.dict(os.environ, {"GOOGLE_AI_KEY": "test-key"}), patch(
            "os.path.isfile",
            return_value=True,
        ), patch(
            "os.path.getsize",
            return_value=1000,
        ), patch(
            "builtins.open",
            create=True,
        ) as mock_open, patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = b"image data"

            from loom.tools.infrastructure.gcp import research_image_analyze

            result = await research_image_analyze("/path/to/image.jpg")

            assert result["status"] == "success"


@pytest.mark.asyncio
class TestResearchTextToSpeech:
    async def test_missing_text(self):
        """Test error when text is missing."""
        from loom.tools.infrastructure.gcp import research_text_to_speech

        result = await research_text_to_speech("")

        assert result["status"] == "failed"
        assert result["error"] == "text is required"

    async def test_text_exceeds_max_length(self):
        """Test error when text exceeds maximum length."""
        from loom.tools.infrastructure.gcp import research_text_to_speech

        long_text = "a" * 6000

        result = await research_text_to_speech(long_text)

        assert result["status"] == "failed"
        assert "exceeds" in result["error"]

    async def test_invalid_voice(self):
        """Test error with invalid voice parameter."""
        from loom.tools.infrastructure.gcp import research_text_to_speech

        result = await research_text_to_speech("Hello world", voice="invalid-voice")

        assert result["status"] == "failed"
        assert "unsupported voice" in result["error"]

    async def test_invalid_speaking_rate(self):
        """Test error with invalid speaking rate."""
        from loom.tools.infrastructure.gcp import research_text_to_speech

        result = await research_text_to_speech(
            "Hello world",
            voice="en-US-Neural2-A",
            speaking_rate=5.0,
        )

        assert result["status"] == "failed"
        assert "speaking_rate must be 0.25-4.0" in result["error"]

    async def test_missing_gcp_credentials_tts(self):
        """Test error when GCP credentials are missing for TTS."""
        with patch.dict(os.environ, {}, clear=True):
            from loom.tools.infrastructure.gcp import research_text_to_speech

            result = await research_text_to_speech("Hello", voice="en-US-Neural2-A")

            assert result["status"] == "failed"
            assert "missing GCP credentials" in result["error"]

    async def test_successful_tts(self):
        """Test successful text-to-speech conversion."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "audioContent": "SGVsbG8gV29ybGQ=",  # Base64 encoded
        }

        with patch.dict(os.environ, {"GOOGLE_AI_KEY": "test-key"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            from loom.tools.infrastructure.gcp import research_text_to_speech

            result = await research_text_to_speech(
                "Hello world",
                voice="en-US-Neural2-A",
                speaking_rate=1.0,
            )

            assert result["status"] == "success"
            assert "audio_base64" in result
            assert result["config"]["voice"] == "en-US-Neural2-A"
            assert result["config"]["speaking_rate"] == 1.0

    async def test_tts_api_error(self):
        """Test handling of TTS API errors."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid text",
                "code": 400,
            }
        }

        with patch.dict(os.environ, {"GOOGLE_AI_KEY": "test-key"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            from loom.tools.infrastructure.gcp import research_text_to_speech

            result = await research_text_to_speech("Hello", voice="en-US-Neural2-A")

            assert result["status"] == "failed"

    async def test_tts_no_audio_content(self):
        """Test handling when no audio content in response."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch.dict(os.environ, {"GOOGLE_AI_KEY": "test-key"}), patch(
            "httpx.AsyncClient.post",
            return_value=mock_response,
        ):
            from loom.tools.infrastructure.gcp import research_text_to_speech

            result = await research_text_to_speech("Hello", voice="en-US-Neural2-A")

            assert result["status"] == "failed"
            assert "no audio content" in result["error"]

    async def test_tts_timeout(self):
        """Test handling of TTS timeout."""
        with patch.dict(os.environ, {"GOOGLE_AI_KEY": "test-key"}), patch(
            "httpx.AsyncClient.post",
            side_effect=httpx.TimeoutException("Timeout"),
        ):
            from loom.tools.infrastructure.gcp import research_text_to_speech

            result = await research_text_to_speech("Hello", voice="en-US-Neural2-A")

            assert result["status"] == "failed"
            assert "timeout" in result["error"].lower()


class TestTTSVoices:
    def test_research_tts_voices(self):
        """Test that TTS voices list is available."""
        from loom.tools.infrastructure.gcp import research_tts_voices

        result = research_tts_voices()

        assert result["status"] == "success"
        assert "voices" in result
        assert len(result["voices"]) > 0
        assert "en-US-Neural2-A" in result["voices"]


class TestGcpValidation:
    def test_validate_gcp_key_invalid(self):
        """Test GCP key validation with invalid key."""
        from loom.tools.infrastructure.gcp import _validate_gcp_key

        # Key starting with AIza is invalid
        assert _validate_gcp_key("AIzaVeryShortKey") is False

    def test_validate_gcp_key_valid(self):
        """Test GCP key validation with valid format."""
        from loom.tools.infrastructure.gcp import _validate_gcp_key

        # Valid format: long string not starting with AIza
        assert _validate_gcp_key("ValidGCPKeyThatIsAtLeast21CharsLong") is True

    def test_load_gcp_credentials(self):
        """Test loading GCP credentials from environment."""
        with patch.dict(os.environ, {"GOOGLE_AI_KEY": "test-key-value"}):
            from loom.tools.infrastructure.gcp import _load_gcp_credentials

            key = _load_gcp_credentials()

            assert key == "test-key-value"

    def test_load_gcp_credentials_fallback(self):
        """Test fallback to alternate environment variables."""
        with patch.dict(os.environ, {"GOOGLE_CLOUD_API_KEY": "fallback-key"}):
            from loom.tools.infrastructure.gcp import _load_gcp_credentials

            key = _load_gcp_credentials()

            assert key == "fallback-key"
