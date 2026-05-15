"""Evasion network tools — Tor circuit rotation and proxy testing."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from loom.connection_pool_manager import get_client
from loom.validators import validate_url
from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json, fetch_text, fetch_bytes

logger = logging.getLogger("loom.tools.evasion_network")

_last_rotate_time: float = 0.0
_rotate_lock: asyncio.Lock | None = None


def _get_rotate_lock() -> asyncio.Lock:
    """Get or create the rotate lock."""
    global _rotate_lock
    if _rotate_lock is None:
        _rotate_lock = asyncio.Lock()
    return _rotate_lock


def _send_tor_rotate() -> tuple[bool, str, str]:
    """Send NEWNYM signal to Tor control port."""
    try:
        from stem.control import Controller  # type: ignore[import-untyped]

        control_password = os.environ.get("TOR_CONTROL_PASSWORD", "")
        with Controller.from_port(port=9051) as controller:
            if control_password:
                controller.authenticate(password=control_password)
            else:
                controller.authenticate()
            controller.signal("NEWNYM")
            logger.info("tor_rotate_newnym_sent")
            return (True, "", "circuit_rotated")
    except Exception as exc:
        logger.error("tor_rotate_failed: %s", type(exc).__name__)
        return (False, "", f"Error: {type(exc).__name__}")


@handle_tool_errors("research_tor_rotate")
async def research_tor_rotate() -> dict[str, Any]:
    """Rotate Tor circuit via NEWNYM signal (rate-limited 1 per 10s).

    Returns: {rotated, new_ip, circuit_id, latency_ms}
    """
    global _last_rotate_time
    start_time = time.time()
    async with _get_rotate_lock():
        now = time.time()
        if now - _last_rotate_time < 10.0:
            return {
                "rotated": False,
                "new_ip": "",
                "circuit_id": "rate_limited",
                "latency_ms": int((time.time() - start_time) * 1000),
            }
        loop = asyncio.get_running_loop()
        success, _, circuit_info = await loop.run_in_executor(None, _send_tor_rotate)
        if success:
            _last_rotate_time = time.time()
            try:
                from loom.config import CONFIG

                proxy = CONFIG.get("TOR_SOCKS5_PROXY", "socks5h://127.0.0.1:9050")
                client = await get_client(
                    base_url="",
                    timeout=5.0,
                    max_connections=5,
                    proxy=proxy,
                )
                new_ip = await fetch_json(client, "https://check.torproject.org/api/ip", timeout=5.0).get("IP", "") if resp.is_success else ""
            except Exception:
                new_ip = ""
            return {
                "rotated": True,
                "new_ip": new_ip,
                "circuit_id": circuit_info,
                "latency_ms": int((time.time() - start_time) * 1000),
            }
        return {
            "rotated": False,
            "new_ip": "",
            "circuit_id": circuit_info,
            "latency_ms": int((time.time() - start_time) * 1000),
        }


@handle_tool_errors("research_proxy_check")
async def research_proxy_check(proxy_url: str = "") -> dict[str, Any]:
    """Test proxy for connectivity and anonymity.

    Returns: {proxy, working, ip_visible, anonymity_level, latency_ms}
    """
    start_time = time.time()
    if not proxy_url:
        from loom.config import CONFIG

        proxy_url = CONFIG.get("TOR_SOCKS5_PROXY", "socks5h://127.0.0.1:9050")
    else:
        validate_url(proxy_url)
    try:
        client = await get_client(
            base_url="",
            timeout=10.0,
            max_connections=5,
            proxy=proxy_url,
        )
        resp = await client.get("https://check.torproject.org/api/ip", timeout=10.0)
        proxy_ip = ""
        if resp.is_success:
            try:
                proxy_ip = resp.json().get("IP", "")
            except Exception:
                proxy_ip = ""

        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "proxy": proxy_url,
            "working": resp.is_success,
            "ip_visible": bool(proxy_ip),
            "ip": proxy_ip,
            "anonymity_level": "high" if not proxy_ip else "medium",
            "latency_ms": latency_ms,
        }

    except Exception as exc:
        logger.error("proxy_check_error: %s", type(exc).__name__)
        return {
            "proxy": proxy_url,
            "working": False,
            "ip_visible": False,
            "ip": "",
            "anonymity_level": "unknown",
            "latency_ms": int((time.time() - start_time) * 1000),
            "error": str(exc),
        }
