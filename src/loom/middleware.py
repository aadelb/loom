"""Middleware for Loom MCP tool wrapping.

Contains _wrap_tool which wraps every registered tool with:
- Rate limiting
- Prometheus metrics
- Billing/token economy
- Audit logging
- WebSocket broadcasts
- SLA monitoring
- Graceful shutdown checks
- Response normalization

Extracted from server.py to reduce monolith size.
"""
from __future__ import annotations

import asyncio
import difflib
import functools
import inspect
import logging
import os
import time
from collections.abc import Callable
from typing import Any

from loom.server_state import is_shutting_down, shutdown_grace_time_remaining
from loom.tracing import new_request_id
from loom.rate_limiter import rate_limited
from loom.feature_flags import get_feature_flags
from loom.audit import log_invocation
from loom.alerting import handle_tool_error
from loom.websocket import get_ws_manager
from loom.tool_latency import get_latency_tracker
from loom.tool_rate_limiter import check_tool_rate_limit
from loom.sla_monitor import get_sla_monitor
from loom.analytics import ToolAnalytics
from loom.billing.meter import record_usage
from loom.billing.token_economy import check_balance, get_tool_cost

log = logging.getLogger("loom.middleware")

# ── Prometheus metrics (optional, graceful fallback if not installed) ──
try:
    from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest

    # Create a registry for Loom metrics
    _PROMETHEUS_REGISTRY = CollectorRegistry()

    # Define metrics
    _loom_tool_calls_total = Counter(
        "loom_tool_calls_total",
        "Total MCP tool calls",
        labelnames=["tool_name", "status"],
        registry=_PROMETHEUS_REGISTRY,
    )

    _loom_tool_duration_seconds = Histogram(
        "loom_tool_duration_seconds",
        "Tool execution duration in seconds",
        labelnames=["tool_name"],
        registry=_PROMETHEUS_REGISTRY,
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")),
    )

    _loom_tool_errors_total = Counter(
        "loom_tool_errors_total",
        "Total MCP tool errors by type",
        labelnames=["tool_name", "error_type"],
        registry=_PROMETHEUS_REGISTRY,
    )

    _prometheus_enabled = True

except ImportError:
    # Stub classes for when prometheus_client is not installed
    _prometheus_enabled = False
    _PROMETHEUS_REGISTRY = None

    class _StubCounter:
        def labels(self, **kwargs):
            return self
        def inc(self, amount=1):
            pass

    class _StubHistogram:
        def labels(self, **kwargs):
            return self
        def observe(self, value):
            pass

    _loom_tool_calls_total = _StubCounter()
    _loom_tool_duration_seconds = _StubHistogram()
    _loom_tool_errors_total = _StubCounter()


PARAM_ALIASES: dict[str, str] = {
    "search_query": "query",
    "max_results": "limit",
    "model_name": "model",
    "timeout_seconds": "timeout",
    "target_url": "url",
    "url_list": "urls",
    "strategy_name": "strategy",
    "target_language": "target_lang",
}

_NOT_FOUND = object()  # Sentinel to distinguish "looked up and not found" from "never looked up"
_pydantic_model_cache: dict[str, type | object] = {}


def _resolve_aliases(kwargs: dict, valid_params: set[str]) -> dict:
    """Resolve parameter aliases to canonical names."""
    resolved = {}
    for key, value in kwargs.items():
        canonical = PARAM_ALIASES.get(key, key)
        if canonical in valid_params:
            resolved[canonical] = value
        else:
            resolved[key] = value
    return resolved


