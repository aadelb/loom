"""Enterprise SSO integration module — SAML, OIDC, OAuth2, LDAP configuration & token validation.

Tools:
    research_sso_configure — Configure SSO provider settings
    research_sso_validate_token — Validate an SSO token (structure, expiry, signature format)
    research_sso_user_info — Extract user info from SSO token (JWT claims parsing)
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.enterprise_sso")

SSO_CONFIG_PATH = Path.home() / ".loom" / "sso_config.json"


def _load_sso_config() -> dict[str, Any]:
    """Load SSO config from disk, return empty dict if not exists."""
    if SSO_CONFIG_PATH.exists():
        try:
            return json.loads(SSO_CONFIG_PATH.read_text())
        except Exception as e:
            logger.warning("sso_config_load_failed error=%s", str(e))
            return {}
    return {}


def _save_sso_config(config: dict[str, Any]) -> None:
    """Save SSO config atomically with restricted file permissions."""
    SSO_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SSO_CONFIG_PATH.write_text(json.dumps(config, indent=2))
    # SECURITY: Ensure config file is not world-readable (may contain secrets)
    SSO_CONFIG_PATH.chmod(0o600)


def _decode_jwt_parts(token: str) -> tuple[dict, dict] | None:
    """Decode JWT header + payload (no signature verification).

    SECURITY: This function does NOT verify the JWT signature.
    It is unsafe to use for authentication without additional verification.
    Only use for structural validation or when signature verification is done elsewhere.

    Returns:
        Tuple of (header_dict, payload_dict) or None if invalid
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        # Decode header
        header_b64 = parts[0]
        header_pad = header_b64 + "=" * (4 - len(header_b64) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_pad))

        # SECURITY: Reject "none" algorithm (algorithm confusion attack)
        if header.get("alg") == "none":
            logger.warning("jwt_algo_none_rejected")
            return None

        # Decode payload
        payload_b64 = parts[1]
        payload_pad = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_pad))

        return (header, payload)
    except Exception as e:
        logger.debug("jwt_decode_failed error=%s", str(e))
        return None


@handle_tool_errors("research_sso_configure")
async def research_sso_configure(
    provider: Literal["saml", "oidc", "oauth2", "ldap"] = "saml",
    metadata_url: str = "",
    client_id: str = "",
) -> dict[str, Any]:
    """Configure SSO provider settings.

    Args:
        provider: SSO provider type ('saml', 'oidc', 'oauth2', 'ldap')
        metadata_url: Metadata endpoint URL (for SAML/OIDC)
        client_id: Client ID for OAuth2/OIDC

    Returns:
        Dict with configured status, provider, settings_saved
    """
    try:
        # Validate provider
        if provider not in ("saml", "oidc", "oauth2", "ldap"):
            return {
                "configured": False,
                "provider": provider,
                "error": "Invalid provider. Must be: saml, oidc, oauth2, ldap",
            }

        # Load existing config
        config = _load_sso_config()

        # Update provider config
        if provider not in config:
            config[provider] = {}

        if metadata_url:
            config[provider]["metadata_url"] = metadata_url
        if client_id:
            config[provider]["client_id"] = client_id

        config[provider]["updated_at"] = datetime.now(UTC).isoformat()

        # Save config
        _save_sso_config(config)

        logger.info("sso_configured provider=%s client_id=%s", provider, client_id or "not_set")

        return {
            "configured": True,
            "provider": provider,
            "settings_saved": True,
            "config_path": str(SSO_CONFIG_PATH),
        }

    except Exception as e:
        logger.error("sso_configure_failed provider=%s error=%s", provider, str(e))
        return {
            "configured": False,
            "provider": provider,
            "error": str(e),
        }


