"""research_tor_status and research_tor_new_identity — Tor daemon management tools.

Provides async tools for checking Tor connectivity and rotating exit circuits.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from loom.connection_pool_manager import get_client
from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json, fetch_text, fetch_bytes

logger = logging.getLogger("loom.tools.tor")

# Rate limiting for NEWNYM requests (1 per 10 seconds)
_last_newnym_time: float = 0.0
_newnym_lock: asyncio.Lock | None = None


def _get_newnym_lock() -> asyncio.Lock:
    """Get or create the newnym lock."""
    global _newnym_lock
    if _newnym_lock is None:
        _newnym_lock = asyncio.Lock()
    return _newnym_lock


@handle_tool_errors("research_tor_status")
async def research_tor_status() -> dict[str, Any]:
    """Check Tor daemon status and get current exit node IP.

    Attempts to connect to the Tor SOCKS5 proxy (from TOR_SOCKS5_PROXY config,
    default 127.0.0.1:9050) and fetches the current exit node IP from
    check.torproject.org API.

    Returns:
        Dict with keys:
        - tor_running (bool): Tor SOCKS5 proxy is accessible
        - exit_ip (str): Current exit node IP address (empty if Tor not running)
        - socks5_proxy (str): SOCKS5 proxy URL configured
        - error (str, optional): Error message if any step fails

    Examples:
        >>> status = await research_tor_status()
        >>> if status["tor_running"]:
        ...     print(f"Exit IP: {status['exit_ip']}")
    """
    from loom.config import CONFIG

    logger.info("tor_status_check_start")

    proxy = CONFIG.get("TOR_SOCKS5_PROXY", "socks5h://127.0.0.1:9050")

    try:
        client = await get_client(
            base_url="",
            timeout=10.0,
            max_connections=5,
            proxy=proxy,
        )
        data = await fetch_json(client,
            "https://check.torproject.org/api/ip",
            timeout=10.0,
        )
        if not data:
            raise ValueError("Empty response from check.torproject.org")

        exit_ip = data.get("IP", "")

        result = {
            "tor_running": True,
            "exit_ip": exit_ip,
            "socks5_proxy": proxy,
        }
        logger.info("tor_status_check_success exit_ip=%s", exit_ip)
        return result

    except (Exception,) as exc:
        import httpx

        if isinstance(exc, (httpx.ConnectError, httpx.ProxyError)):
            logger.warning("tor_status_proxy_error: %s", type(exc).__name__)
            return {
                "tor_running": False,
                "exit_ip": "",
                "socks5_proxy": proxy,
                "error": "Tor SOCKS5 proxy not accessible (is Tor running?)",
            }

        if isinstance(exc, httpx.TimeoutException):
            logger.warning("tor_status_timeout: %s", type(exc).__name__)
            return {
                "tor_running": False,
                "exit_ip": "",
                "socks5_proxy": proxy,
                "error": "Timeout connecting to check.torproject.org",
            }

        logger.error("tor_status_unexpected: %s", type(exc).__name__)
        return {
            "tor_running": False,
            "exit_ip": "",
            "socks5_proxy": proxy,
            "error": "unexpected error",
        }


def _send_tor_newnym() -> bool:
    """Send NEWNYM signal to Tor control port via stem library.

    Returns:
        True if signal sent successfully, False otherwise.
    """
    try:
        from stem.control import Controller  # type: ignore[import-untyped]
    except ImportError:
        logger.error("stem_not_installed")
        return False

    try:
        control_password = os.environ.get("TOR_CONTROL_PASSWORD", "")
        with Controller.from_port(port=9051) as controller:
            # Authenticate: use cookie auth if no password, else password auth
            if control_password:
                controller.authenticate(password=control_password)
            else:
                controller.authenticate()

            # Send NEWNYM signal
            controller.signal("NEWNYM")
            logger.info("tor_newnym_sent")
            return True

    except Exception as exc:
        logger.error("tor_newnym_failed: %s", type(exc).__name__)
        return False


@handle_tool_errors("research_tor_new_identity")
async def research_tor_new_identity() -> dict[str, Any]:
    """Request a new Tor circuit (exit node rotation).

    Sends the NEWNYM signal to Tor's control port to rotate the exit node.
    Rate-limited to 1 request per 10 seconds to avoid overwhelming the Tor daemon.

    Returns:
        Dict with keys:
        - status (str): "new_identity_requested" on success
        - wait_seconds (int): 10 (standard wait time before reusing this endpoint)
        - error (str, optional): Error message if any step fails

    Examples:
        >>> result = await research_tor_new_identity()
        >>> if "error" not in result:
        ...     print("New circuit requested, wait 10 seconds")
    """
    global _last_newnym_time

    logger.info("tor_newnym_request_start")

    async with _get_newnym_lock():
        now = time.time()
        time_since_last = now - _last_newnym_time

        if time_since_last < 10.0:
            wait_time = 10.0 - time_since_last
            logger.warning("tor_newnym_rate_limited wait=%.1f", wait_time)
            return {
                "status": "rate_limited",
                "wait_seconds": 10,
                "error": f"Rate limited: wait {wait_time:.1f}s before next request",
            }

        # Run blocking stem call in executor with timeout to prevent deadlock
        loop = asyncio.get_running_loop()
        try:
            success = await asyncio.wait_for(
                loop.run_in_executor(None, _send_tor_newnym), timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.error("tor_newnym_timeout: stem call hung for 30s")
            return {"status": "failed", "wait_seconds": 30, "error": "Tor control timeout"}
        except Exception as exc:
            logger.error("tor_newnym_executor_error: %s", type(exc).__name__)
            return {
                "status": "failed",
                "wait_seconds": 10,
                "error": "unexpected error",
            }

        if success:
            _last_newnym_time = now
            return {
                "status": "new_identity_requested",
                "wait_seconds": 10,
            }
        else:
            return {
                "status": "failed",
                "wait_seconds": 10,
                "error": "failed to send NEWNYM signal (check Tor running and control auth)",
            }
