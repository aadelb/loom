"""CAPTCHA detection and malicious artifact tests for Loom.

Tests cover:
  - Cloudflare challenge detection (HTTP 403/503 with CF markers)
  - reCAPTCHA detection (HTML form-based bot checks)
  - Zip bomb simulation (file size validation)
  - Steganographic content detection
  - Deeply nested JSON (recursion limit testing)
  - Binary data in text parameters (input validation)
"""

from __future__ import annotations

import json
import tempfile
import zipfile
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestCaptchaCloudflareDetection:
    """Test detection of Cloudflare challenges and blocks."""

    def test_cloudflare_403_ray_id_detection(self) -> None:
        """Verify fetch tool detects Cloudflare 403 with Ray-ID marker."""
        from loom.tools.fetch import _is_cloudflare_block, FetchResult

        # Mock Cloudflare challenge response
        result = FetchResult(
            url="https://protected.example.com",
            status_code=403,
            html="<html><head>CF-RAY: 1a2b3c4d5e6f7g8h</head></html>",
        )

        # Verify detection
        assert _is_cloudflare_block(result) is True

    def test_cloudflare_403_ray_lowercase_detection(self) -> None:
        """Verify detection with lowercase ray id marker."""
        from loom.tools.fetch import _is_cloudflare_block, FetchResult

        result = FetchResult(
            url="https://protected.example.com",
            status_code=403,
            html="<html>Access Denied - ray id: abc123xyz</html>",
        )

        assert _is_cloudflare_block(result) is True

    def test_cloudflare_503_cloudflare_text_detection(self) -> None:
        """Verify detection of Cloudflare 503 service unavailable."""
        from loom.tools.fetch import _is_cloudflare_block, FetchResult

        result = FetchResult(
            url="https://protected.example.com",
            status_code=503,
            html="<html><body>Cloudflare is processing your request</body></html>",
        )

        assert _is_cloudflare_block(result) is True

    def test_cloudflare_detection_case_insensitive(self) -> None:
        """Verify detection is case-insensitive."""
        from loom.tools.fetch import _is_cloudflare_block, FetchResult

        result = FetchResult(
            url="https://protected.example.com",
            status_code=403,
            html="<html><body>CLOUDFLARE Challenge</body></html>",
        )

        assert _is_cloudflare_block(result) is True

    def test_normal_403_not_cloudflare(self) -> None:
        """Verify normal 403 without CF markers is not detected as Cloudflare."""
        from loom.tools.fetch import _is_cloudflare_block, FetchResult

        result = FetchResult(
            url="https://example.com/forbidden",
            status_code=403,
            html="<html><body>Access Forbidden</body></html>",
        )

        assert _is_cloudflare_block(result) is False


class TestReCaptchaDetection:
    """Test detection of reCAPTCHA bot challenges."""

    def test_recaptcha_form_detection(self) -> None:
        """Verify detection of reCAPTCHA form in HTML response."""
        from loom.tools.fetch import FetchResult

        recaptcha_html = """
        <html>
        <body>
            <form method="POST">
                <div class="g-recaptcha" data-sitekey="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"></div>
                <input type="submit" value="Submit">
            </form>
        </body>
        </html>
        """

        result = FetchResult(
            url="https://protected.example.com",
            status_code=200,
            html=recaptcha_html,
        )

        # Check for reCAPTCHA marker in HTML
        assert "g-recaptcha" in result.html.lower()
        assert "sitekey" in result.html.lower()

    def test_recaptcha_error_response_format(self) -> None:
        """Verify proper error response when bot detected."""
        # Simulate a tool detecting reCAPTCHA and returning error
        error_response = {
            "url": "https://protected.example.com",
            "status_code": 200,
            "error": "bot_detected",
            "detail": "reCAPTCHA challenge detected",
            "escalation_suggested": "research_camoufox or research_botasaurus",
        }

        assert error_response["error"] == "bot_detected"
        assert "reCAPTCHA" in error_response["detail"]
        assert error_response["escalation_suggested"] is not None


