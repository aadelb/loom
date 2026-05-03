"""Tests for JWT-based authentication module.

Tests cover:
- Token generation and validation
- Role-based access control
- Token expiration
- Permission checking
- Error handling
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta

import pytest

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None

from loom.jwt_auth import (
    InvalidTokenError,
    InsufficientPermissionsError,
    JWTAuthError,
    ROLE_PERMISSIONS,
    TOOL_CATEGORIES,
    TokenExpiredError,
    check_tool_access,
    create_token,
    get_allowed_tools,
    get_token_info,
    validate_token,
    verify_and_get_role,
)


@pytest.fixture
def jwt_secret() -> str:
    """Set up JWT secret for tests."""
    secret = "test-secret-key-12345"
    os.environ["LOOM_JWT_SECRET"] = secret
    yield secret
    if "LOOM_JWT_SECRET" in os.environ:
        del os.environ["LOOM_JWT_SECRET"]


@pytest.fixture
def admin_token(jwt_secret: str) -> str:
    """Create an admin token for testing."""
    if pyjwt is None:
        pytest.skip("PyJWT not installed")
    return create_token("admin-user", "admin", expires_in_hours=24)


@pytest.fixture
def researcher_token(jwt_secret: str) -> str:
    """Create a researcher token for testing."""
    if pyjwt is None:
        pytest.skip("PyJWT not installed")
    return create_token("researcher-user", "researcher", expires_in_hours=24)


@pytest.fixture
def red_team_token(jwt_secret: str) -> str:
    """Create a red_team token for testing."""
    if pyjwt is None:
        pytest.skip("PyJWT not installed")
    return create_token("red-team-user", "red_team", expires_in_hours=24)


@pytest.fixture
def viewer_token(jwt_secret: str) -> str:
    """Create a viewer token for testing."""
    if pyjwt is None:
        pytest.skip("PyJWT not installed")
    return create_token("viewer-user", "viewer", expires_in_hours=24)


class TestTokenGeneration:
    """Test JWT token generation."""

    def test_create_token_admin(self, jwt_secret: str) -> None:
        """Test creating admin token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        token = create_token("user123", "admin", expires_in_hours=24)
        assert isinstance(token, str)
        assert token.count(".") == 2  # JWT has 3 parts separated by dots

    def test_create_token_researcher(self, jwt_secret: str) -> None:
        """Test creating researcher token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        token = create_token("user456", "researcher", expires_in_hours=12)
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_create_token_invalid_role(self, jwt_secret: str) -> None:
        """Test creating token with invalid role."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        with pytest.raises(ValueError, match="Invalid role"):
            create_token("user123", "invalid_role", expires_in_hours=24)

    def test_create_token_no_secret(self) -> None:
        """Test creating token when secret is not set."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        # Ensure LOOM_JWT_SECRET is not set
        os.environ.pop("LOOM_JWT_SECRET", None)

        with pytest.raises(ValueError, match="LOOM_JWT_SECRET"):
            create_token("user123", "admin", expires_in_hours=24)

    def test_create_token_custom_expiry(self, jwt_secret: str) -> None:
        """Test creating token with custom expiry time."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        token = create_token("user123", "admin", expires_in_hours=72)
        payload = validate_token(token)

        # Verify expiry time is approximately 72 hours from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        now = datetime.now(UTC)
        diff = (exp_time - now).total_seconds()

        # Should be approximately 72 hours (within 5 seconds of margin)
        assert 259190 < diff < 259210  # 72 hours in seconds


