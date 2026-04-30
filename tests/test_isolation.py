"""Unit tests for customer data isolation module.

Tests:
- Customer cache directory isolation
- Customer audit directory isolation
- Customer session directory isolation
- Isolation verification for two customers
- Deterministic directory paths for same customer
- ID sanitization (special chars, path traversal, empty)
- Directory creation on access
- No data leakage between customers
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from loom.billing.isolation import (
    _sanitize_id,
    get_customer_audit_dir,
    get_customer_cache_dir,
    get_customer_session_dir,
    verify_isolation,
)


class TestSanitizeId:
    """Tests for _sanitize_id function."""

    def test_sanitize_removes_special_chars(self) -> None:
        """_sanitize_id replaces special chars with underscores."""
        result = _sanitize_id("customer@example.com")
        assert result == "customer_example_com"

    def test_sanitize_removes_slashes(self) -> None:
        """_sanitize_id removes forward slashes (path traversal prevention)."""
        result = _sanitize_id("customer/test")
        assert result == "customer_test"
        assert "/" not in result

    def test_sanitize_removes_backslashes(self) -> None:
        """_sanitize_id removes backslashes (Windows path traversal prevention)."""
        result = _sanitize_id("customer\\test")
        assert result == "customer_test"
        assert "\\" not in result

    def test_sanitize_removes_dots(self) -> None:
        """_sanitize_id removes dots (hidden file and parent dir traversal prevention)."""
        result = _sanitize_id(".git")
        assert result == "_git"
        assert "." not in result

    def test_sanitize_removes_double_dots(self) -> None:
        """_sanitize_id removes .. (parent directory traversal prevention)."""
        result = _sanitize_id("customer/../admin")
        assert ".." not in result
        # "/" -> "_", "." -> "_", so "/../" becomes "____"
        assert result == "customer____admin"

    def test_sanitize_keeps_alphanumeric(self) -> None:
        """_sanitize_id preserves alphanumeric characters."""
        result = _sanitize_id("customer123ABC")
        assert result == "customer123ABC"

    def test_sanitize_keeps_hyphen_underscore(self) -> None:
        """_sanitize_id preserves hyphens and underscores."""
        result = _sanitize_id("customer-test_id")
        assert result == "customer-test_id"

    def test_sanitize_enforces_max_length(self) -> None:
        """_sanitize_id truncates to max 64 characters."""
        long_id = "a" * 100
        result = _sanitize_id(long_id)
        assert len(result) == 64

    def test_sanitize_raises_on_empty_string(self) -> None:
        """_sanitize_id raises ValueError for empty string."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            _sanitize_id("")

    def test_sanitize_raises_on_none(self) -> None:
        """_sanitize_id raises ValueError for None."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            _sanitize_id(None)  # type: ignore

    def test_sanitize_produces_non_empty_result(self) -> None:
        """_sanitize_id produces non-empty result even with only special chars."""
        result = _sanitize_id("!@#$%^&*()")
        # All chars replaced with _, so we get 10 underscores
        assert result == "__________"
        assert result  # Not empty

    def test_sanitize_handles_mixed_special_chars(self) -> None:
        """_sanitize_id handles complex mixed special character input."""
        result = _sanitize_id("cust@#$%_-001")
        # @ -> _, # -> _, $ -> _, % -> _, _ stays, - stays, 001 stays
        assert result == "cust_____-001"
        assert all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in result)


class TestCustomerCacheDir:
    """Tests for get_customer_cache_dir function."""

    def test_cache_dir_returns_path(self) -> None:
        """get_customer_cache_dir returns a Path object."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = get_customer_cache_dir(base, "customer123")
            assert isinstance(result, Path)

    def test_cache_dir_is_created(self) -> None:
        """get_customer_cache_dir creates directory on access."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = get_customer_cache_dir(base, "customer123")
            assert result.exists()
            assert result.is_dir()

    def test_cache_dir_contains_customer_id(self) -> None:
        """get_customer_cache_dir includes sanitized customer ID in path."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = get_customer_cache_dir(base, "customer123")
            assert "customer123" in str(result)
            assert "customers" in str(result)

    def test_cache_dir_deterministic_for_same_customer(self) -> None:
        """get_customer_cache_dir returns same path for same customer."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            path1 = get_customer_cache_dir(base, "customer123")
            path2 = get_customer_cache_dir(base, "customer123")
            assert path1 == path2

    def test_cache_dir_different_for_different_customers(self) -> None:
        """get_customer_cache_dir returns different paths for different customers."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            path_a = get_customer_cache_dir(base, "customer_a")
            path_b = get_customer_cache_dir(base, "customer_b")
            assert path_a != path_b

    def test_cache_dir_raises_on_invalid_customer_id(self) -> None:
        """get_customer_cache_dir raises ValueError for invalid customer_id."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            with pytest.raises(ValueError):
                get_customer_cache_dir(base, "")


class TestCustomerAuditDir:
    """Tests for get_customer_audit_dir function."""

    def test_audit_dir_returns_path(self) -> None:
        """get_customer_audit_dir returns a Path object."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = get_customer_audit_dir(base, "customer123")
            assert isinstance(result, Path)

    def test_audit_dir_is_created(self) -> None:
        """get_customer_audit_dir creates directory on access."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = get_customer_audit_dir(base, "customer123")
            assert result.exists()
            assert result.is_dir()

    def test_audit_dir_contains_customer_id(self) -> None:
        """get_customer_audit_dir includes sanitized customer ID in path."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = get_customer_audit_dir(base, "customer123")
            assert "customer123" in str(result)
            assert "audit" in str(result)

    def test_audit_dir_deterministic_for_same_customer(self) -> None:
        """get_customer_audit_dir returns same path for same customer."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            path1 = get_customer_audit_dir(base, "customer123")
            path2 = get_customer_audit_dir(base, "customer123")
            assert path1 == path2

    def test_audit_dir_different_for_different_customers(self) -> None:
        """get_customer_audit_dir returns different paths for different customers."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            path_a = get_customer_audit_dir(base, "customer_a")
            path_b = get_customer_audit_dir(base, "customer_b")
            assert path_a != path_b

    def test_audit_dir_raises_on_invalid_customer_id(self) -> None:
        """get_customer_audit_dir raises ValueError for invalid customer_id."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            with pytest.raises(ValueError):
                get_customer_audit_dir(base, "")


class TestCustomerSessionDir:
    """Tests for get_customer_session_dir function."""

    def test_session_dir_returns_path(self) -> None:
        """get_customer_session_dir returns a Path object."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = get_customer_session_dir(base, "customer123")
            assert isinstance(result, Path)

    def test_session_dir_is_created(self) -> None:
        """get_customer_session_dir creates directory on access."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = get_customer_session_dir(base, "customer123")
            assert result.exists()
            assert result.is_dir()

    def test_session_dir_contains_customer_id(self) -> None:
        """get_customer_session_dir includes sanitized customer ID in path."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = get_customer_session_dir(base, "customer123")
            assert "customer123" in str(result)
            assert "sessions" in str(result)

    def test_session_dir_deterministic_for_same_customer(self) -> None:
        """get_customer_session_dir returns same path for same customer."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            path1 = get_customer_session_dir(base, "customer123")
            path2 = get_customer_session_dir(base, "customer123")
            assert path1 == path2

    def test_session_dir_different_for_different_customers(self) -> None:
        """get_customer_session_dir returns different paths for different customers."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            path_a = get_customer_session_dir(base, "customer_a")
            path_b = get_customer_session_dir(base, "customer_b")
            assert path_a != path_b

    def test_session_dir_raises_on_invalid_customer_id(self) -> None:
        """get_customer_session_dir raises ValueError for invalid customer_id."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            with pytest.raises(ValueError):
                get_customer_session_dir(base, "")


class TestVerifyIsolation:
    """Tests for verify_isolation function."""

    def test_verify_isolation_returns_dict(self) -> None:
        """verify_isolation returns a dict with required keys."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = verify_isolation(base, "customer_a", "customer_b")
            assert isinstance(result, dict)
            assert "isolated" in result
            assert "paths_a" in result
            assert "paths_b" in result

    def test_verify_isolation_two_customers_different_cache_dirs(self) -> None:
        """verify_isolation detects different cache dirs for two customers."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = verify_isolation(base, "customer_a", "customer_b")
            assert result["paths_a"]["cache"] != result["paths_b"]["cache"]

    def test_verify_isolation_two_customers_different_audit_dirs(self) -> None:
        """verify_isolation detects different audit dirs for two customers."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = verify_isolation(base, "customer_a", "customer_b")
            assert result["paths_a"]["audit"] != result["paths_b"]["audit"]

    def test_verify_isolation_two_customers_different_session_dirs(self) -> None:
        """verify_isolation detects different session dirs for two customers."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = verify_isolation(base, "customer_a", "customer_b")
            assert result["paths_a"]["session"] != result["paths_b"]["session"]

    def test_verify_isolation_returns_true_for_different_customers(self) -> None:
        """verify_isolation returns isolated=True for different customers."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = verify_isolation(base, "customer_a", "customer_b")
            assert result["isolated"] is True

    def test_verify_isolation_no_path_containment(self) -> None:
        """verify_isolation ensures no customer dir is prefix of another."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = verify_isolation(base, "customer_a", "customer_b")
            paths_a = result["paths_a"]
            paths_b = result["paths_b"]

            for key in paths_a:
                path_a = paths_a[key]
                path_b = paths_b[key]
                # Neither should be a prefix of the other
                assert not path_a.startswith(path_b)
                assert not path_b.startswith(path_a)

    def test_verify_isolation_includes_all_path_types(self) -> None:
        """verify_isolation includes cache, audit, and session paths."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            result = verify_isolation(base, "customer_a", "customer_b")
            assert set(result["paths_a"].keys()) == {"cache", "audit", "session"}
            assert set(result["paths_b"].keys()) == {"cache", "audit", "session"}

    def test_verify_isolation_raises_on_invalid_customer_a(self) -> None:
        """verify_isolation raises ValueError if customer_a is invalid."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            with pytest.raises(ValueError):
                verify_isolation(base, "", "customer_b")

    def test_verify_isolation_raises_on_invalid_customer_b(self) -> None:
        """verify_isolation raises ValueError if customer_b is invalid."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            with pytest.raises(ValueError):
                verify_isolation(base, "customer_a", "")