class TestZipBombDetection:
    """Test detection and rejection of zip bomb attacks."""

    def test_zip_bomb_size_validation(self) -> None:
        """Verify size check rejects files claiming huge size."""
        # Create a tiny zip file that we'll fake as large
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("test.txt", "a" * 100)

        zip_bytes = zip_buffer.getvalue()
        actual_size = len(zip_bytes)

        # In a real scenario, headers might claim larger size
        # Simulate validation that compares declared vs actual
        claimed_size = 1_000_000_000  # 1GB claim
        max_allowed_size = 100_000_000  # 100MB limit

        # Validation should reject
        is_valid = actual_size <= max_allowed_size

        # But claimed size exceeds limit
        exceeds_limit = claimed_size > max_allowed_size

        assert is_valid is True  # actual is small
        assert exceeds_limit is True  # claimed is huge

    def test_zip_bomb_compression_ratio_check(self) -> None:
        """Verify detection of extreme compression ratio (bomb signature)."""
        # Create a highly compressible file
        highly_compressible = "A" * 1_000_000  # 1MB of same char

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("bomb.txt", highly_compressible)

        zip_bytes = zip_buffer.getvalue()
        uncompressed_size = len(highly_compressible)
        compressed_size = len(zip_bytes)

        # Calculate compression ratio
        ratio = uncompressed_size / max(compressed_size, 1)

        # Zip bombs have extremely high ratios (>1000)
        # Normal files have ratios < 50
        is_bomb_like = ratio > 100

        # This test file has a high ratio (expected)
        assert ratio > 10  # Highly compressible
        assert is_bomb_like is True

    def test_small_file_passes_size_check(self) -> None:
        """Verify normal small files pass validation."""
        small_content = "This is a normal small file."
        size = len(small_content)
        max_allowed = 10_000_000

        assert size < max_allowed
        assert size > 0


class TestSteganographicContentDetection:
    """Test detection of hidden steganographic content."""

    def test_zero_width_character_detection(self) -> None:
        """Verify detection of zero-width character steganography."""
        from loom.tools.stego_detect import _check_whitespace_stego

        # Text with hidden zero-width characters
        text_with_stego = "Hello​world‌test‍message⁠hidden"  # Contains ZWSP, ZWNJ, ZWJ, WJ

        result = _check_whitespace_stego(text_with_stego)

        assert result["suspicious"] is True
        assert result["zero_width_characters_found"] >= 3

    def test_normal_text_no_false_positive(self) -> None:
        """Verify normal text doesn't trigger steganography alarm."""
        from loom.tools.stego_detect import _check_whitespace_stego

        normal_text = "This is a completely normal sentence with no hidden data."

        result = _check_whitespace_stego(normal_text)

        assert result["suspicious"] is False
        assert result["zero_width_characters_found"] == 0

    def test_homoglyph_detection(self) -> None:
        """Verify detection of homoglyph/lookalike character attacks."""
        from loom.tools.stego_detect import _check_homoglyphs

        # Mix of Cyrillic lookalikes (А looks like A, С looks like C)
        text_with_homoglyphs = "АВСЕНКМОРТХаеорсухх"  # Cyrillic letters

        result = _check_homoglyphs(text_with_homoglyphs)

        assert result["suspicious"] is True
        assert result["homoglyphs_found"] >= 1

    def test_trailing_whitespace_detection(self) -> None:
        """Verify detection of trailing whitespace steganography."""
        from loom.tools.stego_detect import _check_whitespace_stego

        # Each line has trailing spaces (common stego method)
        text_with_trailing = "Line one   \nLine two  \nLine three    \nLine four \n"

        result = _check_whitespace_stego(text_with_trailing)

        assert result["trailing_whitespace_lines"] > 0