def _validate_with_pydantic(tool_name: str, kwargs: dict) -> dict:
    """Auto-validate params using Pydantic model if one exists.

    Looks up model by naming convention: research_foo → FooParams.
    Falls back to unvalidated kwargs if no model found.
    """
    cached = _pydantic_model_cache.get(tool_name)
    if cached is _NOT_FOUND:
        # Already looked up and not found — skip retry
        return kwargs
    elif cached is not None:
        # Found and cached
        model_cls = cached
    else:
        # Not looked up yet
        suffix = tool_name.replace("research_", "")
        model_name = "".join(w.capitalize() for w in suffix.split("_")) + "Params"
        model_cls = None
        try:
            import loom.params as params_pkg
            for mod_name in ["core", "llm", "intelligence", "adversarial",
                             "infrastructure", "academic", "security",
                             "research", "operations"]:
                mod = getattr(params_pkg, mod_name, None)
                if mod and hasattr(mod, model_name):
                    model_cls = getattr(mod, model_name)
                    break
        except Exception:
            pass
        # Only cache if found; use sentinel if not found
        if model_cls is not None:
            _pydantic_model_cache[tool_name] = model_cls
        else:
            _pydantic_model_cache[tool_name] = _NOT_FOUND

    if model_cls is None:
        return kwargs

    try:
        validated = model_cls(**kwargs)
        return validated.model_dump()
    except Exception as exc:
        log.debug("pydantic_validation_skip tool=%s error=%s", tool_name, exc)
        return kwargs


def _fuzzy_correct_params(func: Callable[..., Any], kwargs: dict) -> tuple[dict, dict]:
    """Auto-correct misspelled param names using fuzzy matching.

    Also resolves parameter aliases and applies Pydantic validation
    if a matching model exists in loom.params.

    Args:
        func: The function to extract parameter names from
        kwargs: The keyword arguments to correct

    Returns:
        Tuple of (corrected_kwargs, corrections_made)
        corrections_made is dict mapping wrong_param -> correct_param (or None if dropped)
    """
    import inspect

    sig = inspect.signature(func)
    valid_params = set(sig.parameters.keys())

    kwargs = _resolve_aliases(kwargs, valid_params)

    corrected = {}
    corrections = {}

    for key, value in kwargs.items():
        if key in valid_params:
            corrected[key] = value
        else:
            matches = difflib.get_close_matches(key, valid_params, n=1, cutoff=0.7)
            if matches:
                corrected[matches[0]] = value
                corrections[key] = matches[0]
            else:
                corrections[key] = None
                log.warning("param_dropped tool=%s param=%s (no close match found)", func.__name__, key)

    tool_name = func.__name__
    corrected = _validate_with_pydantic(tool_name, corrected)

    return corrected, corrections


def _normalize_result(
    result: Any, tool_name: str, category: str | None, duration: float
) -> dict[str, Any]:
    """Normalize any tool return type into the standard ToolResponse envelope.

    Handles: dict, list[TextContent], list, str, None.
    Uses setdefault on dicts to never overwrite existing keys.
    """
    import json as _json

    elapsed_ms = int(duration * 1000)

    if isinstance(result, dict):
        result.setdefault("source", tool_name)
        result.setdefault("category", category or "")
        result.setdefault("elapsed_ms", elapsed_ms)
        return result

    # Handle TextContent lists (20 tool files return this format)
    if isinstance(result, list) and result and hasattr(result[0], "text"):
        try:
            inner = _json.loads(result[0].text)
            if isinstance(inner, dict):
                inner.setdefault("source", tool_name)
                inner.setdefault("category", category or "")
                inner.setdefault("elapsed_ms", elapsed_ms)
                return inner
        except (ValueError, AttributeError, IndexError):
            pass
        return {
            "results": [getattr(r, "text", str(r)) for r in result],
            "total_count": len(result),
            "source": tool_name,
            "category": category or "",
            "elapsed_ms": elapsed_ms,
        }

    if isinstance(result, list):
        return {
            "results": result,
            "total_count": len(result),
            "source": tool_name,
            "category": category or "",
            "elapsed_ms": elapsed_ms,
        }

    if result is None:
        return {"results": None, "source": tool_name, "category": category or "", "elapsed_ms": elapsed_ms}

    return {"results": result, "source": tool_name, "category": category or "", "elapsed_ms": elapsed_ms}


