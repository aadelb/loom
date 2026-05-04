# FIXED _wrap_tool FUNCTION
# This is the corrected version to replace lines 1042-1447 in src/loom/server.py

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

    if is_async:
        if category:
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
            user_id_for_rate = os.getenv("LOOM_USER_ID", "default")
            rate_limit_error = await check_tool_rate_limit(tool_name, user_id_for_rate)
            if rate_limit_error:
                log.warning("tool_rate_limit_exceeded", tool=tool_name, user_id=user_id_for_rate)
                _loom_tool_calls_total.labels(tool_name=tool_name, status="rate_limited").inc()
                return rate_limit_error

            # ── Graceful Shutdown Check ──
            if _is_shutting_down():
                grace_remaining = _shutdown_grace_time_remaining()
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
            current_balance = int(os.getenv("LOOM_USER_BALANCE", "0"))
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
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)

                # Latency Tracker: record per-tool latency
                try:
                    duration_ms = duration * 1000
                    latency_tracker = get_latency_tracker()
                    latency_tracker.record(tool_name, duration_ms)
                    # Add p95 to response if duration slow (>1000ms)
                    if duration_ms > 1000 and isinstance(result, dict):
                        stats = latency_tracker.get_percentiles(tool_name)
                        result['_latency_p95_ms'] = stats['p95']
                except Exception as e:
                    log.debug(f'Latency tracking error: {e}')

                # Billing: record usage after successful execution
                if billing_enabled:
                    duration_ms = duration * 1000
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

                return result
            except asyncio.TimeoutError:
                # Prometheus: record timeout error
                _loom_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
                _loom_tool_errors_total.labels(tool_name=tool_name, error_type="timeout").inc()
                duration = time.time() - start_time
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)

                # Latency Tracker: record timeout latency
                try:
                    duration_ms = duration * 1000
                    latency_tracker = get_latency_tracker()
                    latency_tracker.record(tool_name, duration_ms)
                except Exception as le:
                    log.debug(f'Latency tracking error: {le}')

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
                # Prometheus: record error
                error_type = type(e).__name__
                _loom_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
                _loom_tool_errors_total.labels(tool_name=tool_name, error_type=error_type).inc()
                duration = time.time() - start_time
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)

                # Latency Tracker: record error latency
                try:
                    duration_ms = duration * 1000
                    latency_tracker = get_latency_tracker()
                    latency_tracker.record(tool_name, duration_ms)
                except Exception as le:
                    log.debug(f'Latency tracking error: {le}')

                # Analytics: record tool call error
                try:
                    analytics = ToolAnalytics.get_instance()
                    duration_ms = duration * 1000
                    user_id = os.getenv("LOOM_USER_ID", "anonymous")
                    analytics.record_call(tool_name, duration_ms, False, user_id)
                except Exception as ae:
                    log.debug(f"Analytics recording error: {ae}")

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
                except Exception as audit_e:
                    log.debug(f"Audit logging error at error: {audit_e}")

                raise

        return async_wrapper
    else:
        if category:
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

            # Tool-specific rate limiting (per-tool granular limits)
            # NOTE: Using async check synchronously; may need dedicated sync implementation
            user_id_for_rate = os.getenv("LOOM_USER_ID", "default")
            try:
                # Check if we can call check_tool_rate_limit synchronously
                # For now, we skip this for sync wrappers and rely on category-level rate limiting
                # TODO: Implement sync_check_tool_rate_limit() if needed
                pass
            except Exception:
                pass

            # ── Graceful Shutdown Check ──
            if _is_shutting_down():
                grace_remaining = _shutdown_grace_time_remaining()
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
            current_balance = int(os.getenv("LOOM_USER_BALANCE", "0"))
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
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)

                # Latency Tracker: record per-tool latency (sync wrapper)
                try:
                    duration_ms = duration * 1000
                    latency_tracker = get_latency_tracker()
                    latency_tracker.record(tool_name, duration_ms)
                    # Add p95 to response if duration slow (>1000ms)
                    if duration_ms > 1000 and isinstance(result, dict):
                        stats = latency_tracker.get_percentiles(tool_name)
                        result['_latency_p95_ms'] = stats['p95']
                except Exception as e:
                    log.debug(f'Latency tracking error: {e}')

                # Billing: record usage after successful execution
                if billing_enabled:
                    duration_ms = duration * 1000
                    # Estimate credits: 1 credit per second of execution
                    credits_used = max(1, int(duration_ms / 1000))
                    try:
                        record_usage(customer_id, tool_name, credits_used, duration_ms)
                        log.debug(f"Billed {credits_used} credits to {customer_id} for {tool_name}")
                    except Exception as e:
                        log.error(f"Billing error for {tool_name}: {e}", exc_info=False)

                # Analytics: record tool call (sync wrapper)
                try:
                    analytics = ToolAnalytics.get_instance()
                    duration_ms = duration * 1000
                    user_id = os.getenv("LOOM_USER_ID", "anonymous")
                    analytics.record_call(tool_name, duration_ms, True, user_id)
                except Exception as e:
                    log.debug(f"Analytics recording error (sync): {e}")

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

                return result
            except Exception as e:
                # Prometheus: record error
                error_type = type(e).__name__
                _loom_tool_calls_total.labels(tool_name=tool_name, status="error").inc()
                _loom_tool_errors_total.labels(tool_name=tool_name, error_type=error_type).inc()
                duration = time.time() - start_time
                _loom_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)

                # Latency Tracker: record error latency (sync wrapper)
                try:
                    duration_ms = duration * 1000
                    latency_tracker = get_latency_tracker()
                    latency_tracker.record(tool_name, duration_ms)
                except Exception as le:
                    log.debug(f'Latency tracking error: {le}')

                # Analytics: record tool call error (sync wrapper)
                try:
                    analytics = ToolAnalytics.get_instance()
                    duration_ms = duration * 1000
                    user_id = os.getenv("LOOM_USER_ID", "anonymous")
                    analytics.record_call(tool_name, duration_ms, False, user_id)
                except Exception as ae:
                    log.debug(f"Analytics recording error (sync): {ae}")

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
                except Exception as audit_e:
                    log.debug(f"Audit logging error at error (sync): {audit_e}")

                raise

        return sync_wrapper