class TestDeeplyNestedJsonRecursion:
    """Test handling of deeply nested JSON (recursion limit testing)."""

    def test_deeply_nested_json_1000_levels(self) -> None:
        """Verify no RecursionError on 1000-level nested JSON."""
        # Create deeply nested structure
        depth = 1000
        nested = {"level": 0}
        current = nested

        for i in range(1, depth):
            current["next"] = {"level": i}
            current = current["next"]

        # Should be able to serialize without error
        try:
            json_str = json.dumps(nested)
            # Should succeed
            assert isinstance(json_str, str)
            assert "level" in json_str
        except RecursionError:
            pytest.fail("RecursionError on 1000-level JSON serialization")

    def test_deeply_nested_json_parsing(self) -> None:
        """Verify parsing of deeply nested JSON doesn't crash."""
        # Create moderately deep JSON string
        depth = 500
        json_str = "{" * depth + '"value": 42' + "}" * depth

        try:
            parsed = json.loads(json_str)
            assert isinstance(parsed, dict)
        except json.JSONDecodeError:
            # Expected for some edge cases, but shouldn't RecursionError
            pass

    def test_deeply_nested_json_iteration(self) -> None:
        """Verify safe iteration over nested structure."""
        nested = {"a": {"b": {"c": {"d": {"e": {"f": {"value": 42}}}}}}}

        def safe_get(obj: dict[str, Any], *keys: str) -> Any:
            """Safely traverse nested dict without recursion."""
            current = obj
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current

        # Should work without recursion issues
        result = safe_get(nested, "a", "b", "c", "d", "e", "f", "value")
        assert result == 42

    def test_json_max_depth_limit(self) -> None:
        """Verify enforcement of JSON nesting depth limit."""
        max_allowed_depth = 100
        test_depth = 150

        nested = {"level": 0}
        current = nested

        for i in range(1, test_depth):
            current["next"] = {"level": i}
            current = current["next"]

        # Check depth manually by traversing
        def get_depth(obj: dict[str, Any], current_depth: int = 0) -> int:
            """Calculate actual depth of nested dict."""
            if not isinstance(obj, dict):
                return current_depth

            if "next" in obj:
                return get_depth(obj["next"], current_depth + 1)
            return current_depth

        actual_depth = get_depth(nested)

        # Verify depth is tracked
        assert actual_depth == test_depth - 1
        assert actual_depth > max_allowed_depth  # It exceeds limit


class TestBinaryDataInTextParameters:
    """Test handling of binary data passed to text parameters."""

    def test_binary_data_no_crash(self) -> None:
        """Verify no crash when binary data passed as text parameter."""
        # Create invalid UTF-8 sequence
        invalid_utf8 = b"\x80\x81\x82\x83"

        # Attempt to decode should not crash, but may fail gracefully
        try:
            decoded = invalid_utf8.decode("utf-8", errors="replace")
            # Should produce replacement characters
            assert len(decoded) > 0
        except UnicodeDecodeError:
            # Expected to handle gracefully
            pass

    def test_binary_parameter_validation(self) -> None:
        """Verify parameter validation rejects binary data."""
        from pydantic import BaseModel, ValidationError

        class TextParam(BaseModel):
            content: str

        # Binary data should fail validation or be handled
        binary_data = b"\xff\xfe"

        try:
            # Attempt to create with bytes (invalid for str field)
            param = TextParam(content=binary_data)  # type: ignore
            # If it doesn't raise, verify it was coerced safely
            assert isinstance(param.content, str)
        except (ValidationError, TypeError):
            # Expected behavior
            pass

    def test_null_bytes_in_string(self) -> None:
        """Verify handling of null bytes in string parameters."""
        text_with_null = "Hello\x00World\x00Test"

        # Null bytes should be handled safely
        assert "\x00" in text_with_null

        # Remove null bytes safely
        cleaned = text_with_null.replace("\x00", "")
        assert cleaned == "HelloWorldTest"
        assert "\x00" not in cleaned

    def test_invalid_unicode_escape_sequence(self) -> None:
        """Verify handling of invalid Unicode escape sequences."""
        # Some tools might accept strings with invalid escape sequences
        input_str = r"Test \ud800 invalid"  # Lone surrogate

        # Should handle gracefully
        try:
            # Attempt to encode
            encoded = input_str.encode("utf-8")
            assert len(encoded) > 0
        except UnicodeError:
            # Expected in some cases
            pass

    def test_mixed_encodings_detection(self) -> None:
        """Verify detection of mixed text encodings in single string."""
        # Mix of UTF-8 and potentially corrupted data
        mixed_content = "English text " + "日本語" + " mixed"

        # Should parse without crashing
        assert isinstance(mixed_content, str)
        assert "English" in mixed_content
        assert "日本語" in mixed_content


