"""Unit tests for billing module — customers, API keys, and credit weights.

Tests:
- Customer creation with API key generation
- API key validation and authentication
- Key revocation and rotation
- Credit weight calculations
- Credit balance checking and deduction
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from loom.billing.credits import (
    DEFAULT_WEIGHT,
    check_balance,
    deduct,
    get_tool_cost,
)
from loom.billing.customers import (
    create_customer,
    get_customer,
    list_customers,
    revoke_key,
    rotate_key,
    update_credits,
    validate_key,
)


class TestCustomerCreation:
    """Tests for customer creation and API key generation."""

    def test_create_customer_returns_api_key_with_live_prefix(self) -> None:
        """create_customer returns api_key with loom_live_ prefix."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                result = create_customer("Test User", "test@example.com", "free")

                assert "api_key" in result
                assert result["api_key"].startswith("loom_live_")
                assert "customer_id" in result
                assert result["tier"] == "free"

    def test_create_customer_generates_unique_ids(self) -> None:
        """create_customer generates unique customer IDs."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                result1 = create_customer("User 1", "user1@example.com", "free")
                result2 = create_customer("User 2", "user2@example.com", "free")

                assert result1["customer_id"] != result2["customer_id"]

    def test_create_customer_stores_in_json(self) -> None:
        """create_customer atomically saves to customers.json."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                result = create_customer("Test User", "test@example.com", "pro")

                assert customers_file.exists()
                data = json.loads(customers_file.read_text())
                customer_id = result["customer_id"]
                assert customer_id in data
                assert data[customer_id]["email"] == "test@example.com"
                assert data[customer_id]["tier"] == "pro"

    def test_create_customer_tier_free_credits_500(self) -> None:
        """create_customer tier=free grants 500 credits."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                result = create_customer("User", "user@example.com", "free")
                customer_id = result["customer_id"]

                data = json.loads(customers_file.read_text())
                assert data[customer_id]["credits"] == 500

    def test_create_customer_tier_pro_credits_10k(self) -> None:
        """create_customer tier=pro grants 10,000 credits."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                result = create_customer("User", "user@example.com", "pro")
                customer_id = result["customer_id"]

                data = json.loads(customers_file.read_text())
                assert data[customer_id]["credits"] == 10_000

    def test_create_customer_tier_team_credits_50k(self) -> None:
        """create_customer tier=team grants 50,000 credits."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                result = create_customer("User", "user@example.com", "team")
                customer_id = result["customer_id"]

                data = json.loads(customers_file.read_text())
                assert data[customer_id]["credits"] == 50_000

    def test_create_customer_tier_enterprise_credits_200k(self) -> None:
        """create_customer tier=enterprise grants 200,000 credits."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                result = create_customer("User", "user@example.com", "enterprise")
                customer_id = result["customer_id"]

                data = json.loads(customers_file.read_text())
                assert data[customer_id]["credits"] == 200_000

    def test_create_customer_invalid_tier_raises(self) -> None:
        """create_customer raises ValueError for invalid tier."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                with pytest.raises(ValueError, match="Invalid tier"):
                    create_customer("User", "user@example.com", "invalid")


class TestAPIKeyValidation:
    """Tests for API key validation and authentication."""

    def test_validate_key_finds_valid_customer(self) -> None:
        """validate_key returns customer info for valid key."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                create_result = create_customer("Test User", "test@example.com")
                api_key = create_result["api_key"]

                validated = validate_key(api_key)
                assert validated is not None
                assert validated["customer_id"] == create_result["customer_id"]
                assert validated["email"] == "test@example.com"

    def test_validate_key_returns_none_for_invalid_key(self) -> None:
        """validate_key returns None for invalid/unknown key."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                create_customer("Test User", "test@example.com")

                validated = validate_key("loom_live_invalid_key_xyz")
                assert validated is None

    def test_validate_key_returns_none_for_empty_database(self) -> None:
        """validate_key returns None when no customers exist."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                validated = validate_key("loom_live_any_key")
                assert validated is None

    def test_validate_key_returns_none_for_revoked_customer(self) -> None:
        """validate_key returns None for revoked customer keys."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                create_result = create_customer("Test User", "test@example.com")
                api_key = create_result["api_key"]
                customer_id = create_result["customer_id"]

                # Verify key works before revoke
                assert validate_key(api_key) is not None

                # Revoke the key
                revoke_key(customer_id)

                # Now validation should fail
                validated = validate_key(api_key)
                assert validated is None


class TestKeyManagement:
    """Tests for key revocation and rotation."""

    def test_revoke_key_makes_key_invalid(self) -> None:
        """revoke_key marks customer inactive, invalidating their key."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                create_result = create_customer("Test User", "test@example.com")
                api_key = create_result["api_key"]
                customer_id = create_result["customer_id"]

                # Revoke
                revoked = revoke_key(customer_id)
                assert revoked is True

                # Key should no longer validate
                validated = validate_key(api_key)
                assert validated is None

    def test_revoke_key_returns_false_for_unknown_customer(self) -> None:
        """revoke_key returns False if customer not found."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                result = revoke_key("nonexistent_customer_id")
                assert result is False

    def test_rotate_key_generates_new_api_key(self) -> None:
        """rotate_key generates a new api_key with loom_live_ prefix."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                create_result = create_customer("Test User", "test@example.com")
                old_api_key = create_result["api_key"]
                customer_id = create_result["customer_id"]

                rotate_result = rotate_key(customer_id)
                assert rotate_result is not None
                new_api_key = rotate_result["api_key"]

                # New key should be different
                assert new_api_key != old_api_key
                assert new_api_key.startswith("loom_live_")

                # Old key should no longer work
                assert validate_key(old_api_key) is None

                # New key should work
                assert validate_key(new_api_key) is not None

    def test_rotate_key_returns_none_for_unknown_customer(self) -> None:
        """rotate_key returns None if customer not found."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                result = rotate_key("nonexistent_customer_id")
                assert result is None


class TestCreditWeights:
    """Tests for credit weight calculations."""

    def test_get_tool_cost_light_tool_search_1_credit(self) -> None:
        """get_tool_cost returns 1 for light tool 'search'."""
        assert get_tool_cost("search") == 1
        assert get_tool_cost("research_search") == 1

    def test_get_tool_cost_light_tool_text_analyze_1_credit(self) -> None:
        """get_tool_cost returns 1 for light tool 'text_analyze'."""
        assert get_tool_cost("text_analyze") == 1
        assert get_tool_cost("research_text_analyze") == 1

    def test_get_tool_cost_medium_tool_fetch_3_credits(self) -> None:
        """get_tool_cost returns 3 for medium tool 'fetch'."""
        assert get_tool_cost("fetch") == 3
        assert get_tool_cost("research_fetch") == 3

    def test_get_tool_cost_medium_tool_spider_3_credits(self) -> None:
        """get_tool_cost returns 3 for medium tool 'spider'."""
        assert get_tool_cost("spider") == 3
        assert get_tool_cost("research_spider") == 3

    def test_get_tool_cost_heavy_tool_deep_10_credits(self) -> None:
        """get_tool_cost returns 10 for heavy tool 'deep'."""
        assert get_tool_cost("deep") == 10
        assert get_tool_cost("research_deep") == 10

    def test_get_tool_cost_heavy_tool_dark_forum_10_credits(self) -> None:
        """get_tool_cost returns 10 for heavy tool 'dark_forum'."""
        assert get_tool_cost("dark_forum") == 10
        assert get_tool_cost("research_dark_forum") == 10

    def test_get_tool_cost_unknown_tool_returns_default_2_credits(self) -> None:
        """get_tool_cost returns DEFAULT_WEIGHT for unknown tools."""
        assert get_tool_cost("unknown_tool") == DEFAULT_WEIGHT
        assert get_tool_cost("research_unknown_tool") == DEFAULT_WEIGHT
        assert DEFAULT_WEIGHT == 2


class TestCreditBalance:
    """Tests for credit balance checking and deduction."""

    def test_check_balance_true_when_sufficient_credits(self) -> None:
        """check_balance returns True when sufficient credits."""
        assert check_balance(10, "search") is True  # 10 >= 1
        assert check_balance(5, "fetch") is True  # 5 >= 3
        assert check_balance(10, "deep") is True  # 10 >= 10

    def test_check_balance_false_when_insufficient_credits(self) -> None:
        """check_balance returns False when insufficient credits."""
        assert check_balance(0, "search") is False  # 0 < 1
        assert check_balance(2, "fetch") is False  # 2 < 3
        assert check_balance(9, "deep") is False  # 9 < 10

    def test_check_balance_exact_credits(self) -> None:
        """check_balance returns True when credits exactly equal cost."""
        assert check_balance(1, "search") is True  # 1 == 1
        assert check_balance(3, "fetch") is True  # 3 == 3
        assert check_balance(10, "deep") is True  # 10 == 10

    def test_deduct_reduces_credits_correctly(self) -> None:
        """deduct reduces balance by tool cost correctly."""
        remaining, cost = deduct(10, "search")
        assert cost == 1
        assert remaining == 9

    def test_deduct_medium_tool(self) -> None:
        """deduct calculates correct remaining for medium tool."""
        remaining, cost = deduct(10, "fetch")
        assert cost == 3
        assert remaining == 7

    def test_deduct_heavy_tool(self) -> None:
        """deduct calculates correct remaining for heavy tool."""
        remaining, cost = deduct(10, "deep")
        assert cost == 10
        assert remaining == 0

    def test_deduct_no_negative_balance(self) -> None:
        """deduct never returns negative remaining balance."""
        remaining, cost = deduct(2, "fetch")  # 2 < 3, would go negative
        assert cost == 3
        assert remaining == 0  # Clamps to 0, doesn't go negative

    def test_deduct_returns_cost(self) -> None:
        """deduct returns actual cost charged."""
        _, cost = deduct(100, "research_search")
        assert cost == 1

        _, cost = deduct(100, "research_fetch")
        assert cost == 3

        _, cost = deduct(100, "research_deep")
        assert cost == 10


class TestCustomerQueries:
    """Tests for customer info and listing."""

    def test_get_customer_returns_info(self) -> None:
        """get_customer returns customer info by ID."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                create_result = create_customer("Test User", "test@example.com", "pro")
                customer_id = create_result["customer_id"]

                info = get_customer(customer_id)
                assert info is not None
                assert info["email"] == "test@example.com"
                assert info["tier"] == "pro"

    def test_get_customer_returns_none_for_unknown_id(self) -> None:
        """get_customer returns None if customer not found."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                info = get_customer("nonexistent_id")
                assert info is None

    def test_list_customers_returns_all(self) -> None:
        """list_customers returns all customers."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                create_customer("User 1", "user1@example.com", "free")
                create_customer("User 2", "user2@example.com", "pro")

                customers = list_customers()
                assert len(customers) == 2
                assert all("customer_id" in c for c in customers)
                assert all("email" in c for c in customers)

    def test_list_customers_does_not_expose_key_hash(self) -> None:
        """list_customers excludes api_key hash for security."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                create_customer("User", "user@example.com")

                customers = list_customers()
                assert len(customers) == 1
                assert "api_key" not in customers[0]


class TestCreditUpdates:
    """Tests for credit balance updates."""

    def test_update_credits_increases_balance(self) -> None:
        """update_credits increases customer's credits."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                create_result = create_customer("User", "user@example.com", "free")
                customer_id = create_result["customer_id"]

                update_credits(customer_id, 100)

                info = get_customer(customer_id)
                assert info["credits"] == 600  # 500 + 100

    def test_update_credits_decreases_balance(self) -> None:
        """update_credits decreases customer's credits."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                create_result = create_customer("User", "user@example.com", "free")
                customer_id = create_result["customer_id"]

                update_credits(customer_id, -200)

                info = get_customer(customer_id)
                assert info["credits"] == 300  # 500 - 200

    def test_update_credits_clamps_to_zero(self) -> None:
        """update_credits never goes below zero."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                create_result = create_customer("User", "user@example.com", "free")
                customer_id = create_result["customer_id"]

                update_credits(customer_id, -1000)  # Try to go negative

                info = get_customer(customer_id)
                assert info["credits"] == 0  # Clamped to 0

    def test_update_credits_returns_false_for_unknown_customer(self) -> None:
        """update_credits returns False if customer not found."""
        with TemporaryDirectory(prefix="loom_billing_") as tmpdir:
            customers_file = Path(tmpdir) / "customers.json"
            with patch("loom.billing.customers._CUSTOMERS_FILE", customers_file):
                result = update_credits("nonexistent_id", 100)
                assert result is False
