"""Infrastructure, operations, and integration tools.

Tools for deployment, monitoring, caching, alerting, storage, authentication,
and external service integrations.
"""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.infrastructure")


def register_infrastructure_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 104 infrastructure, ops, and integration tools.

    Includes deployment, monitoring, billing, authentication, data export,
    and external service integrations (VastAI, Vercel, YouTube, etc.).
    """
    # Core infrastructure modules
    from loom.tools import (
        error_wrapper,
        response_cache,
        data_pipeline,
        input_sanitizer,
        metric_alerts,
        plugin_loader,
        data_export,
        rate_limiter_tool,
        circuit_breaker,
        feature_flags,
        config_reload,
        composition_optimizer,
        context_manager,
        provider_health,
        health_dashboard,
        backup_system,
        benchmark_suite,
        request_queue,
        memory_mgmt,
        tool_profiler,
        deployment,
        audit_log,
        env_inspector,
        enterprise_sso,
        redteam_hub,
        backoff_dlq,
        replay_engine,
        schema_migrate,
        capability_matrix,
        changelog_gen,
        compliance_checker,
        credential_vault,
        dependency_graph,
        evidence_fusion,
        full_pipeline,
        functor_map,
        gamification,
        holistic_scorer,
        integration_runner,
        knowledge_base,
        knowledge_injector,
        lifetime_oracle,
        live_registry,
        network_map,
        notifications,
        observability,
        output_formatter,
        output_diff,
        persistent_memory,
        strategy_cache,
        strategy_feedback,
        strategy_ab_test,
        strategy_evolution,
        startup_validator,
        task_resolver,
        telemetry,
        tenant_isolation,
        tool_catalog,
        tool_tags,
        tool_versioning,
        traffic_capture,
        usage_analytics,
        json_logger,
        key_rotation,
    )

    # Error handling and caching
    mcp.tool()(wrap_tool(error_wrapper.research_error_stats))
    mcp.tool()(wrap_tool(error_wrapper.research_error_clear))
    mcp.tool()(wrap_tool(response_cache.research_cache_store))
    mcp.tool()(wrap_tool(response_cache.research_cache_lookup))

    # Data pipeline
    mcp.tool()(wrap_tool(data_pipeline.research_pipeline_create))
    mcp.tool()(wrap_tool(data_pipeline.research_pipeline_validate))
    mcp.tool()(wrap_tool(data_pipeline.research_pipeline_list))
    mcp.tool()(wrap_tool(input_sanitizer.research_sanitize_input))
    mcp.tool()(wrap_tool(input_sanitizer.research_validate_params))

    # Alerting and monitoring
    mcp.tool()(wrap_tool(metric_alerts.research_alert_create))
    mcp.tool()(wrap_tool(metric_alerts.research_alert_check))
    mcp.tool()(wrap_tool(metric_alerts.research_alert_list))

    # Plugin management
    mcp.tool()(wrap_tool(plugin_loader.research_plugin_load))
    mcp.tool()(wrap_tool(plugin_loader.research_plugin_list))
    mcp.tool()(wrap_tool(plugin_loader.research_plugin_unload))

    # Data export
    mcp.tool()(wrap_tool(data_export.research_export_json))
    mcp.tool()(wrap_tool(data_export.research_export_csv))
    mcp.tool()(wrap_tool(data_export.research_export_list))

    # Rate limiting
    mcp.tool()(wrap_tool(rate_limiter_tool.research_ratelimit_check))
    mcp.tool()(wrap_tool(rate_limiter_tool.research_ratelimit_configure))
    mcp.tool()(wrap_tool(rate_limiter_tool.research_ratelimit_status))

    # Circuit breaker
    mcp.tool()(wrap_tool(circuit_breaker.research_breaker_status))
    mcp.tool()(wrap_tool(circuit_breaker.research_breaker_trip))
    mcp.tool()(wrap_tool(circuit_breaker.research_breaker_reset))

    # Feature flags
    mcp.tool()(wrap_tool(feature_flags.research_flag_check))
    mcp.tool()(wrap_tool(feature_flags.research_flag_toggle))
    mcp.tool()(wrap_tool(feature_flags.research_flag_list))

    # Configuration
    mcp.tool()(wrap_tool(config_reload.research_config_watch))
    mcp.tool()(wrap_tool(config_reload.research_config_check))
    mcp.tool()(wrap_tool(config_reload.research_config_diff))

    # Composition and context
    mcp.tool()(wrap_tool(composition_optimizer.research_optimize_workflow))
    mcp.tool()(wrap_tool(composition_optimizer.research_parallel_plan))
    mcp.tool()(wrap_tool(composition_optimizer.research_optimizer_rebuild))
    mcp.tool()(wrap_tool(context_manager.research_context_set))
    mcp.tool()(wrap_tool(context_manager.research_context_get))
    mcp.tool()(wrap_tool(context_manager.research_context_clear))

    # Provider health
    mcp.tool()(wrap_tool(provider_health.research_provider_ping))
    mcp.tool()(wrap_tool(provider_health.research_provider_history))
    mcp.tool()(wrap_tool(provider_health.research_provider_recommend))

    # Dashboard and system status
    mcp.tool()(wrap_tool(health_dashboard.research_dashboard_html))

    # Backup and recovery
    mcp.tool()(wrap_tool(backup_system.research_backup_create))
    mcp.tool()(wrap_tool(backup_system.research_backup_list))
    mcp.tool()(wrap_tool(backup_system.research_backup_restore))

    # Benchmarking
    mcp.tool()(wrap_tool(benchmark_suite.research_benchmark_run))
    mcp.tool()(wrap_tool(benchmark_suite.research_benchmark_compare))

    # Request queue
    mcp.tool()(wrap_tool(request_queue.research_queue_add))
    mcp.tool()(wrap_tool(request_queue.research_queue_status))
    mcp.tool()(wrap_tool(request_queue.research_queue_drain))

    # Memory management
    mcp.tool()(wrap_tool(memory_mgmt.research_memory_status))
    mcp.tool()(wrap_tool(memory_mgmt.research_memory_gc))
    mcp.tool()(wrap_tool(memory_mgmt.research_memory_profile))

    # Tool profiling
    mcp.tool()(wrap_tool(tool_profiler.research_profile_tool))
    mcp.tool()(wrap_tool(tool_profiler.research_profile_hotspots))

    # Deployment
    mcp.tool()(wrap_tool(deployment.research_deploy_status))
    mcp.tool()(wrap_tool(deployment.research_deploy_history))
    mcp.tool()(wrap_tool(deployment.research_deploy_record))

    # Auditing
    mcp.tool()(wrap_tool(audit_log.research_audit_record))
    mcp.tool()(wrap_tool(audit_log.research_audit_query))
    mcp.tool()(wrap_tool(audit_log.research_audit_export))

    # Environment and system
    mcp.tool()(wrap_tool(env_inspector.research_env_inspect))
    mcp.tool()(wrap_tool(env_inspector.research_env_requirements))

    # Enterprise SSO
    mcp.tool()(wrap_tool(enterprise_sso.research_sso_configure))
    mcp.tool()(wrap_tool(enterprise_sso.research_sso_validate_token))
    mcp.tool()(wrap_tool(enterprise_sso.research_sso_user_info))

    # Red team hub
    mcp.tool()(wrap_tool(redteam_hub.research_hub_share))
    mcp.tool()(wrap_tool(redteam_hub.research_hub_feed))
    mcp.tool()(wrap_tool(redteam_hub.research_hub_vote))

    # Dead letter queue
    mcp.tool()(wrap_tool(backoff_dlq.research_dlq_push))
    mcp.tool()(wrap_tool(backoff_dlq.research_dlq_list))
    mcp.tool()(wrap_tool(backoff_dlq.research_dlq_retry))

    # Additional infrastructure tools
    mcp.tool()(wrap_tool(startup_validator.research_validate_startup))
    mcp.tool()(wrap_tool(telemetry.research_telemetry_record))
    mcp.tool()(wrap_tool(telemetry.research_telemetry_query))
    mcp.tool()(wrap_tool(usage_analytics.research_usage_record))
    mcp.tool()(wrap_tool(usage_analytics.research_usage_trends))
    mcp.tool()(wrap_tool(usage_analytics.research_usage_report))

    # Optional infrastructure integrations
    with suppress(ImportError):
        from loom.tools import vastai as vastai_tools

        mcp.tool()(wrap_tool(vastai_tools.research_vastai_search))
        mcp.tool()(wrap_tool(vastai_tools.research_vastai_status))

    with suppress(ImportError):
        from loom.tools import billing as billing_tools

        mcp.tool()(wrap_tool(billing_tools.research_stripe_balance))
        mcp.tool()(wrap_tool(billing_tools.research_stripe_list_invoices))

    with suppress(ImportError):
        from loom.tools import email_report as email_tools

        mcp.tool()(wrap_tool(email_tools.research_email_send_report))
        mcp.tool()(wrap_tool(email_tools.research_email_schedule))

    with suppress(ImportError):
        from loom.tools import joplin as joplin_tools

        mcp.tool()(wrap_tool(joplin_tools.research_joplin_create))
        mcp.tool()(wrap_tool(joplin_tools.research_joplin_update))

    with suppress(ImportError):
        from loom.tools import metrics as metrics_tools

        mcp.tool()(wrap_tool(metrics_tools.research_metrics_record))
        mcp.tool()(wrap_tool(metrics_tools.research_metrics_query))

    log.info("registered infrastructure tools", tool_count=104)
