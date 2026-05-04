"""Tests for Stripe integration with idempotency.

Tests cover:
- Charge creation with idempotency keys
- Subscription creation with idempotency keys
- Checkout session creation with idempotency keys
- Parameter validation
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from loom.billing.stripe_integration import StripeIntegration, TIER_PRICE_MAP


class TestStripeIntegrationInitialization:
    """Test Stripe integration initialization."""

    def test_init_with_provided_key(self) -> None:
        """Test initialization with provided API key."""
        stripe = StripeIntegration(api_key="sk_test_12345")
        assert stripe.api_key == "sk_test_12345"

    def test_init_from_env_var(self) -> None:
        """Test initialization from STRIPE_LIVE_KEY env var."""
        with patch.dict(os.environ, {"STRIPE_LIVE_KEY": "sk_test_env"}):
            stripe = StripeIntegration()
            assert stripe.api_key == "sk_test_env"

    def test_init_raises_without_key(self) -> None:
        """Test initialization raises ValueError when no key available."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Stripe API key required"):
                StripeIntegration()


class TestCreateChargeWithIdempotency:
    """Test create_charge with idempotency keys."""

    @pytest.mark.asyncio
    async def test_create_charge_with_provided_idempotency_key(self) -> None:
        """Test charge creation includes provided idempotency key."""
        stripe = StripeIntegration(api_key="sk_test_123")

        # Mock the httpx client
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "ii_test_123",
            "customer": "cust_456",
            "amount": 9999,
            "description": "Test charge",
            "created": 1700000000,
        }

        with patch.object(stripe, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await stripe.create_charge(
                "cust_456",
                9999,
                "Test charge",
                idempotency_key="test_idempotency_key_abcd1234",
            )

            # Verify the idempotency key was passed
            assert mock_client.post.called
            call_kwargs = mock_client.post.call_args[1]
            assert "headers" in call_kwargs
            assert call_kwargs["headers"].get("Idempotency-Key") == "test_idempotency_key_abcd1234"

            # Verify result includes idempotency key
            assert result["idempotency_key"] == "test_idempotency_key_abcd1234"

    @pytest.mark.asyncio
    async def test_create_charge_without_idempotency_key(self) -> None:
        """Test charge creation without idempotency key."""
        stripe = StripeIntegration(api_key="sk_test_456")

        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "ii_test_456",
            "customer": "cust_789",
            "amount": 5000,
            "description": "No idempotency charge",
            "created": 1700000100,
        }

        with patch.object(stripe, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await stripe.create_charge(
                "cust_789",
                5000,
                "No idempotency charge",
            )

            # Verify result includes "not_provided"
            assert result["idempotency_key"] == "not_provided"

    @pytest.mark.asyncio
    async def test_create_charge_validates_amount(self) -> None:
        """Test charge creation validates positive amount."""
        stripe = StripeIntegration(api_key="sk_test_789")

        with pytest.raises(ValueError, match="Charge amount must be positive"):
            await stripe.create_charge("cust_999", 0, "Invalid charge")

        with pytest.raises(ValueError, match="Charge amount must be positive"):
            await stripe.create_charge("cust_999", -100, "Negative charge")


class TestCreateSubscriptionWithIdempotency:
    """Test create_subscription with idempotency keys."""

    @pytest.mark.asyncio
    async def test_create_subscription_with_idempotency_key(self) -> None:
        """Test subscription creation includes idempotency key."""
        stripe = StripeIntegration(api_key="sk_test_sub")

        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "sub_test_123",
            "customer": "cust_sub_123",
            "status": "active",
            "current_period_start": 1700000000,
            "current_period_end": 1702678400,
        }

        with patch.object(stripe, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await stripe.create_subscription(
                "cust_sub_123",
                "pro",
                idempotency_key="sub_idem_key_xyz",
            )

            # Verify idempotency key was passed
            call_kwargs = mock_client.post.call_args[1]
            assert call_kwargs["headers"].get("Idempotency-Key") == "sub_idem_key_xyz"

            assert result["tier"] == "pro"
            assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_subscription_rejects_free_tier(self) -> None:
        """Test subscription creation rejects free tier."""
        stripe = StripeIntegration(api_key="sk_test_free")

        with pytest.raises(ValueError, match="Cannot create Stripe subscription for free tier"):
            await stripe.create_subscription("cust_free", "free")

    @pytest.mark.asyncio
    async def test_create_subscription_validates_tier(self) -> None:
        """Test subscription creation validates tier."""
        stripe = StripeIntegration(api_key="sk_test_tier")

        with pytest.raises(ValueError, match="Invalid tier"):
            await stripe.create_subscription("cust_invalid", "premium")


class TestCreateCheckoutSessionWithIdempotency:
    """Test create_checkout_session with idempotency keys."""

    @pytest.mark.asyncio
    async def test_create_checkout_session_with_idempotency_key(self) -> None:
        """Test checkout session creation includes idempotency key."""
        stripe = StripeIntegration(api_key="sk_test_checkout")

        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "cs_test_123",
            "url": "https://checkout.stripe.com/session/cs_test_123",
            "customer": "cust_checkout_123",
            "status": "open",
        }

        with patch.object(stripe, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await stripe.create_checkout_session(
                "cust_checkout_123",
                "team",
                "https://example.com/success",
                "https://example.com/cancel",
                idempotency_key="checkout_idem_abc123",
            )

            # Verify idempotency key was passed
            call_kwargs = mock_client.post.call_args[1]
            assert call_kwargs["headers"].get("Idempotency-Key") == "checkout_idem_abc123"

            assert result["status"] == "open"
            assert result["tier"] == "team"

    @pytest.mark.asyncio
    async def test_create_checkout_session_rejects_free_tier(self) -> None:
        """Test checkout session creation rejects free tier."""
        stripe = StripeIntegration(api_key="sk_test_co_free")

        with pytest.raises(ValueError, match="Cannot create checkout session for free tier"):
            await stripe.create_checkout_session(
                "cust_free",
                "free",
                "https://example.com/success",
                "https://example.com/cancel",
            )


class TestStripeContextManager:
    """Test Stripe context manager functionality."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Test Stripe integration works as async context manager."""
        async with StripeIntegration(api_key="sk_test_ctx") as stripe:
            assert stripe.api_key == "sk_test_ctx"
