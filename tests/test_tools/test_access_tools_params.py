"""Validation tests for access_tools parameters."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from loom.params import (
    LegalTakedownParams,
    OpenAccessParams,
    ContentAuthenticityParams,
    CredentialMonitorParams,
    DeepfakeCheckerParams,
)


pytestmark = pytest.mark.asyncio

class TestLegalTakedownParams:
    """Tests for LegalTakedownParams validation."""

    async def test_valid_domain(self):
        """Test valid domain."""
        params = LegalTakedownParams(domain="example.com")
        assert params.domain == "example.com"

    async def test_domain_case_normalization(self):
        """Test that domains are lowercased."""
        params = LegalTakedownParams(domain="EXAMPLE.COM")
        assert params.domain == "example.com"

    async def test_domain_whitespace_trimmed(self):
        """Test that domain whitespace is trimmed."""
        params = LegalTakedownParams(domain="  example.com  ")
        assert params.domain == "example.com"

    async def test_invalid_domain_format(self):
        """Test that invalid domain format raises error."""
        with pytest.raises(ValidationError):
            LegalTakedownParams(domain="invalid..domain")

    async def test_invalid_domain_no_tld(self):
        """Test that domain without TLD raises error."""
        with pytest.raises(ValidationError):
            LegalTakedownParams(domain="localhost")


class TestOpenAccessParams:
    """Tests for OpenAccessParams validation."""

    async def test_valid_doi(self):
        """Test valid DOI."""
        params = OpenAccessParams(doi="10.1000/xyz123")
        assert params.doi == "10.1000/xyz123"

    async def test_doi_whitespace_trimmed(self):
        """Test that DOI whitespace is trimmed."""
        params = OpenAccessParams(doi="  10.1000/xyz123  ")
        assert params.doi == "10.1000/xyz123"

    async def test_invalid_doi_format(self):
        """Test that invalid DOI format raises error."""
        with pytest.raises(ValidationError):
            OpenAccessParams(doi="not_a_doi")

    async def test_valid_title(self):
        """Test valid title."""
        params = OpenAccessParams(title="Machine Learning in Practice")
        assert params.title == "Machine Learning in Practice"

    async def test_title_whitespace_trimmed(self):
        """Test that title whitespace is trimmed."""
        params = OpenAccessParams(title="  Machine Learning  ")
        assert params.title == "Machine Learning"

    async def test_title_max_length(self):
        """Test that title exceeding max length raises error."""
        long_title = "x" * 501
        with pytest.raises(ValidationError):
            OpenAccessParams(title=long_title)

    async def test_doi_and_title_optional(self):
        """Test that both DOI and title are optional."""
        params = OpenAccessParams()
        assert params.doi == ""
        assert params.title == ""


class TestContentAuthenticityParams:
    """Tests for ContentAuthenticityParams validation."""

    async def test_valid_url(self):
        """Test valid URL."""
        params = ContentAuthenticityParams(url="https://example.com/page")
        assert "example.com" in params.url

    async def test_url_validation(self):
        """Test that invalid URL raises error."""
        with pytest.raises(ValidationError):
            ContentAuthenticityParams(url="not a url")

    async def test_http_url(self):
        """Test HTTP URL is accepted."""
        params = ContentAuthenticityParams(url="http://example.com")
        assert "example.com" in params.url


class TestCredentialMonitorParams:
    """Tests for CredentialMonitorParams validation."""

    async def test_valid_email_target(self):
        """Test valid email target."""
        params = CredentialMonitorParams(target="user@example.com", target_type="email")
        assert params.target == "user@example.com"
        assert params.target_type == "email"

    async def test_valid_username_target(self):
        """Test valid username target."""
        params = CredentialMonitorParams(target="john_doe", target_type="username")
        assert params.target == "john_doe"
        assert params.target_type == "username"

    async def test_target_case_normalization(self):
        """Test that target is lowercased."""
        params = CredentialMonitorParams(target="USER@EXAMPLE.COM")
        assert params.target == "user@example.com"

    async def test_target_whitespace_trimmed(self):
        """Test that target whitespace is trimmed."""
        params = CredentialMonitorParams(target="  user@example.com  ")
        assert params.target == "user@example.com"

    async def test_target_max_length(self):
        """Test that target exceeding max length raises error."""
        long_target = "x" * 256
        with pytest.raises(ValidationError):
            CredentialMonitorParams(target=long_target)

    async def test_default_target_type(self):
        """Test that target_type defaults to email."""
        params = CredentialMonitorParams(target="user@example.com")
        assert params.target_type == "email"


class TestDeepfakeCheckerParams:
    """Tests for DeepfakeCheckerParams validation."""

    async def test_valid_jpg_url(self):
        """Test valid JPG image URL."""
        params = DeepfakeCheckerParams(image_url="https://example.com/image.jpg")
        assert "example.com" in params.image_url

    async def test_valid_png_url(self):
        """Test valid PNG image URL."""
        params = DeepfakeCheckerParams(image_url="https://example.com/image.png")
        assert "example.com" in params.image_url

    async def test_valid_webp_url(self):
        """Test valid WebP image URL."""
        params = DeepfakeCheckerParams(image_url="https://example.com/image.webp")
        assert "example.com" in params.image_url

    async def test_invalid_file_type(self):
        """Test that non-image file types raise error."""
        with pytest.raises(ValidationError):
            DeepfakeCheckerParams(image_url="https://example.com/document.pdf")

    async def test_invalid_url(self):
        """Test that invalid URL raises error."""
        with pytest.raises(ValidationError):
            DeepfakeCheckerParams(image_url="not a url")

    async def test_jpeg_extension(self):
        """Test JPEG extension is accepted."""
        params = DeepfakeCheckerParams(image_url="https://example.com/photo.jpeg")
        assert "example.com" in params.image_url


class TestParamsExtraSecurity:
    """Tests for extra fields rejection and strict mode."""

    async def test_legal_takedown_no_extra_fields(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            LegalTakedownParams(domain="example.com", extra_field="value")

    async def test_open_access_no_extra_fields(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            OpenAccessParams(doi="10.1000/xyz", extra_field="value")

    async def test_credential_monitor_no_extra_fields(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            CredentialMonitorParams(target="user@example.com", extra_field="value")

    async def test_deepfake_checker_no_extra_fields(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            DeepfakeCheckerParams(image_url="https://example.com/image.jpg", extra_field="value")
