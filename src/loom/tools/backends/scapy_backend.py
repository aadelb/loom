"""Packet crafting and network probing — Use Scapy for low-level network analysis."""

from __future__ import annotations

import asyncio
import logging
import re
import socket
import time
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.scapy_backend")

# Valid packet types
VALID_PACKET_TYPES = ["tcp_syn", "tcp_rst", "icmp_echo", "udp_probe"]

# Max timeout
MAX_TIMEOUT_SECONDS = 30


@handle_tool_errors("research_packet_craft")
async def research_packet_craft(
    target: str,
    packet_type: str = "tcp_syn",
    port: int = 80,
    timeout: int = 5,
) -> dict[str, Any]:
    """Craft and send a network probe packet using Scapy.

    Scapy is a powerful packet manipulation library for network analysis.
    Sends a single probe packet (TCP SYN, ICMP echo, UDP) to target.

    Args:
        target: target IP address or hostname
        packet_type: type of packet to send:
                     - "tcp_syn": TCP SYN packet (port scan style)
                     - "tcp_rst": TCP RST packet
                     - "icmp_echo": ICMP echo request (ping)
                     - "udp_probe": UDP probe packet (default port 53)
        port: destination port (1-65535, used by TCP/UDP packets)
        timeout: response timeout in seconds (1-30)

    Returns:
        Dict with:
        - target: resolved IP address
        - packet_type: type sent
        - response_received: whether response received
        - ttl: TTL from response (if received)
        - flags: TCP flags from response (if TCP response)
        - latency_ms: round-trip time in milliseconds
        - error: error message if probe failed
    """
    try:
        from scapy.all import IP, ICMP, TCP, UDP, sr1  # type: ignore
    except ImportError:
        return {
            "error": "scapy not installed. Install with: pip install scapy",
        }

    # Validate input
    if not target:
        return {"error": "target must be specified"}

    if packet_type not in VALID_PACKET_TYPES:
        return {
            "error": f"packet_type must be one of: {', '.join(VALID_PACKET_TYPES)}"
        }

    if not (1 <= port <= 65535):
        return {"error": "port must be 1-65535"}

    if not (1 <= timeout <= MAX_TIMEOUT_SECONDS):
        return {"error": f"timeout must be 1-{MAX_TIMEOUT_SECONDS}"}

    output: dict[str, Any] = {
        "target": target,
        "packet_type": packet_type,
        "port": port,
    }

    # Resolve hostname to IP if needed
    try:
        def _resolve_host() -> str:
            # Basic hostname/IP validation
            if not re.match(r"^[a-zA-Z0-9\-\.]+$", target):
                raise ValueError("Invalid hostname/IP format")

            try:
                # Try direct IP parse first
                socket.inet_aton(target)
                return target
            except socket.error:
                # Try hostname resolution
                resolved = socket.gethostbyname(target)
                return resolved

        target_ip = await asyncio.to_thread(_resolve_host)
        output["target_resolved"] = target_ip

        logger.info("host_resolved target=%s ip=%s", target, target_ip)

    except Exception as exc:
        logger.error("hostname_resolution_error target=%s error=%s", target, exc)
        return {
            **output,
            "error": f"Failed to resolve target: {exc}",
        }

    # Craft and send packet
    try:
        def _send_packet() -> dict[str, Any]:
            start_time = time.time()

            try:
                # Construct packet based on type
                if packet_type == "tcp_syn":
                    packet = IP(dst=target_ip) / TCP(dport=port, flags="S")
                    protocol = "TCP"
                elif packet_type == "tcp_rst":
                    packet = IP(dst=target_ip) / TCP(dport=port, flags="R")
                    protocol = "TCP"
                elif packet_type == "icmp_echo":
                    packet = IP(dst=target_ip) / ICMP()
                    protocol = "ICMP"
                elif packet_type == "udp_probe":
                    packet = IP(dst=target_ip) / UDP(dport=port)
                    protocol = "UDP"
                else:
                    raise ValueError(f"Unknown packet type: {packet_type}")

                # Send packet and wait for response
                response = sr1(packet, timeout=timeout, verbose=False)

                elapsed_ms = int((time.time() - start_time) * 1000)

                result: dict[str, Any] = {
                    "protocol": protocol,
                    "response_received": response is not None,
                    "latency_ms": elapsed_ms,
                }

                if response:
                    # Parse response
                    if ICMP in response:
                        result["ttl"] = response.ttl
                        result["icmp_type"] = response[ICMP].type
                        result["icmp_code"] = response[ICMP].code

                    elif TCP in response:
                        result["ttl"] = response.ttl
                        result["flags"] = response[TCP].flags.summary()
                        result["seq"] = response[TCP].seq

                    elif UDP in response:
                        result["ttl"] = response.ttl

                return result

            except PermissionError as exc:
                raise PermissionError(
                    "Raw socket access requires root/admin privileges. "
                    "Try: sudo python or use Windows admin prompt"
                ) from exc

        result = await asyncio.to_thread(_send_packet)
        output.update(result)

        logger.info(
            "packet_sent target=%s type=%s response=%s latency=%d",
            target_ip,
            packet_type,
            result.get("response_received"),
            result.get("latency_ms"),
        )

        return output

    except PermissionError as exc:
        logger.error("permission_error target=%s error=%s", target_ip, exc)
        return {
            **output,
            "error": str(exc),
        }
    except Exception as exc:
        logger.error("packet_send_error target=%s type=%s error=%s", target_ip, packet_type, exc)
        return {
            **output,
            "error": f"Packet sending failed: {exc}",
        }