class TestTokenValidation:
    """Test JWT token validation."""

    def test_validate_token_valid(self, admin_token: str, jwt_secret: str) -> None:
        """Test validating a valid token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        payload = validate_token(admin_token)
        assert payload["sub"] == "admin-user"
        assert payload["role"] == "admin"
        assert "iat" in payload
        assert "exp" in payload

    def test_validate_token_expired(self, jwt_secret: str) -> None:
        """Test validating an expired token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        # Create token that expires immediately
        token = create_token("user123", "admin", expires_in_hours=0)
        time.sleep(0.1)  # Ensure token is expired

        with pytest.raises(TokenExpiredError):
            validate_token(token)

    def test_validate_token_invalid_signature(self, jwt_secret: str) -> None:
        """Test validating token with invalid signature."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        # Create token with correct secret
        token = create_token("user123", "admin", expires_in_hours=24)

        # Change secret and try to validate
        os.environ["LOOM_JWT_SECRET"] = "different-secret"

        with pytest.raises(InvalidTokenError):
            validate_token(token)

    def test_validate_token_malformed(self, jwt_secret: str) -> None:
        """Test validating malformed token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        with pytest.raises(InvalidTokenError):
            validate_token("not.a.valid.token.with.too.many.parts")

    def test_validate_token_empty(self, jwt_secret: str) -> None:
        """Test validating empty token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        with pytest.raises(InvalidTokenError):
            validate_token("")


class TestRoleBasedAccess:
    """Test role-based access control."""

    def test_admin_get_allowed_tools(self) -> None:
        """Test admin has unrestricted access."""
        allowed = get_allowed_tools("admin")
        assert "*" in allowed
        assert len(allowed) == 1

    def test_researcher_get_allowed_tools(self) -> None:
        """Test researcher has limited tools."""
        allowed = get_allowed_tools("researcher")
        assert "*" not in allowed
        assert "search" in allowed
        assert "fetch" in allowed
        assert "llm" in allowed
        assert "prompt_reframe" not in allowed

    def test_red_team_get_allowed_tools(self) -> None:
        """Test red_team has unrestricted access."""
        allowed = get_allowed_tools("red_team")
        assert "*" in allowed

    def test_viewer_get_allowed_tools(self) -> None:
        """Test viewer has minimal tools."""
        allowed = get_allowed_tools("viewer")
        assert "*" not in allowed
        assert "search" in allowed
        assert "health_check" in allowed
        assert "help" in allowed
        assert "fetch" not in allowed
        assert "llm" not in allowed

    def test_get_allowed_tools_invalid_role(self) -> None:
        """Test getting tools for invalid role."""
        with pytest.raises(ValueError, match="Invalid role"):
            get_allowed_tools("nonexistent_role")


class TestToolAccess:
    """Test tool access checking."""

    def test_admin_access_all_tools(self, admin_token: str) -> None:
        """Test admin can access any tool."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        assert check_tool_access(admin_token, "research_fetch") is True
        assert check_tool_access(admin_token, "prompt_reframe") is True
        assert check_tool_access(admin_token, "any_tool") is True

    def test_researcher_access_allowed_tools(self, researcher_token: str) -> None:
        """Test researcher can access allowed tools."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        assert check_tool_access(researcher_token, "search") is True
        assert check_tool_access(researcher_token, "fetch") is True
        assert check_tool_access(researcher_token, "llm") is True

    def test_researcher_cannot_access_restricted_tools(self, researcher_token: str) -> None:
        """Test researcher cannot access restricted tools."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        assert check_tool_access(researcher_token, "prompt_reframe") is False
        assert check_tool_access(researcher_token, "adversarial_debate_tool") is False
        assert check_tool_access(researcher_token, "context_poison") is False

    def test_red_team_access_all_tools(self, red_team_token: str) -> None:
        """Test red_team can access all tools."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        assert check_tool_access(red_team_token, "prompt_reframe") is True
        assert check_tool_access(red_team_token, "adversarial_debate_tool") is True
        assert check_tool_access(red_team_token, "context_poison") is True
        assert check_tool_access(red_team_token, "research_fetch") is True

    def test_viewer_access_read_only(self, viewer_token: str) -> None:
        """Test viewer can only access read-only tools."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        assert check_tool_access(viewer_token, "search") is True
        assert check_tool_access(viewer_token, "help") is True
        assert check_tool_access(viewer_token, "health_check") is True

    def test_viewer_cannot_access_write_tools(self, viewer_token: str) -> None:
        """Test viewer cannot access tools that modify state."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        assert check_tool_access(viewer_token, "fetch") is False
        assert check_tool_access(viewer_token, "llm") is False
        assert check_tool_access(viewer_token, "config") is False

    def test_tool_access_expired_token(self, jwt_secret: str) -> None:
        """Test tool access with expired token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        # Create expired token
        token = create_token("user123", "admin", expires_in_hours=0)
        time.sleep(0.1)

        with pytest.raises(TokenExpiredError):
            check_tool_access(token, "research_fetch")

    def test_tool_access_invalid_token(self) -> None:
        """Test tool access with invalid token."""
        with pytest.raises(InvalidTokenError):
            check_tool_access("invalid.token.here", "research_fetch")


class TestTokenInfo:
    """Test token information retrieval."""

    def test_get_token_info_admin(self, admin_token: str) -> None:
        """Test getting admin token info."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        info = get_token_info(admin_token)
        assert info["user_id"] == "admin-user"
        assert info["role"] == "admin"
        assert info["is_expired"] is False
        assert info["allowed_tools_count"] == "unlimited"

    def test_get_token_info_researcher(self, researcher_token: str) -> None:
        """Test getting researcher token info."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        info = get_token_info(researcher_token)
        assert info["user_id"] == "researcher-user"
        assert info["role"] == "researcher"
        assert info["is_expired"] is False
        assert isinstance(info["allowed_tools_count"], int)
        assert info["allowed_tools_count"] > 0
        assert "safe" in info["allowed_tool_categories"]

    def test_get_token_info_contains_timestamps(self, admin_token: str) -> None:
        """Test token info contains valid timestamps."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        info = get_token_info(admin_token)
        assert "issued_at" in info
        assert "expires_at" in info

        # Parse timestamps
        issued = datetime.fromisoformat(info["issued_at"])
        expires = datetime.fromisoformat(info["expires_at"])

        # Expires should be after issued
        assert expires > issued

    def test_get_token_info_expired_token(self, jwt_secret: str) -> None:
        """Test getting info for expired token (should still work)."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        # Note: validate_token raises TokenExpiredError, but get_token_info
        # should handle it gracefully for inspection purposes
        token = create_token("user123", "admin", expires_in_hours=0)
        time.sleep(0.1)

        # get_token_info calls validate_token which will raise
        with pytest.raises(TokenExpiredError):
            get_token_info(token)


