"""Tests for Stripe integration module.

Tests cover:
- Subscription creation and tier mapping
- One-time charge creation
- Invoice retrieval
- Subscription cancellation
- Invoice listing
- Checkout session creation
- Error handling (missing API key, invalid tiers, etc.)
- All HTTP calls are mocked (never hit real Stripe)
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from loom.billing.stripe_integration import (
    StripeIntegration,
    TIER_PRICE_MAP,
    TIER_PRICE_USD,
)
from loom.params import (
    StripeCreateChargeParams,
    StripeCreateCheckoutParams,
    StripeCreateSubscriptionParams,
    StripeCancelSubscriptionParams,
    StripeGetInvoiceParams,
    StripeListInvoicesParams,
)


@pytest.fixture
def stripe_api_key() -> str:
    """Provide a test Stripe API key."""
    return "sk_test_abcdef123456"


@pytest.fixture
async def stripe_integration(stripe_api_key: str) -> StripeIntegration:
    """Provide a Stripe integration instance with test API key."""
    return StripeIntegration(api_key=stripe_api_key)


class TestStripeInitialization:
    """Test Stripe integration initialization."""

    def test_init_with_explicit_api_key(self, stripe_api_key: str) -> None:
        """Should accept explicit API key."""
        stripe = StripeIntegration(api_key=stripe_api_key)
        assert stripe.api_key == stripe_api_key

    def test_init_with_env_variable(self) -> None:
        """Should read API key from environment variable."""
        os.environ["STRIPE_LIVE_KEY"] = "sk_test_env_key"
        try:
            stripe = StripeIntegration()
            assert stripe.api_key == "sk_test_env_key"
        finally:
            del os.environ["STRIPE_LIVE_KEY"]

    def test_init_missing_api_key(self) -> None:
        """Should raise ValueError if no API key provided."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Stripe API key required"):
                StripeIntegration()

    def test_lazy_client_init(self, stripe_api_key: str) -> None:
        """Should not initialize httpx client on __init__."""
        stripe = StripeIntegration(api_key=stripe_api_key)
        assert stripe._client is None