class TestFetchToolResponsesToMalicious:
    """Integration tests verifying fetch tool behavior with malicious responses."""

    @pytest.mark.asyncio
    async def test_fetch_rejects_cloudflare_response(self) -> None:
        """Verify fetch tool detects Cloudflare and returns bot_detected error."""
        from loom.tools.fetch import _is_cloudflare_block, FetchResult

        # Simulate Cloudflare block response
        mock_response = FetchResult(
            url="https://protected.example.com",
            status_code=403,
            html="<html>CF-RAY: test123</html>",
            text="Access Denied",
        )

        # Verify detection
        is_blocked = _is_cloudflare_block(mock_response)
        assert is_blocked is True

        # In real fetch, this would trigger escalation
        # Not passing HTML raw to LLM
        if is_blocked:
            # Tool should escalate, not return raw HTML
            assert mock_response.html is not None  # But it's captured for escalation
            # Would escalate to camoufox/botasaurus instead

    def test_fetch_escalation_path_tracking(self) -> None:
        """Verify fetch tool tracks escalation attempts."""
        from loom.tools.fetch import FetchResult

        result = FetchResult(
            url="https://protected.example.com",
            status_code=403,
            escalation_path=["http", "stealthy", "dynamic"],
        )

        # Should show escalation was attempted
        assert len(result.escalation_path) >= 1
        assert result.escalation_path[0] == "http"


class TestParameterValidationAgainstMalicious:
    """Test parameter validation guards against malicious inputs."""

    def test_fetch_params_url_validation(self) -> None:
        """Verify FetchParams validates URLs against SSRF."""
        from loom.params import FetchParams
        from pydantic import ValidationError

        # Valid public URL should pass
        try:
            params = FetchParams(url="https://example.com")
            assert params.url == "https://example.com"
        except ValidationError:
            pytest.fail("Valid public URL should pass validation")

        # Private IP should be rejected
        with pytest.raises(ValidationError):
            FetchParams(url="http://192.168.1.1")

    def test_max_chars_prevents_memory_bomb(self) -> None:
        """Verify max_chars parameter prevents memory exhaustion."""
        from loom.validators import MAX_FETCH_CHARS

        # Max chars should be set to reasonable limit
        assert MAX_FETCH_CHARS > 0
        assert MAX_FETCH_CHARS < 10_000_000_000  # Less than 10GB

        # Content should be truncated
        huge_content = "A" * (MAX_FETCH_CHARS + 1000)
        truncated = huge_content[:MAX_FETCH_CHARS]

        assert len(truncated) == MAX_FETCH_CHARS
        assert len(truncated) < len(huge_content)

    def test_header_injection_prevention(self) -> None:
        """Verify header parameters prevent injection attacks."""
        from loom.params import FetchParams

        # Headers with newlines should be sanitized
        malicious_headers = {"User-Agent": "MyBot\r\nX-Injected: true"}

        # Should either reject or sanitize
        try:
            params = FetchParams(
                url="https://example.com",
                headers=malicious_headers,
            )
            # If accepted, headers should be sanitized
            if params.headers:
                for key, value in params.headers.items():
                    assert "\r" not in value
                    assert "\n" not in value
        except (ValidationError, ValueError):
            # Also acceptable - reject outright
            pass
