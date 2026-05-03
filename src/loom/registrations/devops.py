"""DevOps, workflow, and orchestration tools — composition, execution planning, automation.

Tools for workflow management, tool recommendation, experiment execution, and
intelligent orchestration.
"""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.devops")


def register_devops_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 70 DevOps and orchestration tools.

    Includes workflow engines, composition optimizers, tool recommenders,
    execution planning, and intelligent routing.
    """
    from loom.tools import (
        workflow_engine,
        workflow_templates,
        workflow_expander,
        execution_planner,
        smart_router,
        composition_optimizer,
        capability_matrix,
        semantic_index,
        universal_orchestrator,
        auto_params,
        tool_recommender_v2,
        param_sweep,
        realtime_monitor,
        research_scheduler,
        auto_pipeline,
        auto_experiment,
        progress_tracker,
        strategy_evolution,
        strategy_cache,
        strategy_ab_test,
        strategy_feedback,
        lifetime_oracle,
        model_profiler,
        auto_docs,
        tool_catalog,
        tool_tags,
        tool_versioning,
        tool_profiler,
        change_monitor,
        resilience_predictor,
        predictive_ranker,
        response_synthesizer,
        result_aggregator,
        resumption,
        nl_executor,
        parallel_executor,
        chain_composer,
        do_expert,
        expert_engine,
    )

    # Workflow management
    mcp.tool()(wrap_tool(workflow_engine.research_workflow_create))
    mcp.tool()(wrap_tool(workflow_engine.research_workflow_run))
    mcp.tool()(wrap_tool(workflow_engine.research_workflow_status))

    # Workflow templates and generation
    mcp.tool()(wrap_tool(workflow_templates.research_workflow_list))
    mcp.tool()(wrap_tool(workflow_templates.research_workflow_get))
    mcp.tool()(wrap_tool(workflow_expander.research_workflow_generate))
    mcp.tool()(wrap_tool(workflow_expander.research_workflow_coverage))

    # Execution planning
    mcp.tool()(wrap_tool(execution_planner.research_plan_execution))
    mcp.tool()(wrap_tool(execution_planner.research_executable_check))
    mcp.tool()(wrap_tool(execution_planner.research_plan_refine))

    # Smart routing and composition
    mcp.tool()(wrap_tool(smart_router.research_route_query))
    mcp.tool()(wrap_tool(smart_router.research_route_batch))
    mcp.tool()(wrap_tool(smart_router.research_router_rebuild))
    mcp.tool()(wrap_tool(composition_optimizer.research_optimize_workflow))
    mcp.tool()(wrap_tool(composition_optimizer.research_parallel_plan))
    mcp.tool()(wrap_tool(composition_optimizer.research_optimizer_rebuild))
    mcp.tool()(wrap_tool(universal_orchestrator.research_orchestrate_smart))

    # Capability and tool analysis
    mcp.tool()(wrap_tool(capability_matrix.research_capability_matrix))
    mcp.tool()(wrap_tool(capability_matrix.research_find_tools_by_capability))
    mcp.tool()(wrap_tool(semantic_index.research_semantic_index))
    mcp.tool()(wrap_tool(semantic_index.research_similarity_search))

    # Parameter and tool management
    mcp.tool()(wrap_tool(auto_params.research_auto_params))
    mcp.tool()(wrap_tool(auto_params.research_inspect_tool))
    mcp.tool()(wrap_tool(tool_recommender_v2.research_tool_recommend))
    mcp.tool()(wrap_tool(tool_recommender_v2.research_tool_rank))
    mcp.tool()(wrap_tool(param_sweep.research_param_sweep))

    # Monitoring and tracking
    mcp.tool()(wrap_tool(realtime_monitor.research_monitor_status))
    mcp.tool()(wrap_tool(realtime_monitor.research_monitor_alerts))
    mcp.tool()(wrap_tool(research_scheduler.research_schedule_task))
    mcp.tool()(wrap_tool(research_scheduler.research_scheduled_list))

    # Automation and pipelines
    mcp.tool()(wrap_tool(auto_pipeline.research_auto_pipeline))
    mcp.tool()(wrap_tool(auto_experiment.research_experiment_design))
    mcp.tool()(wrap_tool(auto_experiment.research_run_experiment))
    mcp.tool()(wrap_tool(progress_tracker.research_track_progress))

    # Strategy management
    mcp.tool()(wrap_tool(strategy_evolution.research_evolve_strategy))
    mcp.tool()(wrap_tool(strategy_evolution.research_strategy_compare))
    mcp.tool()(wrap_tool(strategy_cache.research_cache_strategy))
    mcp.tool()(wrap_tool(strategy_ab_test.research_ab_test_design))
    mcp.tool()(wrap_tool(strategy_ab_test.research_ab_test_analyze))
    mcp.tool()(wrap_tool(strategy_feedback.research_collect_feedback))
    mcp.tool()(wrap_tool(strategy_feedback.research_apply_feedback))

    # Performance and prediction
    mcp.tool()(wrap_tool(lifetime_oracle.research_predict_lifetime))
    mcp.tool()(wrap_tool(lifetime_oracle.research_estimate_value))
    mcp.tool()(wrap_tool(model_profiler.research_model_profile))
    mcp.tool()(wrap_tool(model_profiler.research_profile_benchmark))
    mcp.tool()(wrap_tool(resilience_predictor.research_predict_resilience))
    mcp.tool()(wrap_tool(predictive_ranker.research_rank_items))

    # Tool and documentation management
    mcp.tool()(wrap_tool(auto_docs.research_generate_docs))
    mcp.tool()(wrap_tool(auto_docs.research_docs_coverage))
    mcp.tool()(wrap_tool(tool_catalog.research_tool_catalog))
    mcp.tool()(wrap_tool(tool_tags.research_tag_tool))
    mcp.tool()(wrap_tool(tool_versioning.research_version_check))
    mcp.tool()(wrap_tool(tool_profiler.research_profile_tool))
    mcp.tool()(wrap_tool(tool_profiler.research_profile_hotspots))

    # Change and trend tracking
    mcp.tool()(wrap_tool(change_monitor.research_change_monitor, "fetch"))

    # Response synthesis and aggregation
    mcp.tool()(wrap_tool(response_synthesizer.research_synthesize_responses))
    mcp.tool()(wrap_tool(result_aggregator.research_aggregate_results))
    mcp.tool()(wrap_tool(resumption.research_resume_session))
    mcp.tool()(wrap_tool(resumption.research_checkpoint_save))

    # Execution tools
    mcp.tool()(wrap_tool(nl_executor.research_execute_nl))
    mcp.tool()(wrap_tool(parallel_executor.research_execute_parallel))
    mcp.tool()(wrap_tool(chain_composer.research_chain_define))
    mcp.tool()(wrap_tool(chain_composer.research_chain_list))
    mcp.tool()(wrap_tool(chain_composer.research_chain_describe))

    # Expert and smart routing
    mcp.tool()(wrap_tool(do_expert.research_do_expert, "orchestration"))
    mcp.tool()(wrap_tool(expert_engine.research_expert))

    # Optional DevOps tools
    with suppress(ImportError):
        mcp.tool()(_optional_tools["cicd"])
        mcp.tool()(_optional_tools["mcp_security"])

    log.info("registered devops tools count=70")