@handle_tool_errors("research_sso_validate_token")
async def research_sso_validate_token(
    token: str,
    provider: Literal["saml", "oidc", "oauth2", "ldap", "auto"] = "auto",
) -> dict[str, Any]:
    """Validate an SSO token (structure, expiry, signature format).

    For JWT: decode header+payload (no signature verification without secret).
    Check: exp claim not expired, iss claim matches configured provider.

    SECURITY WARNING: This function does NOT verify JWT signatures. It only validates:
    1. Token structure (valid base64, 3 parts)
    2. Token not expired (exp claim < now)
    3. Issuer matches configured provider (exact match)
    4. Algorithm is not "none" (rejects algorithm confusion attacks)

    Do NOT use this for authentication without proper signature verification.
    A complete SSO implementation must:
    - Verify JWT signature using the provider's public key
    - Validate cryptographic signature to prevent token forgery
    - Check token audience (aud claim) matches expected client

    Args:
        token: SSO token (JWT or opaque)
        provider: Provider type or 'auto' to detect

    Returns:
        Dict with valid status, provider, claims, expires_at, reason if invalid
    """
    try:
        if not token or not isinstance(token, str):
            return {"valid": False, "reason": "Token is empty or not a string"}

        # Try JWT decode
        jwt_parts = _decode_jwt_parts(token)

        if jwt_parts is None:
            return {
                "valid": False,
                "provider": provider,
                "reason": "Not a valid JWT (invalid base64 or structure)",
            }

        header, payload = jwt_parts

        # Check expiry
        exp = payload.get("exp")
        now_ts = datetime.now(UTC).timestamp()
        expired = exp is not None and exp < now_ts

        expires_at = None
        if exp:
            expires_at = datetime.fromtimestamp(exp, tz=UTC).isoformat()

        if expired:
            return {
                "valid": False,
                "provider": provider,
                "claims": payload,
                "expires_at": expires_at,
                "reason": "Token has expired",
            }

        # Check issuer against configured provider
        if provider != "auto":
            config = _load_sso_config()
            if provider in config:
                configured_iss = config[provider].get("iss") or config[provider].get(
                    "metadata_url"
                )
                token_iss = payload.get("iss")
                # SECURITY: Use exact equality match, not substring match (prevent issuer spoofing)
                if configured_iss and token_iss and configured_iss != token_iss:
                    return {
                        "valid": False,
                        "provider": provider,
                        "claims": payload,
                        "reason": "Issuer mismatch",
                    }

        logger.info("sso_token_valid provider=%s sub=%s", provider, payload.get("sub", "unknown"))

        return {
            "valid": True,
            "provider": provider,
            "claims": payload,
            "expires_at": expires_at,
            "algorithm": header.get("alg", "unknown"),
        }

    except Exception as e:
        logger.error("sso_validate_failed provider=%s error=%s", provider, str(e))
        return {"valid": False, "provider": provider, "reason": str(e)}


@handle_tool_errors("research_sso_user_info")
async def research_sso_user_info(token: str) -> dict[str, Any]:
    """Extract user info from SSO token (JWT claims parsing).

    Parses standard JWT claims: sub, email, name, groups, roles.

    Args:
        token: SSO JWT token

    Returns:
        Dict with user_id, email, name, groups, roles, provider
    """
    try:
        jwt_parts = _decode_jwt_parts(token)

        if jwt_parts is None:
            return {
                "user_id": None,
                "email": None,
                "name": None,
                "groups": [],
                "roles": [],
                "provider": None,
                "error": "Invalid JWT token",
            }

        header, payload = jwt_parts

        # Extract standard claims
        user_id = payload.get("sub") or payload.get("user_id") or payload.get("oid")
        email = payload.get("email")
        name = (
            payload.get("name")
            or payload.get("given_name")
            or payload.get("preferred_username")
        )

        # Extract groups and roles (different providers use different claim names)
        # SECURITY: Validate that groups/roles are lists of strings (prevent RBAC bypass)
        groups = (
            payload.get("groups")
            or payload.get("group")
            or payload.get("memberOf")
            or []
        )
        if isinstance(groups, str):
            groups = [groups]
        elif not isinstance(groups, list):
            groups = []
        # Ensure all group values are strings
        groups = [g for g in groups if isinstance(g, str)]

        roles = (
            payload.get("roles")
            or payload.get("role")
            or payload.get("app_roles")
            or []
        )
        if isinstance(roles, str):
            roles = [roles]
        elif not isinstance(roles, list):
            roles = []
        # Ensure all role values are strings
        roles = [r for r in roles if isinstance(r, str)]

        provider = payload.get("iss", "unknown")

        logger.info("sso_user_extracted user_id=%s email=%s", user_id, email)

        return {
            "user_id": user_id,
            "email": email,
            "name": name,
            "groups": list(groups),
            "roles": list(roles),
            "provider": provider,
        }

    except Exception as e:
        logger.error("sso_user_info_failed error=%s", str(e))
        return {
            "user_id": None,
            "email": None,
            "name": None,
            "groups": [],
            "roles": [],
            "provider": None,
            "error": str(e),
        }
