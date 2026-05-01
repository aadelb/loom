"""Ethereum blockchain analysis — transaction decoding and DeFi security auditing."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.ethereum_tools")

_ETHERSCAN_API = "https://api.etherscan.io/api"
_API_KEY = os.environ.get("ETHERSCAN_API_KEY", "")


async def research_ethereum_tx_decode(tx_hash: str) -> dict[str, Any]:
    """Decode Ethereum transaction from etherscan.io.

    Identifies patterns: token transfer, swap, NFT mint, contract deployment.

    Args:
        tx_hash: transaction hash (0x-prefixed hex string)

    Returns:
        Dict with decoded details, pattern, value_eth, and status.
    """
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        return {"tx_hash": tx_hash, "error": "Invalid tx hash", "decoded": None, "pattern": None, "value_eth": 0.0, "status": None}

    params = {"module": "proxy", "action": "eth_getTransactionByHash", "txhash": tx_hash}
    if _API_KEY:
        params["apikey"] = _API_KEY

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(_ETHERSCAN_API, params=params)
            if resp.status_code != 200:
                return {"tx_hash": tx_hash, "error": f"API error {resp.status_code}", "decoded": None, "pattern": None, "value_eth": 0.0, "status": None}

            data = resp.json()
            tx = data.get("result")
            if not tx:
                return {"tx_hash": tx_hash, "error": data.get("message", "tx not found"), "decoded": None, "pattern": None, "value_eth": 0.0, "status": None}

            value_eth = int(tx.get("value", "0"), 16) / 1e18
            input_data = tx.get("input", "0x")
            pattern = _identify_pattern(input_data, tx.get("to", ""))

            receipt = await _get_receipt(client, tx_hash)
            status = "pending"
            gas_used = 0
            if receipt:
                status = "success" if receipt.get("status") == "0x1" else "failed"
                gas_used = int(receipt.get("gasUsed", "0"), 16)

            return {
                "tx_hash": tx_hash,
                "decoded": {
                    "from": tx.get("from", ""),
                    "to": tx.get("to", ""),
                    "value_wei": int(tx.get("value", "0"), 16),
                    "gas": int(tx.get("gas", "0"), 16),
                    "gas_price_wei": int(tx.get("gasPrice", "0"), 16),
                    "gas_used": gas_used,
                    "nonce": int(tx.get("nonce", "0"), 16),
                    "block_number": int(tx.get("blockNumber", "0"), 16) if tx.get("blockNumber") else None,
                    "input_data": input_data[:256],
                },
                "pattern": pattern,
                "value_eth": round(value_eth, 6),
                "status": status,
            }
    except Exception as exc:
        logger.debug("ethereum_tx_decode failed: %s", exc)
        return {"tx_hash": tx_hash, "error": f"Request failed: {str(exc)[:100]}", "decoded": None, "pattern": None, "value_eth": 0.0, "status": None}


async def research_defi_security_audit(contract_address: str) -> dict[str, Any]:
    """Audit DeFi smart contract for vulnerabilities.

    Checks for reentrancy, unchecked calls, tx.origin usage, overflow patterns.

    Args:
        contract_address: Ethereum contract address (0x-prefixed)

    Returns:
        Dict with verified flag, vulnerabilities, risk_score, recommendations.
    """
    if not contract_address.startswith("0x") or len(contract_address) != 42:
        return {"contract_address": contract_address, "error": "Invalid address", "verified": False, "vulnerabilities": [], "risk_score": 0, "recommendations": []}

    params = {"module": "contract", "action": "getsourcecode", "address": contract_address}
    if _API_KEY:
        params["apikey"] = _API_KEY

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(_ETHERSCAN_API, params=params)
            if resp.status_code != 200:
                return {"contract_address": contract_address, "error": f"API error {resp.status_code}", "verified": False, "vulnerabilities": [], "risk_score": 0, "recommendations": []}

            data = resp.json()
            result = data.get("result", [])
            if not result or not result[0]:
                return {"contract_address": contract_address, "error": "Not verified", "verified": False, "vulnerabilities": [], "risk_score": 0, "recommendations": []}

            contract = result[0]
            source_code = contract.get("SourceCode", "")
            vulnerabilities = _scan_vulns(source_code)
            risk_score = _calculate_score(vulnerabilities)
            recommendations = _gen_recommendations(vulnerabilities)

            return {
                "contract_address": contract_address,
                "verified": contract.get("IsProxy", "0") == "0",
                "compiler_version": contract.get("CompilerVersion", "unknown"),
                "vulnerabilities": vulnerabilities,
                "risk_score": risk_score,
                "recommendations": recommendations,
                "source_length": len(source_code),
            }
    except Exception as exc:
        logger.debug("defi_security_audit failed: %s", exc)
        return {"contract_address": contract_address, "error": f"Request failed: {str(exc)[:100]}", "verified": False, "vulnerabilities": [], "risk_score": 0, "recommendations": []}


def _identify_pattern(input_data: str, to_address: str) -> str:
    """Identify transaction pattern from input data."""
    if input_data == "0x":
        return "ether_transfer"
    if len(input_data) < 10:
        return "unknown"

    selector = input_data[:10].lower()
    patterns = {
        "0xa9059cbb": "erc20_transfer",
        "0x23b872dd": "erc20_transferfrom",
        "0x095ea7b3": "erc20_approve",
        "0xe8e33700": "uniswap_swap",
        "0x414bf389": "uniswap_swap",
        "0x42842e0e": "erc721_transferfrom",
        "0xf242432a": "erc1155_transfer",
        "0xa1448194": "uniswap_nft_mint",
    }
    return patterns.get(selector, "contract_deployment" if to_address in ("0x", "") else "other")


def _scan_vulns(source_code: str) -> list[dict[str, str]]:
    """Scan for smart contract vulnerabilities."""
    vulns = []
    if not source_code:
        return vulns

    code_lower = source_code.lower()

    if "call(" in code_lower and "balance" in code_lower:
        vulns.append({"type": "potential_reentrancy", "severity": "high", "description": "Uses call() with balance check pattern"})

    if "tx.origin" in source_code:
        vulns.append({"type": "tx_origin_usage", "severity": "high", "description": "Uses tx.origin for auth"})

    if (".call(" in source_code or ".delegatecall(" in source_code) and "require(" not in source_code:
        vulns.append({"type": "unchecked_external_call", "severity": "medium", "description": "Unchecked external calls"})

    if "pragma solidity ^0." in source_code:
        version = source_code.split("pragma solidity ^0.")[1][:2]
        if version < "80":
            vulns.append({"type": "no_overflow_protection", "severity": "medium", "description": "Pre-0.8.0: no overflow protection"})

    return vulns


def _calculate_score(vulns: list[dict[str, str]]) -> int:
    """Calculate risk score (0-100)."""
    if not vulns:
        return 0
    weights = {"critical": 25, "high": 15, "medium": 8, "low": 3}
    score = sum(weights.get(v.get("severity", "low"), 3) for v in vulns)
    return min(score, 100)


def _gen_recommendations(vulns: list[dict[str, str]]) -> list[str]:
    """Generate security recommendations."""
    recs = []
    has_high = any(v.get("severity") == "high" for v in vulns)
    has_medium = any(v.get("severity") == "medium" for v in vulns)

    if has_high:
        recs.append("Get professional security audit before mainnet deployment")
    if any(v.get("type") == "potential_reentrancy" for v in vulns):
        recs.append("Use Checks-Effects-Interactions pattern")
    if any(v.get("type") == "tx_origin_usage" for v in vulns):
        recs.append("Replace tx.origin with msg.sender")
    if any(v.get("type") == "unchecked_external_call" for v in vulns):
        recs.append("Wrap external calls in require()")
    if any(v.get("type") == "no_overflow_protection" for v in vulns):
        recs.append("Upgrade to Solidity >= 0.8.0")
    if has_medium or has_high:
        recs.append("Consider formal verification")

    return recs or ["No obvious vulnerabilities detected; still recommend review"]


async def _get_receipt(client: httpx.AsyncClient, tx_hash: str) -> dict[str, Any] | None:
    """Fetch transaction receipt."""
    params = {"module": "proxy", "action": "eth_getTransactionReceipt", "txhash": tx_hash}
    if _API_KEY:
        params["apikey"] = _API_KEY

    try:
        resp = await client.get(_ETHERSCAN_API, params=params)
        if resp.status_code == 200:
            return resp.json().get("result")
    except Exception as exc:
        logger.debug("Failed to fetch receipt: %s", exc)
    return None