class TestSubscriptionCreation:
    """Test subscription creation."""

    @pytest.mark.asyncio
    async def test_create_subscription_pro(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should create pro subscription."""
        customer_id = "cus_test_123"
        tier = "pro"

        mock_response = {
            "id": "sub_test_pro_123",
            "customer": customer_id,
            "status": "active",
            "current_period_start": 1700000000,
            "current_period_end": 1702678400,
        }

        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            result = await stripe_integration.create_subscription(customer_id, tier)

            assert result["id"] == "sub_test_pro_123"
            assert result["customer"] == customer_id
            assert result["tier"] == "pro"
            assert result["price_id"] == "price_pro"
            assert result["status"] == "active"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_subscription_team(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should create team subscription."""
        customer_id = "cus_test_456"
        tier = "team"

        mock_response = {
            "id": "sub_test_team_456",
            "customer": customer_id,
            "status": "active",
            "current_period_start": 1700000000,
            "current_period_end": 1702678400,
        }

        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            result = await stripe_integration.create_subscription(customer_id, tier)

            assert result["id"] == "sub_test_team_456"
            assert result["tier"] == "team"
            assert result["price_id"] == "price_team"

    @pytest.mark.asyncio
    async def test_create_subscription_enterprise(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should create enterprise subscription."""
        customer_id = "cus_test_789"
        tier = "enterprise"

        mock_response = {
            "id": "sub_test_ent_789",
            "customer": customer_id,
            "status": "active",
            "current_period_start": 1700000000,
            "current_period_end": 1702678400,
        }

        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            result = await stripe_integration.create_subscription(customer_id, tier)

            assert result["id"] == "sub_test_ent_789"
            assert result["tier"] == "enterprise"
            assert result["price_id"] == "price_enterprise"

    @pytest.mark.asyncio
    async def test_create_subscription_free_tier_fails(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should reject free tier."""
        with pytest.raises(ValueError, match="Cannot create Stripe subscription"):
            await stripe_integration.create_subscription("cus_test", "free")

    @pytest.mark.asyncio
    async def test_create_subscription_invalid_tier_fails(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should reject invalid tier."""
        with pytest.raises(ValueError, match="Invalid tier"):
            await stripe_integration.create_subscription("cus_test", "invalid")

    @pytest.mark.asyncio
    async def test_create_subscription_api_error(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should propagate HTTP errors."""
        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.post.side_effect = httpx.HTTPError("API error")
            mock_get_client.return_value = mock_client

            with pytest.raises(httpx.HTTPError):
                await stripe_integration.create_subscription("cus_test", "pro")


class TestChargeCreation:
    """Test one-time charge creation."""

    @pytest.mark.asyncio
    async def test_create_charge(self, stripe_integration: StripeIntegration) -> None:
        """Should create overage charge."""
        customer_id = "cus_test_123"
        amount_cents = 9999
        description = "Overage charges for April"

        mock_response = {
            "id": "ii_test_123",
            "customer": customer_id,
            "amount": amount_cents,
            "description": description,
            "created": 1700000000,
        }

        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            result = await stripe_integration.create_charge(
                customer_id, amount_cents, description
            )

            assert result["id"] == "ii_test_123"
            assert result["customer"] == customer_id
            assert result["amount"] == amount_cents
            assert result["description"] == description

    @pytest.mark.asyncio
    async def test_create_charge_zero_amount_fails(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should reject zero or negative amounts."""
        with pytest.raises(ValueError, match="must be positive"):
            await stripe_integration.create_charge("cus_test", 0, "desc")

        with pytest.raises(ValueError, match="must be positive"):
            await stripe_integration.create_charge("cus_test", -100, "desc")

    @pytest.mark.asyncio
    async def test_create_charge_api_error(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should propagate HTTP errors."""
        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.post.side_effect = httpx.HTTPError("API error")
            mock_get_client.return_value = mock_client

            with pytest.raises(httpx.HTTPError):
                await stripe_integration.create_charge("cus_test", 9999, "charge")


class TestInvoiceRetrieval:
    """Test invoice retrieval."""

    @pytest.mark.asyncio
    async def test_get_invoice(self, stripe_integration: StripeIntegration) -> None:
        """Should retrieve invoice details."""
        invoice_id = "in_test_123"

        mock_response = {
            "id": invoice_id,
            "customer": "cus_test_123",
            "amount_paid": 9999,
            "amount_remaining": 0,
            "total": 9999,
            "status": "paid",
            "created": 1700000000,
            "due_date": 1700604800,
            "paid": True,
        }

        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            result = await stripe_integration.get_invoice(invoice_id)

            assert result["id"] == invoice_id
            assert result["status"] == "paid"
            assert result["paid"] is True
            assert result["amount_paid"] == 9999

    @pytest.mark.asyncio
    async def test_get_invoice_not_found(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should propagate 404 errors."""
        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=None, response=None
            )
            mock_client.get.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await stripe_integration.get_invoice("in_invalid")


class TestSubscriptionCancellation:
    """Test subscription cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_subscription(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should cancel subscription."""
        subscription_id = "sub_test_123"

        mock_response = {
            "id": subscription_id,
            "customer": "cus_test_123",
            "status": "canceled",
            "canceled_at": 1700000000,
        }

        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.delete.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            result = await stripe_integration.cancel_subscription(subscription_id)

            assert result["id"] == subscription_id
            assert result["status"] == "canceled"
            assert result["canceled_at"] == 1700000000

    @pytest.mark.asyncio
    async def test_cancel_subscription_api_error(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should propagate HTTP errors."""
        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.delete.side_effect = httpx.HTTPError("API error")
            mock_get_client.return_value = mock_client

            with pytest.raises(httpx.HTTPError):
                await stripe_integration.cancel_subscription("sub_test")


class TestInvoiceListing:
    """Test invoice listing."""

    @pytest.mark.asyncio
    async def test_list_invoices(self, stripe_integration: StripeIntegration) -> None:
        """Should list customer invoices."""
        customer_id = "cus_test_123"

        mock_response = {
            "data": [
                {
                    "id": "in_test_001",
                    "customer": customer_id,
                    "amount_paid": 9999,
                    "total": 9999,
                    "status": "paid",
                    "created": 1700000000,
                    "paid": True,
                },
                {
                    "id": "in_test_002",
                    "customer": customer_id,
                    "amount_paid": 0,
                    "total": 29900,
                    "status": "open",
                    "created": 1700086400,
                    "paid": False,
                },
            ],
            "has_more": False,
        }

        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            result = await stripe_integration.list_invoices(customer_id)

            assert len(result) == 2
            assert result[0]["id"] == "in_test_001"
            assert result[0]["status"] == "paid"
            assert result[1]["id"] == "in_test_002"
            assert result[1]["paid"] is False

    @pytest.mark.asyncio
    async def test_list_invoices_custom_limit(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should respect custom limit."""
        customer_id = "cus_test_123"
        limit = 25

        mock_response = {"data": [], "has_more": False}

        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            await stripe_integration.list_invoices(customer_id, limit=limit)

            call_args = mock_client.get.call_args
            assert call_args[1]["params"]["limit"] == limit

    @pytest.mark.asyncio
    async def test_list_invoices_invalid_limit(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should reject invalid limits."""
        with pytest.raises(ValueError, match="must be 1-100"):
            await stripe_integration.list_invoices("cus_test", limit=0)

        with pytest.raises(ValueError, match="must be 1-100"):
            await stripe_integration.list_invoices("cus_test", limit=101)

    @pytest.mark.asyncio
    async def test_list_invoices_empty(self, stripe_integration: StripeIntegration) -> None:
        """Should handle empty invoice list."""
        customer_id = "cus_test_new"

        mock_response = {"data": [], "has_more": False}

        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            result = await stripe_integration.list_invoices(customer_id)

            assert result == []


class TestCheckoutSessionCreation:
    """Test Checkout session creation."""

    @pytest.mark.asyncio
    async def test_create_checkout_session_pro(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should create pro checkout session."""
        customer_id = "cus_test_123"
        tier = "pro"
        success_url = "https://example.com/success"
        cancel_url = "https://example.com/cancel"

        mock_response = {
            "id": "cs_test_pro_123",
            "url": "https://checkout.stripe.com/pay/cs_test_pro_123",
            "customer": customer_id,
            "status": "open",
        }

        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            result = await stripe_integration.create_checkout_session(
                customer_id, tier, success_url, cancel_url
            )

            assert result["id"] == "cs_test_pro_123"
            assert result["tier"] == "pro"
            assert result["url"] == "https://checkout.stripe.com/pay/cs_test_pro_123"

    @pytest.mark.asyncio
    async def test_create_checkout_session_team(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should create team checkout session."""
        customer_id = "cus_test_456"
        tier = "team"
        success_url = "https://example.com/success"
        cancel_url = "https://example.com/cancel"

        mock_response = {
            "id": "cs_test_team_456",
            "url": "https://checkout.stripe.com/pay/cs_test_team_456",
            "customer": customer_id,
            "status": "open",
        }

        with patch.object(
            stripe_integration,
            "_get_client",
            new_callable=AsyncMock,
        ) as mock_get_client:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_response_obj = MagicMock(spec=httpx.Response)
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            result = await stripe_integration.create_checkout_session(
                customer_id, tier, success_url, cancel_url
            )

            assert result["tier"] == "team"

    @pytest.mark.asyncio
    async def test_create_checkout_session_free_fails(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should reject free tier."""
        with pytest.raises(ValueError, match="Cannot create checkout"):
            await stripe_integration.create_checkout_session(
                "cus_test",
                "free",
                "https://example.com/success",
                "https://example.com/cancel",
            )

    @pytest.mark.asyncio
    async def test_create_checkout_session_invalid_tier(
        self, stripe_integration: StripeIntegration
    ) -> None:
        """Should reject invalid tier."""
        with pytest.raises(ValueError, match="Invalid tier"):
            await stripe_integration.create_checkout_session(
                "cus_test",
                "invalid",
                "https://example.com/success",
                "https://example.com/cancel",
            )


class TestContextManager:
    """Test async context manager interface."""

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, stripe_api_key: str) -> None:
        """Should properly close client on context exit."""
        async with StripeIntegration(api_key=stripe_api_key) as stripe:
            assert stripe._client is None
            # Get client to initialize it
            with patch("httpx.AsyncClient", new_callable=AsyncMock):
                await stripe._get_client()
                assert stripe._client is not None

        # After exit, client should be closed
        assert stripe._client is None


class TestParameterValidation:
    """Test Pydantic parameter models."""

    def test_create_subscription_params_valid(self) -> None:
        """Should accept valid subscription params."""
        params = StripeCreateSubscriptionParams(
            customer_id="cus_test_123",
            tier="pro",
        )
        assert params.customer_id == "cus_test_123"
        assert params.tier == "pro"

    def test_create_subscription_params_invalid_tier(self) -> None:
        """Should reject invalid tier."""
        with pytest.raises(ValueError):
            StripeCreateSubscriptionParams(
                customer_id="cus_test_123",
                tier="invalid",
            )

    def test_create_subscription_params_free_tier(self) -> None:
        """Should reject free tier in params."""
        with pytest.raises(ValueError):
            StripeCreateSubscriptionParams(
                customer_id="cus_test_123",
                tier="free",
            )

    def test_create_charge_params_valid(self) -> None:
        """Should accept valid charge params."""
        params = StripeCreateChargeParams(
            customer_id="cus_test_123",
            amount_cents=9999,
            description="Overage charge",
        )
        assert params.amount_cents == 9999
        assert params.description == "Overage charge"

    def test_create_charge_params_invalid_amount(self) -> None:
        """Should reject zero or negative amounts."""
        with pytest.raises(ValueError):
            StripeCreateChargeParams(
                customer_id="cus_test_123",
                amount_cents=0,
                description="Test",
            )

        with pytest.raises(ValueError):
            StripeCreateChargeParams(
                customer_id="cus_test_123",
                amount_cents=-100,
                description="Test",
            )

    def test_get_invoice_params_valid(self) -> None:
        """Should accept valid invoice params."""
        params = StripeGetInvoiceParams(invoice_id="in_test_123")
        assert params.invoice_id == "in_test_123"

    def test_cancel_subscription_params_valid(self) -> None:
        """Should accept valid cancel params."""
        params = StripeCancelSubscriptionParams(subscription_id="sub_test_123")
        assert params.subscription_id == "sub_test_123"

    def test_list_invoices_params_valid(self) -> None:
        """Should accept valid list params."""
        params = StripeListInvoicesParams(
            customer_id="cus_test_123",
            limit=25,
        )
        assert params.customer_id == "cus_test_123"
        assert params.limit == 25

    def test_list_invoices_params_default_limit(self) -> None:
        """Should default to limit 10."""
        params = StripeListInvoicesParams(customer_id="cus_test_123")
        assert params.limit == 10

    def test_list_invoices_params_invalid_limit(self) -> None:
        """Should reject invalid limits."""
        with pytest.raises(ValueError):
            StripeListInvoicesParams(customer_id="cus_test_123", limit=0)

        with pytest.raises(ValueError):
            StripeListInvoicesParams(customer_id="cus_test_123", limit=101)

    def test_create_checkout_params_valid(self) -> None:
        """Should accept valid checkout params."""
        params = StripeCreateCheckoutParams(
            customer_id="cus_test_123",
            tier="pro",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        assert params.tier == "pro"
        assert params.success_url == "https://example.com/success"

    def test_create_checkout_params_invalid_urls(self) -> None:
        """Should validate HTTP(S) URLs."""
        with pytest.raises(ValueError):
            StripeCreateCheckoutParams(
                customer_id="cus_test_123",
                tier="pro",
                success_url="ftp://example.com/success",
                cancel_url="https://example.com/cancel",
            )

        with pytest.raises(ValueError):
            StripeCreateCheckoutParams(
                customer_id="cus_test_123",
                tier="pro",
                success_url="https://example.com/success",
                cancel_url="ftp://example.com/cancel",
            )


class TestTierMapping:
    """Test tier-to-price mapping."""

    def test_tier_price_map_completeness(self) -> None:
        """All tiers should have price IDs."""
        assert TIER_PRICE_MAP["pro"] == "price_pro"
        assert TIER_PRICE_MAP["team"] == "price_team"
        assert TIER_PRICE_MAP["enterprise"] == "price_enterprise"
        assert TIER_PRICE_MAP["free"] == ""

    def test_tier_price_usd_completeness(self) -> None:
        """All tiers should have USD prices."""
        assert TIER_PRICE_USD["free"] == 0
        assert TIER_PRICE_USD["pro"] == 99
        assert TIER_PRICE_USD["team"] == 299
        assert TIER_PRICE_USD["enterprise"] == 999
