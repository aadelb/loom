"""Registration module for devops tools."""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.devops")


def register_devops_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 26 devops tools."""
    from loom.registrations.tracking import record_success, record_failure

    try:
        from loom.tools.auto_params import research_auto_params, research_inspect_tool
        mcp.tool()(wrap_tool(research_auto_params))
        record_success("devops", "research_auto_params")
        mcp.tool()(wrap_tool(research_inspect_tool))
        record_success("devops", "research_inspect_tool")
    except (ImportError, AttributeError) as e:
        log.debug("skip auto_params: %s", e)
        record_failure("devops", "auto_params", str(e))
    try:
        from loom.tools.capability_matrix import research_capability_matrix, research_find_tools_by_capability
        mcp.tool()(wrap_tool(research_capability_matrix))
        record_success("devops", "research_capability_matrix")
        mcp.tool()(wrap_tool(research_find_tools_by_capability))
        record_success("devops", "research_find_tools_by_capability")
    except (ImportError, AttributeError) as e:
        log.debug("skip capability_matrix: %s", e)
        record_failure("devops", "capability_matrix", str(e))
    try:
        from loom.tools.composition_optimizer import research_optimize_workflow, research_parallel_plan, research_optimizer_rebuild
        mcp.tool()(wrap_tool(research_optimize_workflow))
        record_success("devops", "research_optimize_workflow")
        mcp.tool()(wrap_tool(research_parallel_plan))
        record_success("devops", "research_parallel_plan")
        mcp.tool()(wrap_tool(research_optimizer_rebuild))
        record_success("devops", "research_optimizer_rebuild")
    except (ImportError, AttributeError) as e:
        log.debug("skip composition_optimizer: %s", e)
        record_failure("devops", "composition_optimizer", str(e))
    try:
        from loom.tools.do_expert import research_do_expert
        mcp.tool()(wrap_tool(research_do_expert))
        record_success("devops", "research_do_expert")
    except (ImportError, AttributeError) as e:
        log.debug("skip do_expert: %s", e)
        record_failure("devops", "do_expert", str(e))
    try:
        from loom.tools.execution_planner import research_plan_execution, research_plan_validate
        mcp.tool()(wrap_tool(research_plan_execution))
        record_success("devops", "research_plan_execution")
        mcp.tool()(wrap_tool(research_plan_validate))
        record_success("devops", "research_plan_validate")
    except (ImportError, AttributeError) as e:
        log.debug("skip execution_planner: %s", e)
        record_failure("devops", "execution_planner", str(e))
    try:
        from loom.tools.expert_engine import research_expert
        mcp.tool()(wrap_tool(research_expert))
        record_success("devops", "research_expert")
    except (ImportError, AttributeError) as e:
        log.debug("skip expert_engine: %s", e)
        record_failure("devops", "expert_engine", str(e))
    try:
        from loom.tools.full_pipeline import research_full_pipeline
        mcp.tool()(wrap_tool(research_full_pipeline))
        record_success("devops", "research_full_pipeline")
    except (ImportError, AttributeError) as e:
        log.debug("skip full_pipeline: %s", e)
        record_failure("devops", "full_pipeline", str(e))
    try:
        from loom.tools.semantic_index import research_semantic_search, research_semantic_rebuild
        mcp.tool()(wrap_tool(research_semantic_search))
        record_success("devops", "research_semantic_search")
        mcp.tool()(wrap_tool(research_semantic_rebuild))
        record_success("devops", "research_semantic_rebuild")
    except (ImportError, AttributeError) as e:
        log.debug("skip semantic_index: %s", e)
        record_failure("devops", "semantic_index", str(e))
    try:
        from loom.tools.smart_router import research_route_query, research_route_batch, research_router_rebuild
        mcp.tool()(wrap_tool(research_route_query))
        record_success("devops", "research_route_query")
        mcp.tool()(wrap_tool(research_route_batch))
        record_success("devops", "research_route_batch")
        mcp.tool()(wrap_tool(research_router_rebuild))
        record_success("devops", "research_router_rebuild")
    except (ImportError, AttributeError) as e:
        log.debug("skip smart_router: %s", e)
        record_failure("devops", "smart_router", str(e))
    try:
        from loom.tools.tool_recommender_v2 import research_recommend_next, research_suggest_workflow
        mcp.tool()(wrap_tool(research_recommend_next))
        record_success("devops", "research_recommend_next")
        mcp.tool()(wrap_tool(research_suggest_workflow))
        record_success("devops", "research_suggest_workflow")
    except (ImportError, AttributeError) as e:
        log.debug("skip tool_recommender_v2: %s", e)
        record_failure("devops", "tool_recommender_v2", str(e))
    try:
        from loom.tools.workflow_engine import research_workflow_create, research_workflow_run, research_workflow_status
        mcp.tool()(wrap_tool(research_workflow_create))
        record_success("devops", "research_workflow_create")
        mcp.tool()(wrap_tool(research_workflow_run))
        record_success("devops", "research_workflow_run")
        mcp.tool()(wrap_tool(research_workflow_status))
        record_success("devops", "research_workflow_status")
    except (ImportError, AttributeError) as e:
        log.debug("skip workflow_engine: %s", e)
        record_failure("devops", "workflow_engine", str(e))
    try:
        from loom.tools.workflow_expander import research_workflow_generate, research_workflow_coverage
        mcp.tool()(wrap_tool(research_workflow_generate))
        record_success("devops", "research_workflow_generate")
        mcp.tool()(wrap_tool(research_workflow_coverage))
        record_success("devops", "research_workflow_coverage")
    except (ImportError, AttributeError) as e:
        log.debug("skip workflow_expander: %s", e)
        record_failure("devops", "workflow_expander", str(e))
    try:
        from loom.tools.workflow_templates import research_workflow_list, research_workflow_get
        mcp.tool()(wrap_tool(research_workflow_list))
        record_success("devops", "research_workflow_list")
        mcp.tool()(wrap_tool(research_workflow_get))
        record_success("devops", "research_workflow_get")
    except (ImportError, AttributeError) as e:
        log.debug("skip workflow_templates: %s", e)
        record_failure("devops", "workflow_templates", str(e))
    log.info("registered devops tools count=26")
