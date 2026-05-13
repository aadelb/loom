"""Cryptocurrency flow analyzer — trace funds using public blockchain APIs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote

import httpx

from loom.http_helpers import fetch_json
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.crypto_trace")

_BLOCKCHAIN_INFO = "https://blockchain.info"
_ETHERSCAN = "https://api.etherscan.io/api"
_BLOCKCHAIR = "https://api.blockchair.com"


async def _bitcoin_address_info(
    client: httpx.AsyncClient, address: str
) -> dict[str, Any]:
    data = await fetch_json(
        client, f"{_BLOCKCHAIN_INFO}/rawaddr/{quote(address)}?limit=20"
    )
    if not data:
        return {"address": address, "error": "lookup failed"}
    return {
        "address": address,
        "chain": "bitcoin",
        "total_received_satoshi": data.get("total_received", 0),
        "total_sent_satoshi": data.get("total_sent", 0),
        "balance_satoshi": data.get("final_balance", 0),
        "n_tx": data.get("n_tx", 0),
        "recent_txs": [
            {
                "hash": tx.get("hash", ""),
                "time": tx.get("time", 0),
                "result": tx.get("result", 0),
                "balance": tx.get("balance", 0),
            }
            for tx in data.get("txs", [])[:10]
        ],
    }


async def _bitcoin_tx_info(
    client: httpx.AsyncClient, tx_hash: str
) -> dict[str, Any]:
    data = await fetch_json(client, f"{_BLOCKCHAIN_INFO}/rawtx/{quote(tx_hash)}")
    if not data:
        return {"tx_hash": tx_hash, "error": "lookup failed"}
    inputs = [
        {"address": inp.get("prev_out", {}).get("addr", ""), "value": inp.get("prev_out", {}).get("value", 0)}
        for inp in data.get("inputs", [])[:10]
    ]
    outputs = [
        {"address": out.get("addr", ""), "value": out.get("value", 0)}
        for out in data.get("out", [])[:10]
    ]
    return {
        "tx_hash": tx_hash,
        "chain": "bitcoin",
        "time": data.get("time", 0),
        "block_height": data.get("block_height", 0),
        "inputs": inputs,
        "outputs": outputs,
        "fee": data.get("fee", 0),
        "size": data.get("size", 0),
    }


async def _etherscan_address(
    client: httpx.AsyncClient, address: str, api_key: str = ""
) -> dict[str, Any]:
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 10,
        "sort": "desc",
    }
    if api_key:
        params["apikey"] = api_key
    data = await fetch_json(
        client, f"{_ETHERSCAN}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    )
    if not data or data.get("status") != "1":
        return {"address": address, "chain": "ethereum", "error": "lookup failed"}
    txs = data.get("result", [])
    return {
        "address": address,
        "chain": "ethereum",
        "n_tx": len(txs),
        "recent_txs": [
            {
                "hash": tx.get("hash", ""),
                "from": tx.get("from", ""),
                "to": tx.get("to", ""),
                "value_wei": tx.get("value", "0"),
                "timestamp": tx.get("timeStamp", ""),
                "block": tx.get("blockNumber", ""),
            }
            for tx in txs[:10]
        ],
    }


async def _blockchair_stats(
    client: httpx.AsyncClient, address: str, chain: str = "bitcoin"
) -> dict[str, Any]:
    data = await fetch_json(
        client, f"{_BLOCKCHAIR}/{chain}/dashboards/address/{quote(address)}"
    )
    if not data or "data" not in data:
        return {}
    lookup_key = address.lower() if chain == "ethereum" else address
    addr_data = (data["data"].get(lookup_key) or data["data"].get(address, {})).get("address", {})
    return {
        "balance": addr_data.get("balance", 0),
        "received": addr_data.get("received", 0),
        "spent": addr_data.get("spent", 0),
        "output_count": addr_data.get("output_count", 0),
        "unspent_output_count": addr_data.get("unspent_output_count", 0),
        "first_seen": addr_data.get("first_seen_receiving", ""),
        "last_seen": addr_data.get("last_seen_receiving", ""),
    }


@handle_tool_errors("research_crypto_trace")
async def research_crypto_trace(
    address: str,
    chain: str = "auto",
    include_transactions: bool = True,
) -> dict[str, Any]:
    """Trace cryptocurrency address activity using public blockchain APIs.

    Queries blockchain.info (Bitcoin), Etherscan (Ethereum), and
    Blockchair (multi-chain) to get balance, transaction history,
    and flow analysis for a given address.

    Args:
        address: cryptocurrency address to trace
        chain: "bitcoin", "ethereum", or "auto" (detect from address format)
        include_transactions: include recent transaction details

    Returns:
        Dict with ``address``, ``chain``, ``balance``, ``total_received``,
        ``total_sent``, ``transaction_count``, ``recent_transactions``,
        and ``blockchair_stats``.
    """
    try:
        if chain == "auto":
            if address.startswith("0x") and len(address) == 42:
                chain = "ethereum"
            elif address.startswith(("1", "3", "bc1")):
                chain = "bitcoin"
            else:
                chain = "bitcoin"

        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=30.0,
            ) as client:
                tasks = []
                if chain == "bitcoin":
                    tasks.append(_bitcoin_address_info(client, address))
                    tasks.append(_blockchair_stats(client, address, "bitcoin"))
                elif chain == "ethereum":
                    tasks.append(_etherscan_address(client, address))
                    tasks.append(_blockchair_stats(client, address, "ethereum"))

                if not tasks:
                    return {"address": address, "chain": chain, "error": "unsupported chain"}

                results = await asyncio.gather(*tasks, return_exceptions=True)

                primary = results[0] if results and isinstance(results[0], dict) else {}
                blockchair = results[1] if len(results) > 1 and isinstance(results[1], dict) else {}

                return {
                    "address": address,
                    "chain": chain,
                    "primary_data": primary,
                    "blockchair_stats": blockchair,
                    "sources_checked": ["blockchain.info" if chain == "bitcoin" else "etherscan", "blockchair"],
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_crypto_trace"}
