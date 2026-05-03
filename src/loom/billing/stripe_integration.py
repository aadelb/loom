"""Stripe billing integration for Loom subscriptions.

Provides:
- Create/cancel subscriptions with Stripe price mapping
- One-time charges for overage or credits
- Invoice retrieval and listing
- Checkout session creation for signup flows
- Async httpx-based API calls (no stripe package dependency)
"""

from __future__ import annotations

import base64
import json
import logging
import os
import uuid
from typing import Any

import httpx

log = logging.getLogger(__name__)

# Stripe API base URL
STRIPE_API_BASE = "https://api.stripe.com/v1"

# Tier → Stripe price ID mapping
TIER_PRICE_MAP: dict[str, str] = {
    "free": "",  # No Stripe price for free tier
    "pro": "price_pro",
    "team": "price_team",
    "enterprise": "price_enterprise",
}

# Tier → Monthly price in USD (for reference/validation)
TIER_PRICE_USD: dict[str, int] = {
    "free": 0,
    "pro": 99,
    "team": 299,
    "enterprise": 999,
}


class StripeIntegration:
    """Stripe billing integration for Loom subscriptions.

    Manages subscription lifecycle, invoices, and one-time charges via
    Stripe REST API using httpx for HTTP calls. Requires STRIPE_LIVE_KEY
    environment variable.
    """

    def __init__(self, api_key: str = "") -> None:
        """Initialize Stripe integration.

        Args:
            api_key: Stripe API key (defaults to STRIPE_LIVE_KEY env var)

        Raises:
            ValueError: If no API key provided and env var not set
        """
        self.api_key = api_key or os.environ.get("STRIPE_LIVE_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Stripe API key required: pass api_key or set STRIPE_LIVE_KEY"
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialize async httpx client with Stripe auth."""
        if self._client is None:
            # Stripe API uses basic auth with empty username and API key as password
            auth_str = f":{self.api_key}"
            auth_b64 = base64.b64encode(auth_str.encode()).decode()
            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Basic {auth_b64}"}
            )
        return self._client

    async def close(self) -> None:
        """Close the async client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> StripeIntegration:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def create_subscription(
        self, customer_id: str, tier: str
    ) -> dict[str, Any]:
        """Create Stripe subscription for a customer tier.

        Args:
            customer_id: Loom customer ID (used as Stripe customer reference)
            tier: One of 'free', 'pro', 'team', 'enterprise'

        Returns:
            Dict with subscription details:
            - id: Stripe subscription ID
            - customer: Customer ID
            - tier: Subscription tier
            - price_id: Stripe price ID
            - status: Subscription status (active, incomplete, etc.)
            - current_period_start: Billing period start (Unix timestamp)
            - current_period_end: Billing period end (Unix timestamp)

        Raises:
            ValueError: If tier is 'free' or invalid
            httpx.HTTPError: If API call fails
        """
        if tier == "free":
            raise ValueError("Cannot create Stripe subscription for free tier")

        if tier not in TIER_PRICE_MAP:
            raise ValueError(f"Invalid tier: {tier}")

        price_id = TIER_PRICE_MAP[tier]
        if not price_id or len(price_id) < 5:
            raise ValueError(f"No Stripe price configured for tier: {tier}")

        client = await self._get_client()
        data = {
            "customer": customer_id,
            "items[0][price]": price_id,
            "payment_behavior": "default_incomplete",
            "expand[]": "latest_invoice.payment_intent",
        }

        try:
            response = await client.post(
                f"{STRIPE_API_BASE}/subscriptions",
                data=data,
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
            response.raise_for_status()
            result = response.json()

            log.info(f"Created Stripe subscription: {result.get('id')}")

            return {
                "id": result.get("id"),
                "customer": result.get("customer"),
                "tier": tier,
                "price_id": price_id,
                "status": result.get("status"),
                "current_period_start": result.get("current_period_start"),
                "current_period_end": result.get("current_period_end"),
            }
        except httpx.HTTPError as e:
            log.error(f"Failed to create Stripe subscription for {customer_id}: {e}")
            raise

    async def create_charge(
        self, customer_id: str, amount_cents: int, description: str
    ) -> dict[str, Any]:
        """Create one-time charge for overage or credits.

        Args:
            customer_id: Loom customer ID (Stripe customer)
            amount_cents: Charge amount in cents (e.g., 9999 = $99.99)
            description: Charge description (e.g., "Overage charges for April")

        Returns:
            Dict with charge details:
            - id: Stripe invoice item ID
            - customer: Customer ID
            - amount: Amount in cents
            - description: Description provided
            - created: Creation timestamp (Unix timestamp)

        Raises:
            ValueError: If amount <= 0
            httpx.HTTPError: If API call fails
        """
        if amount_cents <= 0:
            raise ValueError(f"Charge amount must be positive: {amount_cents}")

        client = await self._get_client()
        data = {
            "customer": customer_id,
            "amount": amount_cents,
            "currency": "usd",
            "description": description,
        }

        try:
            response = await client.post(
                f"{STRIPE_API_BASE}/invoiceitems",
                data=data,
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
            response.raise_for_status()
            result = response.json()

            log.info(f"Created Stripe charge: {result.get('id')}")

            return {
                "id": result.get("id"),
                "customer": result.get("customer"),
                "amount": result.get("amount"),
                "description": result.get("description"),
                "created": result.get("created"),
            }
        except httpx.HTTPError as e:
            log.error(f"Failed to create Stripe charge for {customer_id}: {e}")
            raise

    async def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        """Retrieve invoice details.

        Args:
            invoice_id: Stripe invoice ID

        Returns:
            Dict with invoice details:
            - id: Invoice ID
            - customer: Customer ID
            - amount_paid: Amount paid in cents
            - amount_remaining: Amount remaining in cents
            - total: Total amount in cents
            - status: Invoice status (draft, open, paid, void, uncollectible)
            - created: Creation timestamp (Unix timestamp)
            - due_date: Due date (Unix timestamp, if set)
            - paid: Whether invoice is paid (boolean)

        Raises:
            httpx.HTTPError: If API call fails or invoice not found
        """
        client = await self._get_client()

        try:
            response = await client.get(f"{STRIPE_API_BASE}/invoices/{invoice_id}")
            response.raise_for_status()
            result = response.json()

            log.info(f"Retrieved Stripe invoice: {invoice_id}")

            return {
                "id": result.get("id"),
                "customer": result.get("customer"),
                "amount_paid": result.get("amount_paid"),
                "amount_remaining": result.get("amount_remaining"),
                "total": result.get("total"),
                "status": result.get("status"),
                "created": result.get("created"),
                "due_date": result.get("due_date"),
                "paid": result.get("paid"),
            }
        except httpx.HTTPError as e:
            log.error(f"Failed to retrieve Stripe invoice {invoice_id}: {e}")
            raise

    async def cancel_subscription(self, subscription_id: str) -> dict[str, Any]:
        """Cancel a subscription.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Dict with cancellation details:
            - id: Subscription ID
            - customer: Customer ID
            - status: Subscription status (should be 'canceled')
            - canceled_at: Cancellation timestamp (Unix timestamp)

        Raises:
            httpx.HTTPError: If API call fails
        """
        client = await self._get_client()
        data = {"expand[]": "customer"}

        try:
            response = await client.delete(
                f"{STRIPE_API_BASE}/subscriptions/{subscription_id}",
                data=data,
            )
            response.raise_for_status()
            result = response.json()

            log.info(f"Canceled Stripe subscription: {subscription_id}")

            return {
                "id": result.get("id"),
                "customer": result.get("customer"),
                "status": result.get("status"),
                "canceled_at": result.get("canceled_at"),
            }
        except httpx.HTTPError as e:
            log.error(f"Failed to cancel Stripe subscription {subscription_id}: {e}")
            raise

    async def list_invoices(
        self, customer_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """List customer invoices.

        Args:
            customer_id: Loom customer ID (Stripe customer)
            limit: Maximum number of invoices to return (1-100, default 10)

        Returns:
            List of invoice dicts with:
            - id: Invoice ID
            - customer: Customer ID
            - amount_paid: Amount paid in cents
            - total: Total amount in cents
            - status: Invoice status
            - created: Creation timestamp (Unix timestamp)
            - paid: Whether invoice is paid (boolean)

        Raises:
            ValueError: If limit not 1-100
            httpx.HTTPError: If API call fails
        """
        if limit < 1 or limit > 100:
            raise ValueError(f"Limit must be 1-100: {limit}")

        client = await self._get_client()
        params = {"customer": customer_id, "limit": limit}

        try:
            response = await client.get(
                f"{STRIPE_API_BASE}/invoices",
                params=params,
            )
            response.raise_for_status()
            result = response.json()

            log.info(f"Retrieved {len(result.get('data', []))} Stripe invoices for {customer_id}")

            return [
                {
                    "id": inv.get("id"),
                    "customer": inv.get("customer"),
                    "amount_paid": inv.get("amount_paid"),
                    "total": inv.get("total"),
                    "status": inv.get("status"),
                    "created": inv.get("created"),
                    "paid": inv.get("paid"),
                }
                for inv in result.get("data", [])
            ]
        except httpx.HTTPError as e:
            log.error(f"Failed to list Stripe invoices for {customer_id}: {e}")
            raise

    async def create_checkout_session(
        self,
        customer_id: str,
        tier: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        """Create Stripe Checkout session for subscription signup.

        Args:
            customer_id: Loom customer ID
            tier: One of 'pro', 'team', 'enterprise' (not 'free')
            success_url: URL to redirect on successful payment
            cancel_url: URL to redirect if payment cancelled

        Returns:
            Dict with checkout session details:
            - id: Stripe session ID
            - url: Checkout URL for customer
            - customer: Customer ID
            - tier: Subscription tier
            - status: Session status (open, complete)

        Raises:
            ValueError: If tier is 'free' or invalid
            httpx.HTTPError: If API call fails
        """
        if tier == "free":
            raise ValueError("Cannot create checkout session for free tier")

        if tier not in TIER_PRICE_MAP:
            raise ValueError(f"Invalid tier: {tier}")

        price_id = TIER_PRICE_MAP[tier]
        if not price_id or len(price_id) < 5:
            raise ValueError(f"No Stripe price configured for tier: {tier}")

        client = await self._get_client()
        data = {
            "payment_method_types[0]": "card",
            "mode": "subscription",
            "customer": customer_id,
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "success_url": success_url,
            "cancel_url": cancel_url,
        }

        try:
            response = await client.post(
                f"{STRIPE_API_BASE}/checkout/sessions",
                data=data,
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
            response.raise_for_status()
            result = response.json()

            log.info(f"Created Stripe checkout session: {result.get('id')}")

            return {
                "id": result.get("id"),
                "url": result.get("url"),
                "customer": result.get("customer"),
                "tier": tier,
                "status": result.get("status"),
            }
        except httpx.HTTPError as e:
            log.error(f"Failed to create Stripe checkout session for {customer_id}: {e}")
            raise