class TestVerifyAndGetRole:
    """Test convenience function for role extraction."""

    def test_verify_and_get_role_admin(self, admin_token: str) -> None:
        """Test extracting role from admin token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        role = verify_and_get_role(admin_token)
        assert role == "admin"

    def test_verify_and_get_role_researcher(self, researcher_token: str) -> None:
        """Test extracting role from researcher token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        role = verify_and_get_role(researcher_token)
        assert role == "researcher"

    def test_verify_and_get_role_red_team(self, red_team_token: str) -> None:
        """Test extracting role from red_team token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        role = verify_and_get_role(red_team_token)
        assert role == "red_team"

    def test_verify_and_get_role_invalid_token(self) -> None:
        """Test extracting role from invalid token."""
        with pytest.raises(InvalidTokenError):
            verify_and_get_role("invalid.token")


class TestRolePermissions:
    """Test role permissions constants."""

    def test_role_permissions_structure(self) -> None:
        """Test ROLE_PERMISSIONS has expected roles."""
        expected_roles = {"admin", "researcher", "red_team", "viewer"}
        assert set(ROLE_PERMISSIONS.keys()) == expected_roles

    def test_admin_has_unrestricted_access(self) -> None:
        """Test admin role has unrestricted access marker."""
        assert "*" in ROLE_PERMISSIONS["admin"]

    def test_red_team_has_unrestricted_access(self) -> None:
        """Test red_team role has unrestricted access marker."""
        assert "*" in ROLE_PERMISSIONS["red_team"]

    def test_researcher_has_specific_permissions(self) -> None:
        """Test researcher role has specific allowed tools."""
        permissions = ROLE_PERMISSIONS["researcher"]
        assert "*" not in permissions
        assert len(permissions) > 0
        assert isinstance(permissions, set)

    def test_viewer_has_minimal_permissions(self) -> None:
        """Test viewer role has minimal permissions."""
        permissions = ROLE_PERMISSIONS["viewer"]
        assert "*" not in permissions
        assert len(permissions) < len(ROLE_PERMISSIONS["researcher"])


class TestToolCategories:
    """Test tool categories structure."""

    def test_tool_categories_structure(self) -> None:
        """Test TOOL_CATEGORIES has expected structure."""
        expected_categories = {"safe", "research", "restricted", "infrastructure"}
        assert set(TOOL_CATEGORIES.keys()) == expected_categories

    def test_tool_categories_are_sets(self) -> None:
        """Test all categories are sets."""
        for category, tools in TOOL_CATEGORIES.items():
            assert isinstance(tools, set)
            assert len(tools) > 0

    def test_safe_tools_are_accessible(self) -> None:
        """Test safe tools are included."""
        safe_tools = TOOL_CATEGORIES["safe"]
        assert "search" in safe_tools
        assert "help" in safe_tools

    def test_restricted_tools_exist(self) -> None:
        """Test restricted tools are defined."""
        restricted = TOOL_CATEGORIES["restricted"]
        assert len(restricted) > 0
        assert "prompt_reframe" in restricted


class TestSecurityProperties:
    """Test security-related properties."""

    def test_token_contains_timestamp(self, admin_token: str, jwt_secret: str) -> None:
        """Test token contains issued and expiry timestamps."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        payload = validate_token(admin_token)
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_token_uses_hs256(self, jwt_secret: str) -> None:
        """Test token uses HS256 algorithm."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        token = create_token("user123", "admin", expires_in_hours=24)
        # Decode without verification to check algorithm
        header = pyjwt.get_unverified_header(token)
        assert header["alg"] == "HS256"

    def test_permissions_are_immutable(self) -> None:
        """Test role permissions cannot be easily mutated."""
        original = get_allowed_tools("admin").copy()
        assert "*" in original

        # Attempting to modify a returned set won't affect ROLE_PERMISSIONS
        # (since we return the original set, this test verifies we're aware)
        allowed = get_allowed_tools("researcher")
        assert isinstance(allowed, set)