class TestDataIsolation:
    """Tests for actual data isolation (no cross-customer leakage)."""

    def test_data_in_customer_a_cache_not_visible_in_customer_b(self) -> None:
        """Data written to customer A's cache is not visible in customer B's cache."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)

            # Write data to customer A's cache
            cache_dir_a = get_customer_cache_dir(base, "customer_a")
            test_file_a = cache_dir_a / "test_data.json"
            test_file_a.write_text(json.dumps({"customer": "a", "data": "secret"}))

            # Check customer B's cache doesn't contain customer A's data
            cache_dir_b = get_customer_cache_dir(base, "customer_b")
            test_file_b = cache_dir_b / "test_data.json"
            assert not test_file_b.exists()

    def test_data_in_customer_a_audit_not_visible_in_customer_b(self) -> None:
        """Data written to customer A's audit is not visible in customer B's audit."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)

            # Write data to customer A's audit
            audit_dir_a = get_customer_audit_dir(base, "customer_a")
            test_file_a = audit_dir_a / "audit_log.json"
            test_file_a.write_text(json.dumps({"customer": "a", "action": "secret"}))

            # Check customer B's audit doesn't contain customer A's data
            audit_dir_b = get_customer_audit_dir(base, "customer_b")
            test_file_b = audit_dir_b / "audit_log.json"
            assert not test_file_b.exists()

    def test_data_in_customer_a_session_not_visible_in_customer_b(self) -> None:
        """Data written to customer A's session is not visible in customer B's session."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)

            # Write data to customer A's session
            session_dir_a = get_customer_session_dir(base, "customer_a")
            test_file_a = session_dir_a / "session.db"
            test_file_a.write_text("customer_a_session_data")

            # Check customer B's session doesn't contain customer A's data
            session_dir_b = get_customer_session_dir(base, "customer_b")
            test_file_b = session_dir_b / "session.db"
            assert not test_file_b.exists()

    def test_multiple_customers_all_isolated(self) -> None:
        """Multiple customers all have isolated data paths."""
        with TemporaryDirectory(prefix="loom_isolation_") as tmpdir:
            base = Path(tmpdir)
            customers = ["customer_a", "customer_b", "customer_c"]

            # Write unique data to each customer's cache
            for customer in customers:
                cache_dir = get_customer_cache_dir(base, customer)
                test_file = cache_dir / "data.json"
                test_file.write_text(json.dumps({"customer": customer}))

            # Verify each customer only sees their own data
            for customer in customers:
                cache_dir = get_customer_cache_dir(base, customer)
                test_file = cache_dir / "data.json"
                data = json.loads(test_file.read_text())
                assert data["customer"] == customer

                # Verify this customer doesn't see others' data
                for other in customers:
                    if other != customer:
                        other_cache_dir = get_customer_cache_dir(base, other)
                        other_file = other_cache_dir / "data.json"
                        # Verify paths are different
                        assert cache_dir != other_cache_dir
