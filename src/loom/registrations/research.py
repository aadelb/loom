"""Registration module for research tools."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.research")


def register_research_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 369 research tools."""
    from loom.registrations.tracking import record_success, record_failure

    try:
        from loom.tools.research.academic_integrity import research_citation_analysis, research_retraction_check, research_predatory_journal_check
        mcp.tool()(wrap_tool(research_citation_analysis))
        record_success("research", "research_citation_analysis")
        mcp.tool()(wrap_tool(research_retraction_check))
        record_success("research", "research_retraction_check")
        mcp.tool()(wrap_tool(research_predatory_journal_check))
        record_success("research", "research_predatory_journal_check")
    except (ImportError, AttributeError) as e:
        log.debug("skip academic_integrity: %s", e)
        record_failure("research", "academic_integrity", str(e))
    try:
        from loom.tools.infrastructure.access_tools import research_legal_takedown, research_open_access, research_content_authenticity, research_credential_monitor, research_deepfake_checker
        mcp.tool()(wrap_tool(research_legal_takedown))
        record_success("research", "research_legal_takedown")
        mcp.tool()(wrap_tool(research_open_access))
        record_success("research", "research_open_access")
        mcp.tool()(wrap_tool(research_content_authenticity))
        record_success("research", "research_content_authenticity")
        mcp.tool()(wrap_tool(research_credential_monitor))
        record_success("research", "research_credential_monitor")
        mcp.tool()(wrap_tool(research_deepfake_checker))
        record_success("research", "research_deepfake_checker")
    except (ImportError, AttributeError) as e:
        log.debug("skip access_tools: %s", e)
        record_failure("research", "access_tools", str(e))
    try:
        from loom.tools.research.agent_benchmark import research_agent_benchmark
        mcp.tool()(wrap_tool(research_agent_benchmark))
        record_success("research", "research_agent_benchmark")
    except (ImportError, AttributeError) as e:
        log.debug("skip agent_benchmark: %s", e)
        record_failure("research", "agent_benchmark", str(e))
    # ── Composer & Pipeline Tools ──
    try:
        from loom.tools.llm.composer import research_compose, research_compose_validate, research_merge
        mcp.tool()(wrap_tool(research_compose))
        record_success("research", "research_compose")
        mcp.tool()(wrap_tool(research_compose_validate))
        record_success("research", "research_compose_validate")
        mcp.tool()(wrap_tool(research_merge))
        record_success("research", "research_merge")
    except (ImportError, AttributeError) as e:
        log.debug("skip composer: %s", e)
        record_failure("research", "composer", str(e))
    try:
        from loom.tools.infrastructure.pipeline_enhancer import research_compose_pipeline, research_enhance, research_enhance_batch, research_enhance_with_dependencies
        mcp.tool()(wrap_tool(research_compose_pipeline))
        record_success("research", "research_compose_pipeline")
        mcp.tool()(wrap_tool(research_enhance))
        record_success("research", "research_enhance")
        mcp.tool()(wrap_tool(research_enhance_batch))
        record_success("research", "research_enhance_batch")
        mcp.tool()(wrap_tool(research_enhance_with_dependencies))
        record_success("research", "research_enhance_with_dependencies")
    except (ImportError, AttributeError) as e:
        log.debug("skip pipeline_enhancer: %s", e)
        record_failure("research", "pipeline_enhancer", str(e))

    # ── Prompt & Compression Tools ──
    try:
        from loom.tools.llm.prompt_compression import research_compress_prompt, research_compression_stats
        mcp.tool()(wrap_tool(research_compress_prompt))
        record_success("research", "research_compress_prompt")
        mcp.tool()(wrap_tool(research_compression_stats))
        record_success("research", "research_compression_stats")
    except (ImportError, AttributeError) as e:
        log.debug("skip prompt_compression: %s", e)
        record_failure("research", "prompt_compression", str(e))

    # ── Verification Tools ──
    try:
        from loom.tools.research.fact_verification import research_fact_verify, research_batch_verify
        mcp.tool()(wrap_tool(research_fact_verify))
        record_success("research", "research_fact_verify")
        mcp.tool()(wrap_tool(research_batch_verify))
        record_success("research", "research_batch_verify")
    except (ImportError, AttributeError) as e:
        log.debug("skip fact_verification: %s", e)
        record_failure("research", "fact_verification", str(e))

    # ── Stealth Detection Tools ──
    try:
        from loom.tools.adversarial.stealth_score import research_stealth_score, research_stealth_score_heuristic, research_stealth_detect_comparison
        mcp.tool()(wrap_tool(research_stealth_score))
        record_success("research", "research_stealth_score")
        mcp.tool()(wrap_tool(research_stealth_score_heuristic))
        record_success("research", "research_stealth_score_heuristic")
        mcp.tool()(wrap_tool(research_stealth_detect_comparison))
        record_success("research", "research_stealth_detect_comparison")
    except (ImportError, AttributeError) as e:
        log.debug("skip stealth_detector: %s", e)
        record_failure("research", "stealth_detector", str(e))

    # ── Scoring & Evaluation Tools ──
    try:
        from loom.tools.adversarial.attack_scorer import research_attack_score
        mcp.tool()(wrap_tool(research_attack_score))
        record_success("research", "research_attack_score")
    except (ImportError, AttributeError) as e:
        log.debug("skip attack_scorer: %s", e)
        record_failure("research", "attack_scorer", str(e))
    try:
        from loom.tools.adversarial.potency_meter import research_potency_score
        mcp.tool()(wrap_tool(research_potency_score))
        record_success("research", "research_potency_score")
    except (ImportError, AttributeError) as e:
        log.debug("skip potency_meter: %s", e)
        record_failure("research", "potency_meter", str(e))
    try:
        from loom.tools.research.toxicity_checker_tool import research_toxicity_check
        mcp.tool()(wrap_tool(research_toxicity_check))
        record_success("research", "research_toxicity_check")
    except (ImportError, AttributeError) as e:
        log.debug("skip toxicity_checker_tool: %s", e)
        record_failure("research", "toxicity_checker_tool", str(e))

    # ── Strategy & Orchestration Tools ──
    try:
        from loom.tools.llm.strategy_oracle import research_strategy_oracle
        mcp.tool()(wrap_tool(research_strategy_oracle))
        record_success("research", "research_strategy_oracle")
    except (ImportError, AttributeError) as e:
        log.debug("skip strategy_oracle: %s", e)
        record_failure("research", "strategy_oracle", str(e))
    try:
        from loom.tools.adversarial.daisy_chain_tool import research_daisy_chain
        mcp.tool()(wrap_tool(research_daisy_chain))
        record_success("research", "research_daisy_chain")
    except (ImportError, AttributeError) as e:
        log.debug("skip daisy_chain_tool: %s", e)
        record_failure("research", "daisy_chain_tool", str(e))
    try:
        from loom.tools.adversarial.consistency_pressure import research_consistency_pressure, research_consistency_pressure_history, research_consistency_pressure_record
        mcp.tool()(wrap_tool(research_consistency_pressure))
        record_success("research", "research_consistency_pressure")
        mcp.tool()(wrap_tool(research_consistency_pressure_history))
        record_success("research", "research_consistency_pressure_history")
        mcp.tool()(wrap_tool(research_consistency_pressure_record))
        record_success("research", "research_consistency_pressure_record")
    except (ImportError, AttributeError) as e:
        log.debug("skip consistency_pressure: %s", e)
        record_failure("research", "consistency_pressure", str(e))
    try:
        from loom.tools.llm.constraint_optimizer import research_constraint_optimize
        mcp.tool()(wrap_tool(research_constraint_optimize))
        record_success("research", "research_constraint_optimize")
    except (ImportError, AttributeError) as e:
        log.debug("skip constraint_optimizer: %s", e)
        record_failure("research", "constraint_optimizer", str(e))

    # ── Monitoring & Tracking Tools ──
    try:
        from loom.tools.monitoring.drift_monitor_tool import research_drift_monitor, research_drift_monitor_list
        mcp.tool()(wrap_tool(research_drift_monitor))
        record_success("research", "research_drift_monitor")
        mcp.tool()(wrap_tool(research_drift_monitor_list))
        record_success("research", "research_drift_monitor_list")
    except (ImportError, AttributeError) as e:
        log.debug("skip drift_monitor_tool: %s", e)
        record_failure("research", "drift_monitor_tool", str(e))
    try:
        from loom.tools.llm.model_consensus import research_multi_consensus
        mcp.tool()(wrap_tool(research_multi_consensus))
        record_success("research", "research_multi_consensus")
    except (ImportError, AttributeError) as e:
        log.debug("skip model_consensus: %s", e)
        record_failure("research", "model_consensus", str(e))

    # ── Data Export Tools ──
    try:
        from loom.tools.adversarial.bpj import research_bpj_generate
        mcp.tool()(wrap_tool(research_bpj_generate))
        record_success("research", "research_bpj_generate")
    except (ImportError, AttributeError) as e:
        log.debug("skip bpj: %s", e)
        record_failure("research", "bpj", str(e))

    # ── Sandbox Execution Tools ──
    try:
        from loom.tools.security.sandbox_executor import research_sandbox_execute, research_sandbox_monitor
        mcp.tool()(wrap_tool(research_sandbox_execute))
        record_success("research", "research_sandbox_execute")
        mcp.tool()(wrap_tool(research_sandbox_monitor))
        record_success("research", "research_sandbox_monitor")
    except (ImportError, AttributeError) as e:
        log.debug("skip sandbox_executor: %s", e)
        record_failure("research", "sandbox_executor", str(e))

    # ── Steganography Tools ──
    try:
        from loom.tools.privacy.stego_decoder import research_stego_decode
        mcp.tool()(wrap_tool(research_stego_decode))
        record_success("research", "research_stego_decode")
    except (ImportError, AttributeError) as e:
        log.debug("skip stego_decoder: %s", e)
        record_failure("research", "stego_decoder", str(e))

    # ── OCR Tools ──
    try:
        from loom.tools.intelligence.image_intel import research_ocr_extract
        mcp.tool()(wrap_tool(research_ocr_extract))
        record_success("research", "research_ocr_extract")
    except (ImportError, AttributeError) as e:
        log.debug("skip image_intel ocr: %s", e)
        record_failure("research", "image_intel", str(e))

    # ── Graph & Visualization Tools ──
    try:
        from loom.tools.core.graph_scraper import research_graph_scrape
        mcp.tool()(wrap_tool(research_graph_scrape))
        record_success("research", "research_graph_scrape")
    except (ImportError, AttributeError) as e:
        log.debug("skip graph_scraper: %s", e)
        record_failure("research", "graph_scraper", str(e))

    # ── Audit Tools ──
    try:
        from loom.tools.core.audit_query import research_audit_stats
        mcp.tool()(wrap_tool(research_audit_stats))
        record_success("research", "research_audit_stats")
    except (ImportError, AttributeError) as e:
        log.debug("skip audit_query: %s", e)
        record_failure("research", "audit_query", str(e))

    # ── Ethereum/DeFi Tools ──
    try:
        from loom.tools.infrastructure.ethereum_tools import research_ethereum_tx_decode, research_defi_security_audit
        mcp.tool()(wrap_tool(research_ethereum_tx_decode))
        record_success("research", "research_ethereum_tx_decode")
        mcp.tool()(wrap_tool(research_defi_security_audit))
        record_success("research", "research_defi_security_audit")
    except (ImportError, AttributeError) as e:
        log.debug("skip ethereum_tools: %s", e)
        record_failure("research", "ethereum_tools", str(e))

    # ── Routing & Recommendation Tools ──
    try:
        from loom.tools.llm.router import research_route_to_model, research_recommend_tools
        mcp.tool()(wrap_tool(research_route_to_model))
        record_success("research", "research_route_to_model")
        mcp.tool()(wrap_tool(research_recommend_tools))
        record_success("research", "research_recommend_tools")
    except (ImportError, AttributeError) as e:
        log.debug("skip router: %s", e)
        record_failure("research", "router", str(e))

    # ── Demo Tools ──
    try:
        from loom.tools.intelligence.threat_profile_demo import research_threat_profile_demo
        mcp.tool()(wrap_tool(research_threat_profile_demo))
        record_success("research", "research_threat_profile_demo")
    except (ImportError, AttributeError) as e:
        log.debug("skip threat_profile_demo: %s", e)
        record_failure("research", "threat_profile_demo", str(e))
    try:
        from loom.tools.intelligence.social_graph_demo import research_social_graph_demo
        mcp.tool()(wrap_tool(research_social_graph_demo))
        record_success("research", "research_social_graph_demo")
    except (ImportError, AttributeError) as e:
        log.debug("skip social_graph_demo: %s", e)
        record_failure("research", "social_graph_demo", str(e))

    # ── UAE Retail Intelligence ──
    try:
        from loom.tools.research.uae_retail_intel import (
            research_uae_price_compare,
            research_uae_wholesale_markets,
            research_uae_distributor_find,
            research_uae_price_search,
            research_uae_margin_calculator,
            research_uae_sourcing_plan,
        )
        for fn in [
            research_uae_price_compare,
            research_uae_wholesale_markets,
            research_uae_distributor_find,
            research_uae_price_search,
            research_uae_margin_calculator,
            research_uae_sourcing_plan,
        ]:
            mcp.tool()(wrap_tool(fn))
            record_success("research", fn.__name__)
    except (ImportError, AttributeError) as e:
        log.debug("skip uae_retail_intel: %s", e)
        record_failure("research", "uae_retail_intel", str(e))

    # ── UAE Retail Advanced Tools ──
    try:
        from loom.tools.research.uae_retail_advanced import (
            research_uae_competitor_scan,
            research_uae_high_margin_products,
            research_uae_delivery_setup,
            research_uae_seasonal_calendar,
            research_uae_legal_check,
            research_uae_bundle_optimizer,
        )
        for fn in [
            research_uae_competitor_scan,
            research_uae_high_margin_products,
            research_uae_delivery_setup,
            research_uae_seasonal_calendar,
            research_uae_legal_check,
            research_uae_bundle_optimizer,
        ]:
            mcp.tool()(wrap_tool(fn))
            record_success("research", fn.__name__)
    except (ImportError, AttributeError) as e:
        log.debug("skip uae_retail_advanced: %s", e)
        record_failure("research", "uae_retail_advanced", str(e))

    log.info("registered research tools count=442")
