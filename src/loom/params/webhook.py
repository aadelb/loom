"""Pydantic parameter models for webhook management tools."""

from __future__ import annotations


from pydantic import BaseModel, Field, field_validator


class WebhookRegisterParams(BaseModel):
    """Parameters for research_webhook_register tool."""

    url: str = Field(description="Webhook URL to POST to (must start with http:// or https://)")
    events: list[str] = Field(
        description="List of events to subscribe to",
        min_items=1,
        max_items=5,
    )
    secret: str | None = Field(
        default=None,
        description="HMAC secret for signature verification (generated if not provided)"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("url must be a string")
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        if len(v) > 2048:
            raise ValueError("url max 2048 characters")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        from loom.webhooks import SUPPORTED_EVENTS

        invalid = set(v) - SUPPORTED_EVENTS
        if invalid:
            raise ValueError(
                f"invalid events: {invalid}. "
                f"supported: {sorted(SUPPORTED_EVENTS)}"
            )
        return v

    @field_validator("secret")
    @classmethod
    def validate_secret(cls, v: str | None) -> str | None:
        if v is not None:
            if not isinstance(v, str) or len(v) < 8:
                raise ValueError("secret must be at least 8 characters")
            if len(v) > 256:
                raise ValueError("secret max 256 characters")
        return v


class WebhookUnregisterParams(BaseModel):
    """Parameters for research_webhook_unregister tool."""

    webhook_id: str = Field(description="ID of webhook to unregister")

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("webhook_id")
    @classmethod
    def validate_webhook_id(cls, v: str) -> str:
        if not v or len(v) < 1:
            raise ValueError("webhook_id must not be empty")
        if len(v) > 64:
            raise ValueError("webhook_id max 64 characters")
        return v


class WebhookTestParams(BaseModel):
    """Parameters for research_webhook_test tool."""

    webhook_id: str = Field(description="ID of webhook to test")

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("webhook_id")
    @classmethod
    def validate_webhook_id(cls, v: str) -> str:
        if not v or len(v) < 1:
            raise ValueError("webhook_id must not be empty")
        if len(v) > 64:
            raise ValueError("webhook_id max 64 characters")
        return v
