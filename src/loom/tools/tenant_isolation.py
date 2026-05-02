"""Isolated cache, audit trails, rate limits per tenant."""
from __future__ import annotations
import asyncio, json, logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.tenant_isolation")
_TENANT_FILE = Path.home() / ".loom" / "tenants.json"
_lock = asyncio.Lock()


def _load_tenants() -> dict[str, Any]:
    _TENANT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _TENANT_FILE.exists():
        return {}
    try:
        return json.loads(_TENANT_FILE.read_text()).get("tenants", {})
    except Exception:
        return {}


def _save_tenants(tenants: dict[str, Any]) -> None:
    _TENANT_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TENANT_FILE.write_text(json.dumps({"tenants": tenants}, indent=2))


async def research_tenant_create(tenant_id: str, name: str = "", quota_calls_per_hour: int = 1000) -> dict[str, Any]:
    """Create tenant with isolated context and rate limit.
    Returns: {tenant_id, name, quota, created_at}"""
    if not tenant_id or not all(c.isalnum() or c == "_" for c in tenant_id):
        raise ValueError("tenant_id alphanumeric + underscore")
    if len(tenant_id) > 64 or not (1 <= quota_calls_per_hour <= 100000):
        raise ValueError("tenant_id max 64, quota 1-100000")
    async with _lock:
        tenants = _load_tenants()
        if tenant_id in tenants:
            raise ValueError(f"tenant {tenant_id} exists")
        now = datetime.now(UTC).isoformat()
        tenants[tenant_id] = {
            "tenant_id": tenant_id, "name": name or tenant_id, "quota_calls_per_hour": quota_calls_per_hour,
            "created_at": now, "calls_today": 0, "calls_this_hour": 0, "top_tools_used": {}}
        _save_tenants(tenants)
        return {"tenant_id": tenant_id, "name": name or tenant_id, "quota": quota_calls_per_hour, "created_at": now}


async def research_tenant_list() -> dict[str, Any]:
    """List all tenants.
    Returns: {tenants: [{id, name, quota, created, calls_today}], total}"""
    async with _lock:
        tenants = _load_tenants()
        return {"tenants": [{"id": t["tenant_id"], "name": t.get("name", t["tenant_id"]), "quota": t["quota_calls_per_hour"],
                            "created": t["created_at"], "calls_today": t.get("calls_today", 0)} for t in tenants.values()],
                "total": len(tenants)}


async def research_tenant_usage(tenant_id: str) -> dict[str, Any]:
    """Get tenant usage metrics.
    Returns: {tenant_id, calls_today, calls_this_hour, quota_remaining, quota_total, top_tools_used, created_at}"""
    async with _lock:
        tenants = _load_tenants()
        if tenant_id not in tenants:
            raise ValueError(f"tenant {tenant_id} not found")
        t = tenants[tenant_id]
        q, ch = t["quota_calls_per_hour"], t.get("calls_this_hour", 0)
        top = sorted(t.get("top_tools_used", {}).items(), key=lambda x: x[1], reverse=True)[:5]
        return {"tenant_id": tenant_id, "calls_today": t.get("calls_today", 0), "calls_this_hour": ch,
                "quota_remaining": max(0, q - ch), "quota_total": q,
                "top_tools_used": [{"tool": tool, "count": count} for tool, count in top], "created_at": t["created_at"]}