def _wrap_tool(func: Callable[..., Any], category: str | None = None) -> Callable[..., Any]:
    """Wrap tool with tracing, rate limiting, metrics, and optional billing.

    Handles both sync and async tool functions correctly.
    Instruments tools with Prometheus metrics (call count, duration, errors).
    """
    import inspect

    is_async = inspect.iscoroutinefunction(func)

    tool_timeout = 60  # seconds
    billing_enabled = os.getenv("LOOM_BILLING_ENABLED", "").lower() == "true"
    token_economy_enabled = os.getenv("LOOM_TOKEN_ECONOMY", "").lower() == "true"
    tool_name = func.__name__

    # Detect if function is CPU-bound
    is_cpu_bound_func = getattr(func, "_cpu_bound", False) is True


    if is_async:
        if category and not getattr(func, "_rate_limited", False):
            func = rate_limited(category)(func)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            request_id = new_request_id()
            start_time = time.time()
            # Auto-correct parameters
            corrected_kwargs, corrections = _fuzzy_correct_params(func, kwargs)
            if corrections:
                log.debug(f"Parameter corrections for {tool_name}: {corrections}")

            # Tool-specific rate limiting (per-tool granular limits)
            # Check feature flag before applying per-tool rate limiting
            ff = get_feature_flags()
            if ff.is_enabled("per_tool_rate_limit"):
                user_id_for_rate = os.getenv("LOOM_USER_ID", "default")
                rate_limit_error = await check_tool_rate_limit(tool_name, user_id_for_rate)
                if rate_limit_error:
                    log.warning("tool_rate_limit_exceeded", tool=tool_name, user_id=user_id_for_rate)
                    _loom_tool_calls_total.labels(tool_name=tool_name, status="rate_limited").inc()
                    return rate_limit_error

            # ── Graceful Shutdown Check ──
            if is_shutting_down():
                grace_remaining = shutdown_grace_time_remaining()
                log.warning("tool_call_during_shutdown tool=%s grace_remaining_seconds=%.1f", tool_name, grace_remaining)
                _loom_tool_calls_total.labels(tool_name=tool_name, status="shutdown").inc()
                return {
                    "error": "server_shutting_down",
                    "message": "Server is shutting down. No new tool calls accepted.",
                    "retry_after_seconds": int(grace_remaining) + 1,
                    "graceful_shutdown": True,
                }


            # Token Economy: check credits before execution (if enabled)
            user_id = os.getenv("LOOM_USER_ID", "anonymous")
            try:
                current_balance = int(os.getenv("LOOM_USER_BALANCE", "0"))
            except ValueError:
                log.warning(f"Invalid LOOM_USER_BALANCE value, defaulting to 0")
                current_balance = 0
            token_economy_result = {}

            if token_economy_enabled:
                balance_check = check_balance(user_id, current_balance, tool_name)

                if not balance_check["sufficient"]:
                    log.warning(
                        "insufficient_credits",
                        user_id=user_id,
                        tool_name=tool_name,
                        required=balance_check["required"],
                        balance=balance_check["balance"],
                        shortfall=balance_check["shortfall"],
                    )
                    return {
                        "error": "insufficient_credits",
                        "message": f"Tool '{tool_name}' requires {balance_check['required']} credits, but you have {balance_check['balance']}. Need {balance_check['shortfall']} more credits.",
                        "tool": tool_name,
                        "required_credits": balance_check["required"],
                        "available_credits": balance_check["balance"],
                        "shortfall": balance_check["shortfall"],
                    }

                token_economy_result = {
                    "cost": balance_check["required"],
                    "balance_before": current_balance,
                }

            # Billing: check credits before execution (if enabled)
            customer_id = os.getenv("LOOM_CUSTOMER_ID", "default")
            if billing_enabled:
                # Credit check would go here; for now we just record
                log.debug(f"Billing enabled for tool {tool_name}, customer {customer_id}")

            try:
                # WebSocket: broadcast tool started
                try:
                    ws_mgr = get_ws_manager()
                    job_id = request_id
                    await ws_mgr.broadcast_tool_started(tool_name, job_id)
                except Exception as ws_e:
                    log.debug(f"WebSocket broadcast error (tool.started): {ws_e}")

                result = await asyncio.wait_for(func(*args, **corrected_kwargs), timeout=tool_timeout)
                # Add correction metadata if there were corrections
                if corrections and isinstance(result, dict):
                    result["_param_corrections"] = corrections

                # Token Economy: deduct credits after successful execution
                if token_economy_enabled:
                    cost = get_tool_cost(tool_name)
                    new_balance = max(0, current_balance - cost)
                    token_economy_result["balance_after"] = new_balance

                    log.info(
                        "token_economy_deduction",
                        user_id=user_id,
                        tool_name=tool_name,
                        cost=cost,
                        balance_before=current_balance,
                        balance_after=new_balance,
                    )

                    if isinstance(result, dict):
                        result["_token_economy"] = token_economy_result

                # Prometheus: record success
                _loom_tool_calls_total.labels(tool_name=tool_name, status="success").inc()
                duration = time.time() - start_time
                duration_ms = duration * 1000
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)

                # Latency Tracker: record per-tool latency
                try:
                    latency_tracker = get_latency_tracker()
                    latency_tracker.record(tool_name, duration_ms)
                    # Add p95 to response if duration slow (>1000ms)
                    if duration_ms > 1000 and isinstance(result, dict):
                        stats = latency_tracker.get_percentiles(tool_name)
                        result['_latency_p95_ms'] = stats['p95']
                except Exception as e:
                    log.debug(f'Latency tracking error: {e}')

                # SLA Monitor: record successful request
                try:
                    sla_monitor = get_sla_monitor()
                    sla_monitor.record_request(
                        success=True,
                        latency_ms=duration_ms,
                        tool_name=tool_name,
                    )
                    sla_monitor.check_and_alert()
                except Exception as e:
                    log.debug(f'SLA monitoring error: {e}')

                # Billing: record usage after successful execution
                if billing_enabled:
                    # Estimate credits: 1 credit per second of execution
                    credits_used = max(1, int(duration_ms / 1000))
                    try:
                        record_usage(customer_id, tool_name, credits_used, duration_ms)
                        log.debug(f"Billed {credits_used} credits to {customer_id} for {tool_name}")
                    except Exception as e:
                        log.error(f"Billing error for {tool_name}: {e}", exc_info=False)

                
                # Analytics: record tool call
                try:
                    analytics = ToolAnalytics.get_instance()
                    duration_ms = duration * 1000
                    user_id = os.getenv("LOOM_USER_ID", "anonymous")
                    analytics.record_call(tool_name, duration_ms, True, user_id)
                except Exception as e:
                    log.debug(f"Analytics recording error: {e}")

                # Audit: Log tool call success
                try:
                    client_id = os.getenv("LOOM_CLIENT_ID", os.getenv("LOOM_USER_ID", "anonymous"))
                    result_size = len(str(result)) if result else 0
                    log_invocation(
                        client_id=client_id,
                        tool_name=tool_name,
                        params=corrected_kwargs,
                        result_summary=f"success: {result_size} bytes",
                        duration_ms=int(duration_ms),
                        status="success"
                    )
                except Exception as audit_e:
                    log.debug(f"Audit logging error at success: {audit_e}")

                # WebSocket: broadcast tool completed (success)
                try:
                    ws_mgr = get_ws_manager()
                    duration_ms = int(duration * 1000)
                    job_id = request_id
                    await ws_mgr.broadcast_tool_completed(tool_name, job_id, duration_ms, True)
                except Exception as ws_e:
                    log.debug(f"WebSocket broadcast error (tool.completed): {ws_e}")

                result = _normalize_result(result, tool_name, category, duration)
                return result
            except asyncio.TimeoutError:
                # Prometheus: record timeout error
                _loom_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
                _loom_tool_errors_total.labels(tool_name=tool_name, error_type="timeout").inc()
                duration = time.time() - start_time
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)
                
                # Analytics: record tool call error
                try:
                    analytics = ToolAnalytics.get_instance()
                    duration_ms = duration * 1000
                    user_id = os.getenv("LOOM_USER_ID", "anonymous")
                    analytics.record_call(tool_name, duration_ms, False, user_id)
                except Exception as e:
                    log.debug(f"Analytics recording error: {e}")

                # Audit: Log tool call timeout
                try:
                    client_id = os.getenv("LOOM_CLIENT_ID", os.getenv("LOOM_USER_ID", "anonymous"))
                    log_invocation(
                        client_id=client_id,
                        tool_name=tool_name,
                        params=corrected_kwargs,
                        result_summary="timeout_error",
                        duration_ms=int(duration * 1000),
                        status="timeout"
                    )
                except Exception as audit_e:
                    log.debug(f"Audit logging error at timeout: {audit_e}")

                return {"error": f"Tool timed out after {tool_timeout}s", "tool": tool_name}
            except Exception as e:
                # Preserve the full traceback immediately
                log.exception("tool_execution_failed tool=%s", tool_name)

                # WebSocket: broadcast tool failed
                try:
                    ws_mgr = get_ws_manager()
                    error_msg = str(e)
                    job_id = request_id
                    await ws_mgr.broadcast_tool_failed(tool_name, error_msg)
                except Exception:
                    pass

                # Prometheus: record error
                error_type = type(e).__name__
                try:
                    _loom_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
                except Exception:
                    pass
                try:
                    _loom_tool_errors_total.labels(tool_name=tool_name, error_type=error_type).inc()
                except Exception:
                    pass

                duration = time.time() - start_time
                try:
                    _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)
                except Exception:
                    pass

                # Send alert for critical errors via webhook/email
                try:
                    await handle_tool_error(tool_name, e, execution_time_ms=duration * 1000)
                except Exception:
                    pass

                # Audit: Log tool call error
                try:
                    client_id = os.getenv("LOOM_CLIENT_ID", os.getenv("LOOM_USER_ID", "anonymous"))
                    log_invocation(
                        client_id=client_id,
                        tool_name=tool_name,
                        params=corrected_kwargs,
                        result_summary=f"error: {error_type}",
                        duration_ms=int(duration * 1000),
                        status="error"
                    )
                except Exception:
                    pass

                raise

        return async_wrapper
    else:
        if category and not getattr(func, "_rate_limited", False):
            from loom.rate_limiter import sync_rate_limited
            func = sync_rate_limited(category)(func)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            request_id = new_request_id()
            start_time = time.time()
            # Auto-correct parameters
            corrected_kwargs, corrections = _fuzzy_correct_params(func, kwargs)
            if corrections:
                log.debug(f"Parameter corrections for {tool_name}: {corrections}")

            # ── Graceful Shutdown Check ──
            if is_shutting_down():
                grace_remaining = shutdown_grace_time_remaining()
                log.warning("tool_call_during_shutdown sync tool=%s grace_remaining_seconds=%.1f", tool_name, grace_remaining)
                _loom_tool_calls_total.labels(tool_name=tool_name, status="shutdown").inc()
                return {
                    "error": "server_shutting_down",
                    "message": "Server is shutting down. No new tool calls accepted.",
                    "retry_after_seconds": int(grace_remaining) + 1,
                    "graceful_shutdown": True,
                }


            # Token Economy: check credits before execution (if enabled)
            user_id = os.getenv("LOOM_USER_ID", "anonymous")
            try:
                current_balance = int(os.getenv("LOOM_USER_BALANCE", "0"))
            except ValueError:
                log.warning(f"Invalid LOOM_USER_BALANCE value, defaulting to 0")
                current_balance = 0
            token_economy_result = {}

            if token_economy_enabled:
                balance_check = check_balance(user_id, current_balance, tool_name)

                if not balance_check["sufficient"]:
                    log.warning(
                        "insufficient_credits",
                        user_id=user_id,
                        tool_name=tool_name,
                        required=balance_check["required"],
                        balance=balance_check["balance"],
                        shortfall=balance_check["shortfall"],
                    )
                    return {
                        "error": "insufficient_credits",
                        "message": f"Tool '{tool_name}' requires {balance_check['required']} credits, but you have {balance_check['balance']}. Need {balance_check['shortfall']} more credits.",
                        "tool": tool_name,
                        "required_credits": balance_check["required"],
                        "available_credits": balance_check["balance"],
                        "shortfall": balance_check["shortfall"],
                    }

                token_economy_result = {
                    "cost": balance_check["required"],
                    "balance_before": current_balance,
                }

            # Billing: check credits before execution (if enabled)
            customer_id = os.getenv("LOOM_CUSTOMER_ID", "default")
            if billing_enabled:
                # Credit check would go here; for now we just record
                log.debug(f"Billing enabled for tool {tool_name}, customer {customer_id}")

            try:
                result = func(*args, **corrected_kwargs)
                # Add correction metadata if there were corrections
                if corrections and isinstance(result, dict):
                    result["_param_corrections"] = corrections

                # Token Economy: deduct credits after successful execution
                if token_economy_enabled:
                    cost = get_tool_cost(tool_name)
                    new_balance = max(0, current_balance - cost)
                    token_economy_result["balance_after"] = new_balance
                    
                    log.info(
                        "token_economy_deduction",
                        user_id=user_id,
                        tool_name=tool_name,
                        cost=cost,
                        balance_before=current_balance,
                        balance_after=new_balance,
                    )
                    
                    if isinstance(result, dict):
                        result["_token_economy"] = token_economy_result

                # Prometheus: record success
                _loom_tool_calls_total.labels(tool_name=tool_name, status="success").inc()
                duration = time.time() - start_time
                duration_ms = duration * 1000
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)

                # Latency Tracker: record per-tool latency (sync wrapper)
                try:
                    latency_tracker = get_latency_tracker()
                    latency_tracker.record(tool_name, duration_ms)
                    # Add p95 to response if duration slow (>1000ms)
                    if duration_ms > 1000 and isinstance(result, dict):
                        stats = latency_tracker.get_percentiles(tool_name)
                        result['_latency_p95_ms'] = stats['p95']
                except Exception as e:
                    log.debug(f'Latency tracking error: {e}')

                # SLA Monitor: record successful request
                try:
                    sla_monitor = get_sla_monitor()
                    sla_monitor.record_request(
                        success=True,
                        latency_ms=duration_ms,
                        tool_name=tool_name,
                    )
                    sla_monitor.check_and_alert()
                except Exception as e:
                    log.debug(f'SLA monitoring error: {e}')

                # Billing: record usage after successful execution
                if billing_enabled:
                    # Estimate credits: 1 credit per second of execution
                    credits_used = max(1, int(duration_ms / 1000))
                    try:
                        record_usage(customer_id, tool_name, credits_used, duration_ms)
                        log.debug(f"Billed {credits_used} credits to {customer_id} for {tool_name}")
                    except Exception as e:
                        log.error(f"Billing error for {tool_name}: {e}", exc_info=False)

                # Audit: Log tool call success (sync wrapper)
                try:
                    client_id = os.getenv("LOOM_CLIENT_ID", os.getenv("LOOM_USER_ID", "anonymous"))
                    result_size = len(str(result)) if result else 0
                    log_invocation(
                        client_id=client_id,
                        tool_name=tool_name,
                        params=corrected_kwargs,
                        result_summary=f"success: {result_size} bytes",
                        duration_ms=int(duration_ms),
                        status="success"
                    )
                except Exception as audit_e:
                    log.debug(f"Audit logging error at success (sync): {audit_e}")

                result = _normalize_result(result, tool_name, category, duration)
                return result
            except Exception as e:
                # Preserve the full traceback immediately
                log.exception("tool_execution_failed tool=%s", tool_name)

                # Prometheus: record error
                error_type = type(e).__name__
                try:
                    _loom_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
                except Exception:
                    pass
                try:
                    _loom_tool_errors_total.labels(tool_name=tool_name, error_type=error_type).inc()
                except Exception:
                    pass

                duration = time.time() - start_time
                try:
                    _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)
                except Exception:
                    pass

                # Audit: Log tool call error (sync wrapper)
                try:
                    client_id = os.getenv("LOOM_CLIENT_ID", os.getenv("LOOM_USER_ID", "anonymous"))
                    log_invocation(
                        client_id=client_id,
                        tool_name=tool_name,
                        params=corrected_kwargs,
                        result_summary=f"error: {error_type}",
                        duration_ms=int(duration * 1000),
                        status="error"
                    )
                except Exception:
                    pass

                raise

        return sync_wrapper

