"""research_tor_status and research_tor_new_identity — Tor daemon management tools.

Provides async tools for checking Tor connectivity and rotating exit circuits.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.tor")

# Rate limiting for NEWNYM requests (1 per 10 seconds)
_last_newnym_time: float = 0.0
_newnym_lock = asyncio.Lock()

# Module-level client for Tor proxy connectivity checks
_tor_client: httpx.AsyncClient | None = None


async def _get_tor_client() -> httpx.AsyncClient:
    """Get or create async HTTP client configured for Tor proxy."""
    global _tor_client
    if _tor_client is None:
        _tor_client = httpx.AsyncClient(
            proxy="socks5h://127.0.0.1:9050",
            timeout=10.0,
            limits=httpx.Limits(max_connections=5),
        )
    return _tor_client


async def research_tor_status() -> dict[str, Any]:
    """Check Tor daemon status and get current exit node IP.

    Attempts to connect to the Tor SOCKS5 proxy (127.0.0.1:9050) and
    fetches the current exit node IP from check.torproject.org API.

    Returns:
        Dict with keys:
        - tor_running (bool): Tor SOCKS5 proxy is accessible
        - exit_ip (str): Current exit node IP address (empty if Tor not running)
        - socks5_proxy (str): SOCKS5 proxy URL ("socks5h://127.0.0.1:9050")
        - error (str, optional): Error message if any step fails

    Examples:
        >>> status = await research_tor_status()
        >>> if status["tor_running"]:
        ...     print(f"Exit IP: {status['exit_ip']}")
    """
    logger.info("tor_status_check_start")

    try:
        client = await _get_tor_client()
        resp = await client.get(
            "https://check.torproject.org/api/ip",
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        exit_ip = data.get("IP", "")

        result = {
            "tor_running": True,
            "exit_ip": exit_ip,
            "socks5_proxy": "socks5h://127.0.0.1:9050",
        }
        logger.info("tor_status_check_success exit_ip=%s", exit_ip)
        return result

    except (httpx.ConnectError, httpx.ProxyError) as exc:
        logger.warning("tor_status_proxy_error: %s", type(exc).__name__)
        return {
            "tor_running": False,
            "exit_ip": "",
            "socks5_proxy": "socks5h://127.0.0.1:9050",
            "error": "Tor SOCKS5 proxy not accessible (is Tor running?)",
        }

    except httpx.TimeoutException as exc:
        logger.warning("tor_status_timeout: %s", type(exc).__name__)
        return {
            "tor_running": False,
            "exit_ip": "",
            "socks5_proxy": "socks5h://127.0.0.1:9050",
            "error": "Timeout connecting to check.torproject.org",
        }

    except ImportError:
        return {
            "tor_running": False,
            "exit_ip": "",
            "socks5_proxy": "socks5h://127.0.0.1:9050",
            "error": "socksio not installed (pip install socksio) — required for SOCKS5 proxy",
        }

    except Exception as exc:
        logger.error("tor_status_unexpected: %s", type(exc).__name__)
        return {
            "tor_running": False,
            "exit_ip": "",
            "socks5_proxy": "socks5h://127.0.0.1:9050",
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

    async with _newnym_lock:
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

        # Run blocking stem call in executor
        loop = asyncio.get_running_loop()
        try:
            success = await loop.run_in_executor(None, _send_tor_newnym)
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
