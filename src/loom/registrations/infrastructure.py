"""Registration module for infrastructure tools."""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.infrastructure")


def register_infrastructure_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 41 infrastructure tools."""
    from loom.registrations.tracking import record_success, record_failure

    try:
        from loom.tools.audit_log import research_audit_record, research_audit_query, research_audit_export
        mcp.tool()(wrap_tool(research_audit_record))
        record_success("infrastructure", "research_audit_record")
        mcp.tool()(wrap_tool(research_audit_query))
        record_success("infrastructure", "research_audit_query")
        mcp.tool()(wrap_tool(research_audit_export))
        record_success("infrastructure", "research_audit_export")
    except (ImportError, AttributeError) as e:
        log.debug("skip audit_log: %s", e)
        record_failure("infrastructure", "audit_log", str(e))
    try:
        from loom.tools.backup_system import research_backup_create, research_backup_list, research_backup_restore
        mcp.tool()(wrap_tool(research_backup_create))
        record_success("infrastructure", "research_backup_create")
        mcp.tool()(wrap_tool(research_backup_list))
        record_success("infrastructure", "research_backup_list")
        mcp.tool()(wrap_tool(research_backup_restore))
        record_success("infrastructure", "research_backup_restore")
    except (ImportError, AttributeError) as e:
        log.debug("skip backup_system: %s", e)
        record_failure("infrastructure", "backup_system", str(e))
    try:
        from loom.tools.billing import research_stripe_balance
        mcp.tool()(wrap_tool(research_stripe_balance))
        record_success("infrastructure", "research_stripe_balance")
    except (ImportError, AttributeError) as e:
        log.debug("skip billing_mod: %s", e)
        record_failure("infrastructure", "billing", str(e))
    try:
        from loom.tools.config_reload import research_config_watch, research_config_check, research_config_diff
        mcp.tool()(wrap_tool(research_config_watch))
        record_success("infrastructure", "research_config_watch")
        mcp.tool()(wrap_tool(research_config_check))
        record_success("infrastructure", "research_config_check")
        mcp.tool()(wrap_tool(research_config_diff))
        record_success("infrastructure", "research_config_diff")
    except (ImportError, AttributeError) as e:
        log.debug("skip config_reload: %s", e)
        record_failure("infrastructure", "config_reload", str(e))
    try:
        from loom.tools.deployment import research_deploy_status, research_deploy_history, research_deploy_record
        mcp.tool()(wrap_tool(research_deploy_status))
        record_success("infrastructure", "research_deploy_status")
        mcp.tool()(wrap_tool(research_deploy_history))
        record_success("infrastructure", "research_deploy_history")
        mcp.tool()(wrap_tool(research_deploy_record))
        record_success("infrastructure", "research_deploy_record")
    except (ImportError, AttributeError) as e:
        log.debug("skip deployment: %s", e)
        record_failure("infrastructure", "deployment", str(e))
    try:
        from loom.tools.email_report import research_email_report
        mcp.tool()(wrap_tool(research_email_report))
        record_success("infrastructure", "research_email_report")
    except (ImportError, AttributeError) as e:
        log.debug("skip email_mod: %s", e)
        record_failure("infrastructure", "email_report", str(e))
    try:
        from loom.tools.error_wrapper import research_error_stats, research_error_clear
        mcp.tool()(wrap_tool(research_error_stats))
        record_success("infrastructure", "research_error_stats")
        mcp.tool()(wrap_tool(research_error_clear))
        record_success("infrastructure", "research_error_clear")
    except (ImportError, AttributeError) as e:
        log.debug("skip error_wrapper: %s", e)
        record_failure("infrastructure", "error_wrapper", str(e))
    try:
        from loom.tools.gcp import research_image_analyze, research_text_to_speech, research_tts_voices
        mcp.tool()(wrap_tool(research_image_analyze))
        record_success("infrastructure", "research_image_analyze")
        mcp.tool()(wrap_tool(research_text_to_speech))
        record_success("infrastructure", "research_text_to_speech")
        mcp.tool()(wrap_tool(research_tts_voices))
        record_success("infrastructure", "research_tts_voices")
    except (ImportError, AttributeError) as e:
        log.debug("skip gcp_mod: %s", e)
        record_failure("infrastructure", "gcp", str(e))
    try:
        from loom.tools.joplin import research_save_note, research_list_notebooks
        mcp.tool()(wrap_tool(research_save_note))
        record_success("infrastructure", "research_save_note")
        mcp.tool()(wrap_tool(research_list_notebooks))
        record_success("infrastructure", "research_list_notebooks")
    except (ImportError, AttributeError) as e:
        log.debug("skip joplin_mod: %s", e)
        record_failure("infrastructure", "joplin", str(e))
    try:
        from loom.tools.key_rotation import research_key_status, research_key_rotate, research_key_test
        mcp.tool()(wrap_tool(research_key_status))
        record_success("infrastructure", "research_key_status")
        mcp.tool()(wrap_tool(research_key_rotate))
        record_success("infrastructure", "research_key_rotate")
        mcp.tool()(wrap_tool(research_key_test))
        record_success("infrastructure", "research_key_test")
    except (ImportError, AttributeError) as e:
        log.debug("skip key_rotation: %s", e)
        record_failure("infrastructure", "key_rotation", str(e))
    try:
        from loom.tools.memory_mgmt import research_memory_status, research_memory_gc, research_memory_profile
        mcp.tool()(wrap_tool(research_memory_status))
        record_success("infrastructure", "research_memory_status")
        mcp.tool()(wrap_tool(research_memory_gc))
        record_success("infrastructure", "research_memory_gc")
        mcp.tool()(wrap_tool(research_memory_profile))
        record_success("infrastructure", "research_memory_profile")
    except (ImportError, AttributeError) as e:
        log.debug("skip memory_mgmt: %s", e)
        record_failure("infrastructure", "memory_mgmt", str(e))
    try:
        from loom.tools.metrics import research_metrics
        mcp.tool()(wrap_tool(research_metrics))
        record_success("infrastructure", "research_metrics")
    except (ImportError, AttributeError) as e:
        log.debug("skip metrics_mod: %s", e)
        record_failure("infrastructure", "metrics", str(e))
    try:
        from loom.tools.observability import research_trace_start, research_trace_end, research_traces_list
        mcp.tool()(wrap_tool(research_trace_start))
        record_success("infrastructure", "research_trace_start")
        mcp.tool()(wrap_tool(research_trace_end))
        record_success("infrastructure", "research_trace_end")
        mcp.tool()(wrap_tool(research_traces_list))
        record_success("infrastructure", "research_traces_list")
    except (ImportError, AttributeError) as e:
        log.debug("skip observability: %s", e)
        record_failure("infrastructure", "observability", str(e))
    try:
        from loom.tools.session_replay import research_session_record, research_session_replay, research_session_list
        mcp.tool()(wrap_tool(research_session_record))
        record_success("infrastructure", "research_session_record")
        mcp.tool()(wrap_tool(research_session_replay))
        record_success("infrastructure", "research_session_replay")
        mcp.tool()(wrap_tool(research_session_list))
        record_success("infrastructure", "research_session_list")
    except (ImportError, AttributeError) as e:
        log.debug("skip session_replay: %s", e)
        record_failure("infrastructure", "session_replay", str(e))
    try:
        from loom.tools.slack import research_slack_notify
        mcp.tool()(wrap_tool(research_slack_notify))
        record_success("infrastructure", "research_slack_notify")
    except (ImportError, AttributeError) as e:
        log.debug("skip slack_mod: %s", e)
        record_failure("infrastructure", "slack", str(e))
    try:
        from loom.tools.telemetry import research_telemetry_record, research_telemetry_stats, research_telemetry_reset
        mcp.tool()(wrap_tool(research_telemetry_record))
        record_success("infrastructure", "research_telemetry_record")
        mcp.tool()(wrap_tool(research_telemetry_stats))
        record_success("infrastructure", "research_telemetry_stats")
        mcp.tool()(wrap_tool(research_telemetry_reset))
        record_success("infrastructure", "research_telemetry_reset")
    except (ImportError, AttributeError) as e:
        log.debug("skip telemetry: %s", e)
        record_failure("infrastructure", "telemetry", str(e))
    try:
        from loom.tools.vastai import research_vastai_search, research_vastai_status
        mcp.tool()(wrap_tool(research_vastai_search))
        record_success("infrastructure", "research_vastai_search")
        mcp.tool()(wrap_tool(research_vastai_status))
        record_success("infrastructure", "research_vastai_status")
    except (ImportError, AttributeError) as e:
        log.debug("skip vastai_mod: %s", e)
        record_failure("infrastructure", "vastai", str(e))
    try:
        from loom.tools.vercel import research_vercel_status
        mcp.tool()(wrap_tool(research_vercel_status))
        record_success("infrastructure", "research_vercel_status")
    except (ImportError, AttributeError) as e:
        log.debug("skip vercel_mod: %s", e)
        record_failure("infrastructure", "vercel", str(e))
    log.info("registered infrastructure tools count=41")
