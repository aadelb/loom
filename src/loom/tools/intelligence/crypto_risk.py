"""Cryptocurrency wallet risk scoring tools."""

from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json

logger = logging.getLogger("loom.tools.crypto_risk")
_BASE58 = r"[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]"


try:
    from loom.score_utils import clamp
except ImportError:
    def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, v))


def _validate_bitcoin_address(address: str) -> bool:
    """Validate Bitcoin address (P2PKH/P2SH/Bech32)."""
    pattern = f"^(1{_BASE58}{{24,33}}|3{_BASE58}{{24,33}}|bc1[a-z0-9]{{39,59}})$"
    return bool(re.match(pattern, address))


def _validate_ethereum_address(address: str) -> bool:
    """Validate Ethereum address (0x + 40 hex chars)."""
    return bool(re.match(r"^0x[a-fA-F0-9]{40}$", address))


def _calculate_risk_score(metrics: dict[str, Any]) -> tuple[int, str]:
    """Calculate risk score (0-100) and risk level."""
    score = 50
    if days_old := metrics.get("days_old"):
        score += 15 if days_old < 30 else 5 if days_old < 180 else -10 if days_old > 1825 else 0
    tx_count = metrics.get("transaction_count", 0)
    score += 20 if tx_count == 0 else 10 if tx_count < 5 else -15 if tx_count > 100 else 0
    if (bal := metrics.get("current_balance", 0)) > 0 and (tot := metrics.get("total_received", 0)) > 0:
        conc = bal / tot
        score += 10 if conc > 0.8 else -5 if conc < 0.1 else 0
    score = max(0, min(100, score))
    level = "critical" if score >= 75 else "high" if score >= 50 else "medium" if score >= 25 else "low"
    return score, level


@handle_tool_errors("research_crypto_risk_score")
async def research_crypto_risk_score(address: str, chain: str = "bitcoin") -> dict[str, Any]:
    """Evaluate cryptocurrency wallet risk.

    Queries blockchain.info (Bitcoin) or etherscan.io (Ethereum) to compute
    a risk score (0-100) based on wallet age, transaction volume, and balance.

    Args:
        address: Cryptocurrency address
        chain: "bitcoin" or "ethereum" (default "bitcoin")

    Returns:
        Dict: address, chain, risk_score, risk_level, metrics, factors, error
    """
    address, chain = address.strip(), chain.lower()

    if chain == "bitcoin":
        if not _validate_bitcoin_address(address):
            return {"address": address, "chain": chain, "error": "Invalid Bitcoin address", "risk_score": None, "risk_level": None, "metrics": {}, "factors": []}
        api_url = f"https://blockchain.info/q/addressbalance/{address}"
    elif chain == "ethereum":
        if not _validate_ethereum_address(address):
            return {"address": address, "chain": chain, "error": "Invalid Ethereum address", "risk_score": None, "risk_level": None, "metrics": {}, "factors": []}
        key = os.environ.get("ETHERSCAN_API_KEY", "")
        api_url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&apikey={key}"
    else:
        return {"address": address, "chain": chain, "error": "Unsupported chain", "risk_score": None, "risk_level": None, "metrics": {}, "factors": []}

    metrics = {"transaction_count": 0, "total_received": 0, "total_sent": 0, "current_balance": 0, "first_seen": None, "last_seen": None, "days_old": None}
    factors = []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            data = await fetch_json(client, api_url)
            if not data:
                raise ValueError("Empty response from blockchain API")

        if chain == "bitcoin":
            metrics["current_balance"] = (data if isinstance(data, int) else data.get("balance", 0)) / 100_000_000
            detail_url = f"https://blockchain.info/address/{address}?format=json"
            async with httpx.AsyncClient(timeout=15.0) as client:
                detail = (await client.get(detail_url)).json()
            metrics["transaction_count"] = detail.get("n_tx", 0)
            metrics["total_received"] = detail.get("total_received", 0) / 100_000_000
            metrics["total_sent"] = detail.get("total_sent", 0) / 100_000_000
            if ft := detail.get("first_tx"):
                if t := ft.get("time"):
                    fs = datetime.fromtimestamp(t, tz=UTC)
                    metrics["first_seen"] = fs.isoformat()
                    metrics["days_old"] = (datetime.now(UTC) - fs).days
            if lt := detail.get("latest_tx"):
                if t := lt.get("time"):
                    metrics["last_seen"] = datetime.fromtimestamp(t, tz=UTC).isoformat()
        else:
            if data.get("status") != "1":
                return {"address": address, "chain": chain, "error": "API error", "risk_score": None, "risk_level": None, "metrics": {}, "factors": []}
            metrics["current_balance"] = int(data["result"]) / 1e18
            tx_url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=asc"
            if k := os.environ.get("ETHERSCAN_API_KEY"):
                tx_url += f"&apikey={k}"
            async with httpx.AsyncClient(timeout=15.0) as client:
                txs = (await client.get(tx_url)).json().get("result", [])
            if txs:
                metrics["transaction_count"] = len(txs)
                ts, tr = 0, 0
                if ft := int(txs[0].get("timeStamp", 0)):
                    fs = datetime.fromtimestamp(ft, tz=UTC)
                    metrics["first_seen"] = fs.isoformat()
                    metrics["days_old"] = (datetime.now(UTC) - fs).days
                if lt := int(txs[-1].get("timeStamp", 0)):
                    metrics["last_seen"] = datetime.fromtimestamp(lt, tz=UTC).isoformat()
                for tx in txs:
                    v = int(tx.get("value", 0))
                    if tx.get("from", "").lower() == address.lower():
                        ts += v
                    if tx.get("to", "").lower() == address.lower():
                        tr += v
                metrics["total_sent"], metrics["total_received"] = ts / 1e18, tr / 1e18

        if metrics["days_old"] and metrics["days_old"] < 30:
            factors.append("Wallet created <30 days ago")
        if metrics["transaction_count"] == 0:
            factors.append("No transaction history")
        elif metrics["transaction_count"] < 5:
            factors.append("Very few transactions")
        b, tr = metrics["current_balance"], metrics["total_received"]
        if b > 0 and tr > 0 and (b / tr) > 0.9:
            factors.append("High balance concentration")
        if b == 0:
            factors.append("Empty wallet")

        risk_score, risk_level = _calculate_risk_score(metrics)
        logger.info("crypto_risk_score_calculated address=%s chain=%s score=%d", address, chain, risk_score)
        return {"address": address, "chain": chain, "risk_score": risk_score, "risk_level": risk_level, "metrics": metrics, "factors": factors}

    except Exception as exc:
        logger.exception("crypto_risk_score_failed address=%s", address)
        return {"address": address, "chain": chain, "error": str(exc), "risk_score": None, "risk_level": None, "metrics": metrics, "factors": []}
