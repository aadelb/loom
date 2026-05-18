"""Tests for JWT middleware JTI revocation checks."""
from __future__ import annotations

import os

import pytest

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None


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
    from loom.jwt_auth import create_token

    return create_token("admin-user", "admin", expires_in_hours=24)


class TestMiddlewareJtiCheck:
    """Test that middleware checks JTI against revocation set."""

    def test_require_auth_allows_valid_token(self, admin_token: str) -> None:
        """Test @require_auth allows a valid unrevoked token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        from loom.jwt_middleware import require_auth

        @require_auth(require_role="admin")
        def protected_func() -> str:
            return "ok"

        result = protected_func(_jwt_token=admin_token)
        assert result == "ok"

    def test_require_auth_blocks_revoked_token(self, admin_token: str) -> None:
        """Test @require_auth blocks a revoked token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        from loom.jwt_auth import revoke_jti, validate_token
        from loom.jwt_middleware import require_auth
        from loom.jwt_auth import InvalidTokenError

        payload = validate_token(admin_token)
        revoke_jti(payload["jti"])

        @require_auth(require_role="admin")
        def protected_func() -> str:
            return "ok"

        with pytest.raises(InvalidTokenError, match="revoked"):
            protected_func(_jwt_token=admin_token)

    def test_authorized_wrapper_allows_valid_token(self, admin_token: str) -> None:
        """Test create_authorized_wrapper allows a valid unrevoked token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        from loom.jwt_middleware import create_authorized_wrapper

        def my_tool() -> str:
            return "ok"

        wrapped = create_authorized_wrapper(my_tool)
        result = wrapped(_jwt_token=admin_token)
        assert result == "ok"

    def test_authorized_wrapper_blocks_revoked_token(self, admin_token: str) -> None:
        """Test create_authorized_wrapper blocks a revoked token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        from loom.jwt_auth import InvalidTokenError, revoke_jti, validate_token
        from loom.jwt_middleware import create_authorized_wrapper

        payload = validate_token(admin_token)
        revoke_jti(payload["jti"])

        def my_tool() -> str:
            return "ok"

        wrapped = create_authorized_wrapper(my_tool)
        with pytest.raises(InvalidTokenError, match="revoked"):
            wrapped(_jwt_token=admin_token)

    def test_async_wrapper_allows_valid_token(self, admin_token: str) -> None:
        """Test async wrapper allows a valid unrevoked token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        from loom.jwt_middleware import require_auth

        @require_auth(require_role="admin")
        async def async_protected() -> str:
            return "ok"

        import asyncio

        result = asyncio.run(async_protected(_jwt_token=admin_token))
        assert result == "ok"

    def test_async_wrapper_blocks_revoked_token(self, admin_token: str) -> None:
        """Test async wrapper blocks a revoked token."""
        if pyjwt is None:
            pytest.skip("PyJWT not installed")

        from loom.jwt_auth import InvalidTokenError, revoke_jti, validate_token
        from loom.jwt_middleware import require_auth

        payload = validate_token(admin_token)
        revoke_jti(payload["jti"])

        @require_auth(require_role="admin")
        async def async_protected() -> str:
            return "ok"

        import asyncio

        with pytest.raises(InvalidTokenError, match="revoked"):
            asyncio.run(async_protected(_jwt_token=admin_token))

    def test_refresh_token_imported_in_middleware(self) -> None:
        """Test that refresh_token is available from jwt_middleware module."""
        from loom.jwt_middleware import refresh_token

        assert callable(refresh_token)
