"""FastMCP server entrypoint for Loom MCP service.

Exports the FastMCP instance with all research tools registered
via dynamic tool discovery from the loom.tools namespace.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import os
import signal
import time
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from mcp.server import FastMCP
from mcp.server.auth.settings import AuthSettings

from loom.config import load_config, research_config_get, research_config_set
from loom.orchestrator import research_orchestrate
from loom.audit import export_audit
from loom.logging_config import setup_logging
from loom.rate_limiter import rate_limited
from loom.sessions import (
    cleanup_all_sessions,
    research_session_close,
    research_session_list,
    research_session_open,
)
from loom.scoring import research_score_all
from loom.unified_scorer import research_unified_score

from loom.benchmarks import research_benchmark_run
from loom.consensus_builder import (
    research_consensus_build,
    research_consensus_pressure,
)
from loom.crescendo_loop import research_crescendo_loop
from loom.model_profiler import research_model_profile
from loom.reid_pipeline import research_reid_pipeline
from loom.full_spectrum import FullSpectrumPipeline
from loom import crawlee_backend
from loom import zendriver_backend


# Import tool modules to register their functions
from loom.tools import (
    academic_integrity,
    access_tools,
    adversarial_debate_tool,
    agent_benchmark,
    benchmark_datasets,
    ai_safety,
    ai_safety_extended,
    antiforensics,
    autonomous_agent,
    bias_lens,
    breach_check,
    compliance_report,
    cache_mgmt,
    cert_analyzer,
    change_monitor,
    company_intel,
    competitive_intel,
    cross_domain,
    crypto_risk,
    crypto_trace,
    culture_dna,
    cyberscraper,
    dark_forum,
    dark_recon,
    darkweb_early_warning,
    dead_content,
    deception_detect,
    deception_job_scanner,
    evasion_network,
    deep,
    deep_research_agent,
    domain_intel,
    exploit_db,
    ethereum_tools,
    fact_checker,
    fetch,
    full_pipeline,
    gap_tools_academic,
    gap_tools_advanced,
    gap_tools_ai,
    gap_tools_infra,
    github,
    graph_analysis,
    graph_scraper,
    hcs10_academic,
    hcs_escalation,
    hcs_report,
    hcs_rubric_tool,
    hcs_scorer,
    identity_resolve,
    infowar_tools,
    infra_analysis,
    infra_correlator,
    invisible_web,
    job_signals,
    js_intel,
    knowledge_graph,
    leak_scan,
    lightpanda_backend,
    markdown,
    metadata_forensics,
    multi_search,
    neo4j_backend,
    observability,
    onion_discover,
    osint_extended,
    output_formatter,
    p3_tools,
    persistent_memory,
    passive_recon,
    pdf_extract,
    projectdiscovery,
    prompt_analyzer,
    prompt_reframe,
    psycholinguistic,
    rag_anything,
    realtime_adapt,
    realtime_monitor,
    report_generator,
    response_synthesizer,
    rss_monitor,
    salary_synthesizer,
    scraper_engine_tools,
    search,
    security_headers,
    sherlock_backend,
    simplifier,
    signal_detection,
    social_graph,
    social_intel,
    social_scraper,
    spider,
    stagehand_backend,
    stealth,
    stego_detect,
    stego_encoder,
    strategy_cache,
    strategy_feedback,
    stylometry,
    supply_chain_intel,
    synth_echo,
    threat_intel,
    threat_profile,
    transferability,
    tool_catalog,
    trend_predictor,
    unique_tools,
    vision_agent,
    workflow_engine,
)
from loom.tracing import install_tracing, new_request_id

log = logging.getLogger("loom.server")

# Dynamically import optional tool modules (LLM tools, etc.)
_optional_tools: dict[str, Any] = {}
with suppress(ImportError):
    from loom.tools import llm as llm_tools

    _optional_tools["llm"] = llm_tools

with suppress(ImportError):
    from loom.tools import enrich as enrich_tools

    _optional_tools["enrich"] = enrich_tools

with suppress(ImportError):
    from loom.tools import experts as experts_tools

    _optional_tools["experts"] = experts_tools

with suppress(ImportError):
    from loom.tools import creative as creative_tools

    _optional_tools["creative"] = creative_tools

with suppress(ImportError):
    from loom.providers import youtube_transcripts as yt_tools

    _optional_tools["youtube"] = yt_tools

with suppress(ImportError):
    from loom.tools import vastai as vastai_tools

    _optional_tools["vastai"] = vastai_tools

with suppress(ImportError):
    from loom.tools import billing as billing_tools

    _optional_tools["billing"] = billing_tools

with suppress(ImportError):
    from loom.tools import email_report as email_tools

    _optional_tools["email"] = email_tools

with suppress(ImportError):
    from loom.tools import joplin as joplin_tools

    _optional_tools["joplin"] = joplin_tools
with suppress(ImportError):
    from loom.tools import evasion_network as evasion_network_tools

    _optional_tools["evasion_network"] = evasion_network_tools


with suppress(ImportError):
    from loom.tools import tor as tor_tools

    _optional_tools["tor"] = tor_tools

with suppress(ImportError):
    from loom.tools import transcribe as transcribe_tools

    _optional_tools["transcribe"] = transcribe_tools

with suppress(ImportError):
    from loom.tools import document as document_tools

    _optional_tools["document"] = document_tools


with suppress(ImportError):
    from loom.tools import metrics as metrics_tools

    _optional_tools["metrics"] = metrics_tools

with suppress(ImportError):
    from loom.tools import slack as slack_tools

    _optional_tools["slack"] = slack_tools

with suppress(ImportError):
    from loom.tools import gcp as gcp_tools

    _optional_tools["gcp"] = gcp_tools

with suppress(ImportError):
    from loom.tools import vercel as vercel_tools

    _optional_tools["vercel"] = vercel_tools

# ── v3 modules: scorers, pipelines, orchestration, tracking ──
with suppress(ImportError):
    from loom.tools import attack_scorer as attack_scorer_tools
    _optional_tools["attack_scorer"] = attack_scorer_tools

with suppress(ImportError):
    from loom.tools import stealth_score as stealth_score_tools
    _optional_tools["stealth_score"] = stealth_score_tools

with suppress(ImportError):
    from loom.tools import model_sentiment as model_sentiment_tools
    _optional_tools["model_sentiment"] = model_sentiment_tools

with suppress(ImportError):
    from loom.tools import toxicity_checker_tool as toxicity_tools
    _optional_tools["toxicity"] = toxicity_tools

with suppress(ImportError):
    from loom.tools import drift_monitor_tool as drift_tools
    _optional_tools["drift"] = drift_tools

with suppress(ImportError):
    from loom.tools import bpj as bpj_tools
    _optional_tools["bpj"] = bpj_tools

with suppress(ImportError):
    from loom.tools import daisy_chain_tool as daisy_tools
    _optional_tools["daisy_chain"] = daisy_tools

with suppress(ImportError):
    from loom.tools import consistency_pressure as consistency_tools
    _optional_tools["consistency"] = consistency_tools

with suppress(ImportError):
    from loom.tools import constraint_optimizer as constraint_tools
    _optional_tools["constraint"] = constraint_tools

with suppress(ImportError):
    from loom.tools import jailbreak_evolution as jailbreak_evo_tools
    _optional_tools["jailbreak_evo"] = jailbreak_evo_tools

with suppress(ImportError):
    from loom.tools import semantic_cache_mgmt as sem_cache_tools
    _optional_tools["sem_cache"] = sem_cache_tools

with suppress(ImportError):
    from loom.tools import param_sweep as param_sweep_tools
    _optional_tools["param_sweep"] = param_sweep_tools

with suppress(ImportError):
    from loom.tools import strategy_oracle as strategy_oracle_tools
    _optional_tools["strategy_oracle"] = strategy_oracle_tools

with suppress(ImportError):
    from loom.tools import stealth_detect as stealth_detect_tools
    _optional_tools["stealth_detect"] = stealth_detect_tools

with suppress(ImportError):
    from loom.tools import tool_recommender_tool as recommender_tools
    _optional_tools["recommender"] = recommender_tools

with suppress(ImportError):
    from loom.tools import ytdlp_backend as ytdlp_tools
    _optional_tools["ytdlp"] = ytdlp_tools

# ── v3 direct imports (functions in src/loom/*.py) ──
with suppress(ImportError):
    from loom.danger_prescore import research_danger_prescore
    _optional_tools["danger_prescore"] = research_danger_prescore

with suppress(ImportError):
    from loom.quality_scorer import research_quality_score
    _optional_tools["quality_scorer"] = research_quality_score

with suppress(ImportError):
    from loom.evidence_pipeline import research_evidence_pipeline
    _optional_tools["evidence_pipeline"] = research_evidence_pipeline

with suppress(ImportError):
    from loom.context_poisoning import research_context_poison
    _optional_tools["context_poison"] = research_context_poison

with suppress(ImportError):
    from loom.adversarial_debate import research_adversarial_debate
    _optional_tools["adversarial_debate"] = research_adversarial_debate

with suppress(ImportError):
    from loom.model_evidence import research_model_evidence
    _optional_tools["model_evidence"] = research_model_evidence

with suppress(ImportError):
    from loom.target_orchestrator import research_target_orchestrate
    _optional_tools["target_orchestrate"] = research_target_orchestrate

with suppress(ImportError):
    from loom.reid_auto import ReidAutoReframe
    _optional_tools["reid_auto"] = ReidAutoReframe

with suppress(ImportError):
    from loom.mcp_security import research_mcp_security_scan
    _optional_tools["mcp_security"] = research_mcp_security_scan

with suppress(ImportError):
    from loom.cicd import research_cicd_run
    _optional_tools["cicd"] = research_cicd_run

with suppress(ImportError):
    from loom.stealth_detector import research_stealth_detect as stealth_det_fn
    _optional_tools["stealth_detector"] = stealth_det_fn

with suppress(ImportError):
    from loom.doc_parser import research_ocr_advanced, research_pdf_advanced, research_document_analyze
    _optional_tools["doc_parser"] = {"ocr": research_ocr_advanced, "pdf": research_pdf_advanced, "analyze": research_document_analyze}

with suppress(ImportError):
    from loom.tools import cipher_mirror as cipher_mirror_tools

    _optional_tools["cipher_mirror"] = cipher_mirror_tools

with suppress(ImportError):
    from loom.tools import forum_cortex as forum_cortex_tools

    _optional_tools["forum_cortex"] = forum_cortex_tools

with suppress(ImportError):
    from loom.tools import onion_spectra as onion_spectra_tools

    _optional_tools["onion_spectra"] = onion_spectra_tools

with suppress(ImportError):
    from loom.tools import ghost_weave as ghost_weave_tools

    _optional_tools["ghost_weave"] = ghost_weave_tools

with suppress(ImportError):
    from loom.tools import dead_drop_scanner as dead_drop_scanner_tools

    _optional_tools["dead_drop_scanner"] = dead_drop_scanner_tools

with suppress(ImportError):
    from loom.tools import persona_profile as persona_profile_tools

    _optional_tools["persona_profile"] = persona_profile_tools

with suppress(ImportError):
    from loom.tools import radicalization_detect as radicalization_detect_tools

    _optional_tools["radicalization_detect"] = radicalization_detect_tools
with suppress(ImportError):
    from loom.tools import sentiment_deep as sentiment_deep_tools

    _optional_tools["sentiment_deep"] = sentiment_deep_tools

with suppress(ImportError):
    from loom.tools import network_persona as network_persona_tools

    _optional_tools["network_persona"] = network_persona_tools

with suppress(ImportError):
    from loom.tools import text_analyze as text_analyze_tools

    _optional_tools["text_analyze"] = text_analyze_tools

with suppress(ImportError):
    from loom.tools import screenshot as screenshot_tools

    _optional_tools["screenshot"] = screenshot_tools


with suppress(ImportError):
    from loom.tools import geoip_local as geoip_local_tools

    _optional_tools["geoip_local"] = geoip_local_tools

with suppress(ImportError):
    from loom.tools import image_intel as image_intel_tools

    _optional_tools["image_intel"] = image_intel_tools

with suppress(ImportError):
    from loom.tools import ip_intel as ip_intel_tools

    _optional_tools["ip_intel"] = ip_intel_tools

with suppress(ImportError):
    from loom.tools import cve_lookup as cve_lookup_tools

    _optional_tools["cve_lookup"] = cve_lookup_tools

with suppress(ImportError):
    from loom.tools import vuln_intel as vuln_intel_tools

    _optional_tools["vuln_intel"] = vuln_intel_tools

with suppress(ImportError):
    from loom.tools import urlhaus_lookup as urlhaus_lookup_tools

    _optional_tools["urlhaus_lookup"] = urlhaus_lookup_tools

with suppress(ImportError):
    from loom.tools import job_research as job_research_tools

    _optional_tools["job_research"] = job_research_tools


with suppress(ImportError):
    from loom.tools import career_intel as career_intel_tools

    _optional_tools["career_intel"] = career_intel_tools

with suppress(ImportError):
    from loom.tools import resume_intel as resume_intel_tools

    _optional_tools["resume_intel"] = resume_intel_tools


with suppress(ImportError):
    from loom.tools import career_trajectory as career_trajectory_tools

    _optional_tools["career_trajectory"] = career_trajectory_tools

with suppress(ImportError):
    from loom.tools import consistency_pressure as consistency_pressure_tools

    _optional_tools["consistency_pressure"] = consistency_pressure_tools

with suppress(ImportError):
    from loom.tools import constraint_optimizer as constraint_optimizer_tools

    _optional_tools["constraint_optimizer"] = constraint_optimizer_tools

with suppress(ImportError):
    from loom.tools import semantic_cache_mgmt as semantic_cache_mgmt_tools

    _optional_tools["semantic_cache_mgmt"] = semantic_cache_mgmt_tools

with suppress(ImportError):
    from loom.tools import param_sweep as param_sweep_tools

    _optional_tools["param_sweep"] = param_sweep_tools

with suppress(ImportError):
    from loom import nodriver_backend

    _optional_tools["nodriver"] = nodriver_backend

with suppress(ImportError):
    from loom.tools import ytdlp_backend as ytdlp_backend_tools

    _optional_tools["ytdlp_backend"] = ytdlp_backend_tools


with suppress(ImportError):
    from loom.tools import model_consensus as model_consensus_tools

    _optional_tools["model_consensus"] = model_consensus_tools


with suppress(ImportError):
    from loom import doc_parser as doc_parser_tools

    _optional_tools["doc_parser"] = doc_parser_tools
_start_time = time.time()
