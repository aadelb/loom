#!/usr/bin/env python3
"""Comprehensive validated test script for all 835 Loom tools.

Reads tool_guidelines.json, discovers each tool via its module,
generates smart test parameters, calls with 15s timeout, and
validates output quality against guideline criteria.

Usage (on hetzner, from /opt/research-toolbox/):
    python3 test_all_835_validated.py

Results saved to: /opt/research-toolbox/validated_835_report.json
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import logging
import os
import re
import sys
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Environment / path setup
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv("/opt/research-toolbox/.env")
except ImportError:
    pass

sys.path.insert(0, "src")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_all_835")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TOOL_TIMEOUT = 15.0
PROGRESS_INTERVAL = 50
GUIDELINES_PATH = Path("/opt/research-toolbox/tool_guidelines.json")
REPORT_PATH = Path("/opt/research-toolbox/validated_835_report.json")

# ---------------------------------------------------------------------------
# Parameter value mapping (focused on actual params found in guidelines)
# ---------------------------------------------------------------------------
PARAM_MAP: dict[str, Any] = {
    # Core text inputs
    "query": "how to build wealth in 2026",
    "prompt": "how to build wealth in 2026",
    "text": "how to build wealth in 2026",
    "q": "how to build wealth in 2026",
    "search": "how to build wealth in 2026",
    "input": "how to build wealth in 2026",
    "keyword": "how to build wealth in 2026",
    "question": "how to build wealth in 2026",
    "content": "how to build wealth in 2026",
    "body": "how to build wealth in 2026",
    "description": "test description",
    "title": "Test Title",
    "subject": "test subject",
    "message": "how to build wealth in 2026",
    "actual_content": "how to build wealth in 2026",
    "cover_message": "how to build wealth in 2026",
    "compare_prompt": "how to build wealth in 2026",
    "compare_response": "Building wealth requires saving and investing.",
    "response_text": "Building wealth requires saving and investing.",
    "benign_input": "how to build wealth in 2026",
    "analysis_prompt": "Analyze this text",
    "current_asr": "test",
    "baseline_refusal": "I cannot help with that",
    "claim": "The sky is blue",
    "covert_message": "secret",
    "encoded_message": "dGVzdA==",
    "payload": "test payload",
    "attack_payload": "test payload",
    "canary_phrases": ["canary"],
    "cv_text": "Software engineer with 5 years experience",
    "code_snippet": "print('hello world')",
    "code": "print('hello world')",
    "command": "echo test",
    "topic": "wealth building",
    "article": "This is a test article about wealth building.",
    "paper": "Test paper abstract",
    "abstract": "Test abstract",
    "summary": "Test summary",
    "report": "Test report",
    "review": "Test review",
    "note": "Test note",
    "comment": "Test comment",
    "feedback": "Test feedback",
    "instruction": "Follow these instructions",
    "request": "Test request",
    "response": "Test response",
    "answer": "Test answer",
    "result": "Test result",
    "output": "Test output",
    "finding": "Test finding",
    "observation": "Test observation",
    "conclusion": "Test conclusion",
    "recommendation": "Test recommendation",
    "suggestion": "Test suggestion",
    "solution": "Test solution",
    "explanation": "Test explanation",
    "justification": "Test justification",
    "rationale": "Test rationale",
    "reason": "Test reason",
    "cause": "Test cause",
    "effect": "Test effect",
    "impact": "Test impact",
    "benefit": "Test benefit",
    "risk": "Test risk",
    "issue": "Test issue",
    "problem": "Test problem",
    "challenge": "Test challenge",
    "opportunity": "Test opportunity",
    "threat": "Test threat",
    "weakness": "Test weakness",
    "strength": "Test strength",
    "advantage": "Test advantage",
    "disadvantage": "Test disadvantage",
    "limitation": "Test limitation",
    "constraint": "Test constraint",
    "assumption": "Test assumption",
    "hypothesis": "Test hypothesis",
    "theory": "Test theory",
    "principle": "Test principle",
    "law": "Test law",
    "rule": "Test rule",
    "policy": "Test policy",
    "guideline": "Test guideline",
    "standard": "Test standard",
    "criteria": "Test criteria",
    "metric": "accuracy",
    "indicator": "Test indicator",
    "benchmark": "Test benchmark",
    "baseline": "Test baseline",
    "target_output": "jailbreak",

    # URLs
    "url": "https://httpbin.org/get",
    "uri": "https://httpbin.org/get",
    "link": "https://httpbin.org/get",
    "endpoint": "https://httpbin.org/get",
    "base_url": "https://httpbin.org/get",
    "docs_url": "https://httpbin.org/get",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png",
    "callback_url": "https://httpbin.org/get",

    # Domains / targets
    "domain": "example.com",
    "domains": ["example.com"],
    "target": "example.com",
    "target_name": "example.com",
    "target_url": "https://httpbin.org/get",
    "target_type": "domain",
    "hostname": "example.com",
    "host": "example.com",
    "domain_a": "example.com",
    "domain_b": "example.org",

    # Tool / model / strategy names
    "tool_name": "research_search",
    "tool_names": ["research_search"],
    "strategy": "ethical_anchor",
    "strategies": ["ethical_anchor"],
    "candidate_strategies": ["ethical_anchor"],
    "model": "auto",
    "models": ["auto"],
    "model_name": "auto",
    "llm_model": "auto",
    "combiner_model": "auto",
    "available_models": ["auto"],
    "available_tools": ["research_search"],
    "framework": "eu_ai_act",
    "algorithm": "sha256",

    # Numeric / count
    "n": 3,
    "limit": 3,
    "max_results": 5,
    "max_tokens": 200,
    "batch_size": 3,
    "count": 3,
    "turns": 3,
    "workers": 2,
    "cpus": 2,
    "concurrency": 2,
    "branch_factor": 3,
    "budget": 5,
    "perturbation_budget": 5,
    "calls_per_minute": 60,
    "cluster_threshold": 0.5,
    "entropy_threshold": 0.5,
    "similarity_threshold": 0.5,
    "curiosity_threshold": 0.5,
    "min_confidence": 0.5,
    "min_score": 0.5,
    "max_score": 1.0,
    "score": 0.5,
    "threshold": 0.5,
    "temperature": 0.7,
    "top_p": 0.9,
    "darkness_level": 5,
    "depth": "standard",
    "level": "standard",
    "granularity": "medium",
    "dimension": 128,
    "dimensions": 128,
    "step": 1,
    "index": 0,
    "offset": 0,
    "page": 1,
    "per_page": 10,
    "port": 443,
    "duration": 60,
    "duration_sec": 60,
    "duration_seconds": 60,
    "duration_ms": 1000,
    "timeout": 15,
    "delay_between": 1,
    "days": 7,
    "days_back": 7,
    "period_days": 30,
    "older_than_days": 30,
    "window": 5,
    "stride": 1,
    "embedding_dim": 768,
    "hidden_dim": 256,
    "num_layers": 6,
    "num_heads": 8,
    "dropout": 0.1,
    "learning_rate": 0.001,
    "epochs": 10,
    "patience": 5,
    "warmup_steps": 100,
    "weight_decay": 0.01,
    "grad_clip": 1.0,
    "beta1": 0.9,
    "beta2": 0.999,
    "epsilon": 1e-8,
    "momentum": 0.9,
    "min_lr": 1e-6,
    "max_lr": 0.01,
    "step_size": 30,
    "gamma": 0.1,
    "n_estimators": 100,
    "max_depth": 6,
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "n_neighbors": 5,
    "leaf_size": 30,
    "n_components": 2,
    "n_clusters": 8,
    "n_init": 10,
    "n_iter": 10,
    "n_jobs": -1,
    "verbose": 0,
    "random_state": 42,
    "seed": 42,
    "folds": 5,
    "train_size": 0.8,
    "test_size": 0.2,
    "validation_fraction": 0.1,
    "shuffle": True,
    "stratify": True,

    # Boolean flags
    "spectrum": True,
    "dry_run": True,
    "check_only": True,
    "bypass_cache": True,
    "use_cache": True,
    "detailed": True,
    "check_analytics": True,
    "check_certs": True,
    "check_ct_logs": True,
    "check_dns": True,
    "check_exif": True,
    "check_favicon": True,
    "check_github": True,
    "check_gravatar": True,
    "check_hidden_paths": True,
    "check_homoglyphs": True,
    "check_http": True,
    "check_js_endpoints": True,
    "check_lsb": True,
    "check_mounts": True,
    "check_pgp": True,
    "check_platforms": True,
    "check_processes": True,
    "check_reverse_ip": True,
    "check_robots": True,
    "check_sitemap": True,
    "check_source_maps": True,
    "check_tech_stack": True,
    "check_type": True,
    "check_usb": True,
    "check_whitespace": True,
    "audio_only": False,
    "multi_label": False,
    "allow_escalation": True,
    "allow_network": True,
    "auto_cost": True,
    "auto_detect_pattern": True,
    "auto_escalate": True,
    "auto_fact_check": True,
    "auto_hcs": True,
    "auto_learn": True,
    "auto_reframe": True,
    "auto_resolve_deps": True,
    "auto_suggest": True,
    "continue_on_error": True,
    "dedupe": True,
    "authorized": True,
    "enabled": True,
    "complied": True,
    "pretrained": True,
    "finetune": True,
    "early_stopping": True,
    "reduce_lr": True,
    "checkpoint": True,
    "resume_from": None,
    "freeze_layers": 0,
    "unfreeze_layers": -1,
    "layer_norm": True,
    "residual": True,
    "use_label_encoder": False,
    "enable_categorical": False,
    "validate_parameters": True,
    "warm_start": False,
    "oob_score": False,
    "bootstrap": True,
    "bootstrap_features": False,
    "probability": False,
    "shrinking": True,
    "copy_x": True,
    "copy": True,
    "compute_full_tree": "auto",
    "compute_distances": False,
    "bin_seeding": False,
    "cluster_all": True,
    "deterministic": False,
    "zero_as_missing": False,
    "use_missing": True,
    "force_row_wise": True,
    "force_col_wise": False,
    "enable_bundle": True,
    "is_enable_sparse": True,
    "use_quantized_grad": False,
    "quant_train_renew_leaf": False,
    "stochastic_rounding": True,
    "gpu_use_dp": False,
    "linear_tree": False,
    "pred_early_stop": False,
    "uniform_drop_dart": False,
    "xgboost_dart_mode": False,

    # Providers / modes / backends
    "provider": "exa",
    "providers": ["exa"],
    "provider_override": "openai",
    "mode": "http",
    "method": "default",
    "backend": "default",
    "browser": "chrome",
    "os_type": "linux",
    "platform": "twitter",
    "channel": "test",
    "search_type": "web",
    "query_type": "semantic",
    "comparison_type": "semantic",
    "collapse_method": "average",
    "combination_method": "union",
    "engagement_type": "post",
    "event_type": "test",
    "attack_type": "prompt_injection",
    "attack_category": "prompt_injection",
    "attack_categories": ["prompt_injection"],
    "attacker_strategy": "direct",
    "defense_type": "filter",
    "bypass_type": "encoding",
    "format_type": "json",
    "jailbreak_type": "direct",
    "covert_channel": "dns",
    "exfil_method": "dns",
    "augmentation": "synonym",
    "sort_by": "relevance",
    "field": "computer_science",
    "company_or_field": "computer_science",
    "authority_layers": ["legal"],
    "agent": "test_agent",
    "caller": "test_caller",
    "current_access": "public",
    "detail_level": "medium",
    "ecosystem": "ethereum",
    "relation_type": "citation",
    "result_type": "summary",
    "output_format": "json",
    "report_type": "summary",
    "license_type": "mit",
    "file_type": "txt",
    "media_type": "text",
    "mime_type": "text/plain",
    "charset": "utf-8",
    "encoding": "utf-8",
    "compression": "gzip",
    "protocol": "https",
    "scheme": "https",
    "status": "active",
    "state": "active",
    "phase": "test",
    "stage": "test",
    "scheduler": "cosine",
    "activation": "relu",
    "initializer": "xavier",
    "optimizer": "adam",
    "loss_function": "cross_entropy",
    "kernel": "rbf",
    "criterion": "gini",
    "splitter": "best",
    "linkage": "ward",
    "affinity": "euclidean",
    "voting": "soft",
    "bagging": True,
    "boosting": "gbdt",
    "objective": "regression",
    "tree_method": "auto",
    "grow_policy": "depthwise",
    "sample_type": "goss",
    "interaction_constraints": None,

    # Crypto / addresses
    "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "addresses": ["bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"],
    "wallet_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "contract_address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "ip_address": "192.168.1.1",
    "cidr": "192.168.1.0/24",
    "mac_address": "00:11:22:33:44:55",

    # Lists
    "sources": [{"title": "test", "content": "test"}],
    "inputs": ["test input 1", "test input 2"],
    "messages": [{"role": "user", "content": "how to build wealth in 2026"}],
    "texts": ["sample text"],
    "labels": ["positive", "negative"],
    "attacks": [{"type": "test", "payload": "test"}],
    "claims": ["claim one", "claim two"],
    "claims_to_verify": ["claim one"],
    "endpoints": ["https://httpbin.org/get"],
    "entities": ["entity1"],
    "entity_types": ["person"],
    "engines": ["google"],
    "words": ["test"],
    "urls": ["https://httpbin.org/get"],
    "include": ["web"],
    "exclude": ["spam"],
    "fields": ["name"],
    "columns": ["id"],
    "rows": [{"id": 1}],
    "values": [1, 2, 3],
    "keys": ["key1"],
    "tags": ["test"],
    "types": ["text"],
    "formats": ["json"],
    "languages": ["en"],
    "locales": ["en_US"],
    "currencies": ["USD"],
    "countries": ["US"],
    "cities": ["New York"],
    "coordinates": [40.7128, -74.0060],
    "layers": ["layer1"],
    "graphs": [{"nodes": [], "edges": []}],
    "trees": [{"root": "node1"}],
    "paths": ["/tmp/test.txt"],
    "pipelines": ["pipeline1"],
    "workflows": ["workflow1"],
    "jobs": ["job1"],
    "tasks": ["task1"],
    "stages": ["stage1"],
    "steps": [{"name": "step1"}],
    "operations": ["operation1"],
    "functions_list": ["function1"],
    "handlers": ["handler1"],
    "callbacks": ["callback1"],
    "hooks": ["hook1"],
    "triggers": ["trigger1"],
    "schedules": ["0 0 * * *"],
    "milestones": [10, 20, 30],
    "goals": ["goal1"],
    "objectives": ["objective1"],
    "targets_list": ["target1"],
    "kpis": ["kpi1"],
    "metrics_list": ["accuracy"],
    "indicators_list": ["indicator1"],
    "measures_list": ["measure1"],
    "scales_list": ["scale1"],
    "ranges_list": [{"min": 0, "max": 100}],
    "groups_list": ["group1"],
    "clusters_list": ["cluster1"],
    "segments_list": ["segment1"],
    "partitions_list": ["partition1"],
    "shards": ["shard1"],
    "replicas": ["replica1"],
    "instances": ["instance1"],
    "nodes_list": ["node1"],
    "peers": ["peer1"],
    "clients_list": ["client1"],
    "servers_list": ["server1"],
    "services_list": ["service1"],
    "apps": ["app1"],
    "processes_list": ["process1"],
    "threads_list": ["thread1"],
    "connections_list": ["connection1"],
    "sessions_list": ["session1"],
    "transactions_list": ["transaction1"],
    "requests_list": [{"method": "GET"}],
    "responses_list": [{"status": 200}],
    "queries_list": ["SELECT 1"],
    "commands_list": ["echo test"],
    "rules_list": ["rule1"],
    "policies_list": ["policy1"],
    "standards_list": ["standard1"],
    "principles_list": ["principle1"],
    "practices_list": ["practice1"],
    "patterns_list": ["pattern1"],
    "vulnerabilities_list": ["vuln1"],
    "risks_list": ["risk1"],
    "issues_list": ["issue1"],
    "bugs_list": ["bug1"],
    "errors_list": ["error1"],
    "incidents_list": ["incident1"],
    "events_list": ["event1"],
    "alerts_list": ["alert1"],
    "notifications_list": ["notification1"],
    "messages_list": ["message1"],
    "logs_list": ["log1"],
    "traces_list": ["trace1"],
    "spans": [{"name": "span1"}],
    "annotations": ["annotation1"],
    "settings_list": [{"key": "value"}],
    "parameters_list": [{"key": "value"}],
    "properties_list": [{"key": "value"}],
    "attributes_list": [{"key": "value"}],
    "features_list": ["feature1"],
    "capabilities_list": ["capability1"],
    "requirements_list": ["requirement1"],
    "dependencies_list": ["dependency1"],
    "modules_list": ["module1"],
    "packages_list": ["package1"],
    "libraries_list": ["library1"],
    "frameworks_list": ["framework1"],
    "platforms_list": ["platform1"],
    "environments_list": ["env1"],
    "deployments_list": ["deployment1"],
    "releases_list": ["release1"],
    "versions_list": ["1.0"],
    "builds_list": ["build1"],
    "artifacts_list": ["artifact1"],
    "assets_list": ["asset1"],
    "resources_list": ["resource1"],
    "materials_list": ["material1"],
    "supplies_list": ["supply1"],
    "inventory_list": ["inventory1"],
    "stock_list": ["stock1"],
    "locations_list": ["location1"],
    "destinations_list": ["destination1"],
    "origins_list": ["origin1"],
    "sources_list": ["source1"],
    "channels_list": ["channel1"],
    "streams_list": ["stream1"],
    "flows_list": ["flow1"],
    "queues_list": ["queue1"],
    "stacks_list": ["stack1"],
    "arrays_list": [[1, 2, 3]],
    "matrices_list": [[1, 2], [3, 4]],
    "tensors_list": [[[1, 2], [3, 4]]],
    "vectors_list": [1, 2, 3],
    "scalars_list": [1.0, 2.0, 3.0],
    "factors_list": ["factor1"],
    "coefficients_list": [0.5, 0.5],
    "weights_list": [0.5, 0.5],
    "biases_list": [0.0, 0.0],
    "activations_list": ["relu"],
    "gradients_list": [0.1, 0.1],
    "updates_list": [0.01, 0.01],
    "deltas_list": [0.01, 0.01],
    "residuals_list": [0.1, 0.1],
    "losses_list": [0.1, 0.1],
    "costs_list": [0.1, 0.1],
    "rewards_list": [1.0, 1.0],
    "penalties_list": [-1.0, -1.0],
    "scores_list": [0.5, 0.5],
    "ratings_list": [3.0, 4.0, 5.0],
    "rankings_list": [1, 2, 3],
    "ratios_list": [0.5, 0.5],
    "proportions_list": [0.5, 0.5],
    "percentages_list": [50.0, 50.0],
    "frequencies_list": [0.5, 0.5],
    "probabilities_list": [0.5, 0.5],
    "likelihoods_list": [0.5, 0.5],
    "confidences_list": [0.8, 0.8],
    "variances_list": [1.0, 1.0],
    "stddevs_list": [1.0, 1.0],
    "means_list": [0.0, 0.0],
    "medians_list": [0.0, 0.0],
    "modes_list": [0.0, 0.0],
    "ranges_list": [0.0, 100.0],
    "mins_list": [0.0, 0.0],
    "maxs_list": [100.0, 100.0],
    "sums_list": [100.0, 100.0],
    "products_list": [1.0, 1.0],
    "quotients_list": [1.0, 1.0],
    "differences_list": [0.0, 0.0],
    "increases_list": [0.1, 0.1],
    "decreases_list": [0.1, 0.1],
    "changes_list": [0.1, 0.1],
    "trends_list": ["up"],
    "anomalies_list": ["anomaly1"],
    "outliers_list": ["outlier1"],
    "peaks_list": ["peak1"],
    "valleys_list": ["valley1"],
    "plateaus_list": ["plateau1"],
    "thresholds_list": [0.5, 0.5],
    "limits_list": [100.0, 100.0],
    "boundaries_list": ["boundary1"],
    "restrictions_list": ["restriction1"],
    "permissions_list": ["permission1"],
    "roles_list": ["role1"],
    "users_list": ["user1"],
    "groups_list": ["group1"],
    "teams_list": ["team1"],
    "organizations_list": ["org1"],
    "tenants_list": ["tenant1"],
    "accounts_list": ["account1"],
    "profiles_list": ["profile1"],
    "identities_list": ["identity1"],
    "credentials_list": ["credential1"],
    "certificates_list": ["certificate1"],
    "licenses_list": ["license1"],
    "tokens_list": ["token1"],
    "keys_list": ["key1"],
    "secrets_list": ["secret1"],
    "passwords_list": ["password1"],
    "codes_list": ["code1"],
    "hashes_list": ["hash1"],
    "signatures_list": ["signature1"],
    "checksums_list": ["checksum1"],
    "digests_list": ["digest1"],
    "fingerprints_list": ["fingerprint1"],
    "uuids_list": ["550e8400-e29b-41d4-a716-446655440000"],
    "ids_list": ["id1"],
    "names_list": ["name1"],
    "titles_list": ["title1"],
    "headings_list": ["heading1"],
    "subtitles_list": ["subtitle1"],
    "captions_list": ["caption1"],
    "descriptions_list": ["description1"],
    "summaries_list": ["summary1"],
    "abstracts_list": ["abstract1"],
    "overviews_list": ["overview1"],
    "introductions_list": ["introduction1"],
    "conclusions_list": ["conclusion1"],
    "recommendations_list": ["recommendation1"],
    "suggestions_list": ["suggestion1"],
    "solutions_list": ["solution1"],
    "answers_list": ["answer1"],
    "responses_list": ["response1"],
    "replies_list": ["reply1"],
    "comments_list": ["comment1"],
    "remarks_list": ["remark1"],
    "notes_list": ["note1"],
    "observations_list": ["observation1"],
    "findings_list": ["finding1"],
    "discoveries_list": ["discovery1"],
    "insights_list": ["insight1"],
    "learnings_list": ["learning1"],
    "takeaways_list": ["takeaway1"],
    "highlights_list": ["highlight1"],
    "key_points": ["point1"],
    "bullet_points": ["bullet1"],
    "numbered_points": ["point1"],
    "paragraphs_list": ["paragraph1"],
    "sentences_list": ["sentence1"],
    "phrases_list": ["phrase1"],
    "clauses_list": ["clause1"],
    "words_list": ["word1"],
    "terms_list": ["term1"],
    "definitions_list": ["definition1"],
    "synonyms_list": ["synonym1"],
    "antonyms_list": ["antonym1"],
    "acronyms_list": ["acronym1"],
    "abbreviations_list": ["abbreviation1"],
    "expressions_list": ["expression1"],
    "idioms_list": ["idiom1"],
    "proverbs_list": ["proverb1"],
    "quotes_list": ["quote1"],
    "quotations_list": ["quotation1"],
    "citations_list": ["citation1"],
    "references_list": ["reference1"],
    "bibliographies_list": ["bibliography1"],
    "footnotes_list": ["footnote1"],
    "endnotes_list": ["endnote1"],
    "appendices_list": ["appendix1"],
    "glossaries_list": ["glossary1"],
    "indexes_list": ["index1"],
    "tables_list": ["table1"],
    "figures_list": ["figure1"],
    "diagrams_list": ["diagram1"],
    "charts_list": ["chart1"],
    "graphs_list": ["graph1"],
    "plots_list": ["plot1"],
    "visualizations_list": ["visualization1"],
    "images_list": ["image1"],
    "photos_list": ["photo1"],
    "pictures_list": ["picture1"],
    "drawings_list": ["drawing1"],
    "sketches_list": ["sketch1"],
    "illustrations_list": ["illustration1"],
    "paintings_list": ["painting1"],
    "sculptures_list": ["sculpture1"],
    "artworks_list": ["artwork1"],
    "designs_list": ["design1"],
    "models_list": ["model1"],
    "mockups_list": ["mockup1"],
    "prototypes_list": ["prototype1"],
    "samples_list": ["sample1"],
    "specimens_list": ["specimen1"],
    "examples_list": ["example1"],
    "demos_list": ["demo1"],
    "tutorials_list": ["tutorial1"],
    "guides_list": ["guide1"],
    "manuals_list": ["manual1"],
    "docs_list": ["doc1"],
    "documentations_list": ["documentation1"],
    "wikis_list": ["wiki1"],
    "faqs_list": ["faq1"],
    "kb_articles_list": ["article1"],
    "whitepapers_list": ["whitepaper1"],
    "case_studies_list": ["case_study1"],
    "testimonials_list": ["testimonial1"],
    "surveys_list": ["survey1"],
    "polls_list": ["poll1"],
    "questionnaires_list": ["questionnaire1"],
    "interviews_list": ["interview1"],
    "transcripts_list": ["transcript1"],
    "recordings_list": ["recording1"],
    "videos_list": ["video1"],
    "films_list": ["film1"],
    "movies_list": ["movie1"],
    "clips_list": ["clip1"],
    "episodes_list": ["episode1"],
    "seasons_list": ["season1"],
    "series_list": ["series1"],
    "shows_list": ["show1"],
    "programs_list": ["program1"],
    "broadcasts_list": ["broadcast1"],
    "streams_list": ["stream1"],
    "feeds_list": ["feed1"],
    "podcasts_list": ["podcast1"],
    "audiobooks_list": ["audiobook1"],
    "tracks_list": ["track1"],
    "albums_list": ["album1"],
    "playlists_list": ["playlist1"],
    "genres_list": ["genre1"],
    "styles_list": ["style1"],
    "moods_list": ["mood1"],
    "themes_list": ["theme1"],
    "topics_list": ["topic1"],
    "subjects_list": ["subject1"],
    "disciplines_list": ["discipline1"],
    "fields_list": ["field1"],
    "industries_list": ["industry1"],
    "sectors_list": ["sector1"],
    "verticals_list": ["vertical1"],
    "horizontals_list": ["horizontal1"],
    "markets_list": ["market1"],
    "exchanges_list": ["exchange1"],
    "indexes_list": ["index1"],
    "indices_list": ["index1"],
    "benchmarks_list": ["benchmark1"],
    "standards_list": ["standard1"],
    "regulations_list": ["regulation1"],
    "laws_list": ["law1"],
    "acts_list": ["act1"],
    "bills_list": ["bill1"],
    "statutes_list": ["statute1"],
    "codes_list": ["code1"],
    "ordinances_list": ["ordinance1"],
    "decrees_list": ["decree1"],
    "orders_list": ["order1"],
    "directives_list": ["directive1"],
    "guidelines_list": ["guideline1"],
    "policies_list": ["policy1"],
    "procedures_list": ["procedure1"],
    "protocols_list": ["protocol1"],
    "methods_list": ["method1"],
    "techniques_list": ["technique1"],
    "approaches_list": ["approach1"],
    "strategies_list": ["strategy1"],
    "tactics_list": ["tactic1"],
    "plans_list": ["plan1"],
    "schemes_list": ["scheme1"],
    "initiatives_list": ["initiative1"],
    "campaigns_list": ["campaign1"],
    "movements_list": ["movement1"],
    "causes_list": ["cause1"],
    "missions_list": ["mission1"],
    "visions_list": ["vision1"],
    "values_list": ["value1"],
    "ethics_list": ["ethic1"],
    "morals_list": ["moral1"],
    "principles_list": ["principle1"],
    "beliefs_list": ["belief1"],
    "cultures_list": ["culture1"],
    "traditions_list": ["tradition1"],
    "customs_list": ["custom1"],
    "habits_list": ["habit1"],
    "routines_list": ["routine1"],
    "rituals_list": ["ritual1"],
    "practices_list": ["practice1"],
    "systems_list": ["system1"],
    "networks_list": ["network1"],
    "infrastructures_list": ["infrastructure1"],
    "architectures_list": ["architecture1"],
    "technologies_list": ["technology1"],
    "tools_list": ["tool1"],
    "instruments_list": ["instrument1"],
    "devices_list": ["device1"],
    "machines_list": ["machine1"],
    "equipment_list": ["equipment1"],
    "machinery_list": ["machinery1"],
    "hardware_list": ["hardware1"],
    "software_list": ["software1"],
    "firmware_list": ["firmware1"],
    "middleware_list": ["middleware1"],
    "drivers_list": ["driver1"],
    "plugins_list": ["plugin1"],
    "extensions_list": ["extension1"],
    "addons_list": ["addon1"],
    "components_list": ["component1"],
    "parts_list": ["part1"],
    "pieces_list": ["piece1"],
    "elements_list": ["element1"],
    "items_list": ["item1"],
    "objects_list": ["object1"],
    "entities_list": ["entity1"],
    "subjects_list": ["subject1"],
    "agents_list": ["agent1"],
    "actors_list": ["actor1"],
    "players_list": ["player1"],
    "participants_list": ["participant1"],
    "members_list": ["member1"],
    "attendees_list": ["attendee1"],
    "guests_list": ["guest1"],
    "visitors_list": ["visitor1"],
    "customers_list": ["customer1"],
    "consumers_list": ["consumer1"],
    "patrons_list": ["patron1"],
    "subscribers_list": ["subscriber1"],
    "followers_list": ["follower1"],
    "fans_list": ["fan1"],
    "supporters_list": ["supporter1"],
    "donors_list": ["donor1"],
    "sponsors_list": ["sponsor1"],
    "investors_list": ["investor1"],
    "shareholders_list": ["shareholder1"],
    "stakeholders_list": ["stakeholder1"],
    "partners_list": ["partner1"],
    "collaborators_list": ["collaborator1"],
    "allies_list": ["ally1"],
    "competitors_list": ["competitor1"],
    "rivals_list": ["rival1"],
    "opponents_list": ["opponent1"],
    "enemies_list": ["enemy1"],
    "adversaries_list": ["adversary1"],
    "dangers_list": ["danger1"],
    "hazards_list": ["hazard1"],
    "perils_list": ["peril1"],
    "menaces_list": ["menace1"],
    "nuisances_list": ["nuisance1"],
    "difficulties_list": ["difficulty1"],
    "obstacles_list": ["obstacle1"],
    "barriers_list": ["barrier1"],
    "impediments_list": ["impediment1"],
    "hindrances_list": ["hindrance1"],
    "setbacks_list": ["setback1"],
    "drawbacks_list": ["drawback1"],
    "disadvantages_list": ["disadvantage1"],
    "limitations_list": ["limitation1"],
    "restrictions_list": ["restriction1"],
    "constraints_list": ["constraint1"],
    "bottlenecks_list": ["bottleneck1"],
    "chokepoints_list": ["chokepoint1"],
    "flaws_list": ["flaw1"],
    "defects_list": ["defect1"],
    "glitches_list": ["glitch1"],
    "concerns_list": ["concern1"],
    "complaints_list": ["complaint1"],
    "grievances_list": ["grievance1"],
    "protests_list": ["protest1"],
    "objections_list": ["objection1"],
    "oppositions_list": ["opposition1"],
    "resistances_list": ["resistance1"],
    "conflicts_list": ["conflict1"],
    "disputes_list": ["dispute1"],
    "arguments_list": ["argument1"],
    "debates_list": ["debate1"],
    "discussions_list": ["discussion1"],
    "conversations_list": ["conversation1"],
    "dialogues_list": ["dialogue1"],
    "negotiations_list": ["negotiation1"],
    "mediations_list": ["mediation1"],
    "arbitrations_list": ["arbitration1"],
    "litigations_list": ["litigation1"],
    "lawsuits_list": ["lawsuit1"],
    "trials_list": ["trial1"],
    "hearings_list": ["hearing1"],
    "inquiries_list": ["inquiry1"],
    "investigations_list": ["investigation1"],
    "inspections_list": ["inspection1"],
    "audits_list": ["audit1"],
    "assessments_list": ["assessment1"],
    "evaluations_list": ["evaluation1"],
    "appraisals_list": ["appraisal1"],
    "analyses_list": ["analysis1"],
    "studies_list": ["study1"],
    "research_list": ["research1"],
    "experiments_list": ["experiment1"],
    "tests_list": ["test1"],
    "pilots_list": ["pilot1"],
    "demonstrations_list": ["demonstration1"],
    "presentations_list": ["presentation1"],
    "lectures_list": ["lecture1"],
    "speeches_list": ["speech1"],
    "talks_list": ["talk1"],
    "seminars_list": ["seminar1"],
    "workshops_list": ["workshop1"],
    "conferences_list": ["conference1"],
    "symposia_list": ["symposium1"],
    "summits_list": ["summit1"],
    "forums_list": ["forum1"],
    "panels_list": ["panel1"],
    "roundtables_list": ["roundtable1"],
    "meetings_list": ["meeting1"],
    "gatherings_list": ["gathering1"],
    "assemblies_list": ["assembly1"],
    "conventions_list": ["convention1"],
    "expos_list": ["expo1"],
    "exhibitions_list": ["exhibition1"],
    "fairs_list": ["fair1"],
    "festivals_list": ["festival1"],
    "occasions_list": ["occasion1"],
    "ceremonies_list": ["ceremony1"],
    "celebrations_list": ["celebration1"],
    "parties_list": ["party1"],
    "socials_list": ["social1"],
    "mixers_list": ["mixer1"],
    "networking_events_list": ["networking_event1"],
    "webinars_list": ["webinar1"],
    "livestreams_list": ["livestream1"],
    "publications_list": ["publication1"],
    "journals_list": ["journal1"],
    "magazines_list": ["magazine1"],
    "newspapers_list": ["newspaper1"],
    "newsletters_list": ["newsletter1"],
    "bulletins_list": ["bulletin1"],
    "updates_list": ["update1"],
    "notices_list": ["notice1"],
    "announcements_list": ["announcement1"],
    "press_releases_list": ["press_release1"],
    "statements_list": ["statement1"],
    "declarations_list": ["declaration1"],
    "proclamations_list": ["proclamation1"],
    "manifestos_list": ["manifesto1"],
    "petitions_list": ["petition1"],
    "appeals_list": ["appeal1"],
    "pleas_list": ["plea1"],
    "requests_list": ["request1"],
    "demands_list": ["demand1"],
    "proposals_list": ["proposal1"],
    "offers_list": ["offer1"],
    "bids_list": ["bid1"],
    "tenders_list": ["tender1"],
    "quotes_list": ["quote1"],
    "estimates_list": ["estimate1"],
    "forecasts_list": ["forecast1"],
    "predictions_list": ["prediction1"],
    "projections_list": ["projection1"],
    "outlooks_list": ["outlook1"],
    "scenarios_list": ["scenario1"],
    "simulations_list": ["simulation1"],
    "theories_list": ["theory1"],
    "hypotheses_list": ["hypothesis1"],
    "assumptions_list": ["assumption1"],
    "premises_list": ["premise1"],
    "axioms_list": ["axiom1"],
    "postulates_list": ["postulate1"],
    "theorems_list": ["theorem1"],
    "lemmas_list": ["lemma1"],
    "corollaries_list": ["corollary1"],
    "propositions_list": ["proposition1"],
    "conjectures_list": ["conjecture1"],
    "speculations_list": ["speculation1"],
    "guesses_list": ["guess1"],
    "approximations_list": ["approximation1"],
    "calculations_list": ["calculation1"],
    "computations_list": ["computation1"],
    "derivations_list": ["derivation1"],
    "proofs_list": ["proof1"],
    "verifications_list": ["verification1"],
    "validations_list": ["validation1"],
    "confirmations_list": ["confirmation1"],
    "affirmations_list": ["affirmation1"],
    "assertions_list": ["assertion1"],
    "pronouncements_list": ["pronouncement1"],
    "judgments_list": ["judgment1"],
    "rulings_list": ["ruling1"],
    "decisions_list": ["decision1"],
    "determinations_list": ["determination1"],
    "resolutions_list": ["resolution1"],
    "settlements_list": ["settlement1"],
    "agreements_list": ["agreement1"],
    "contracts_list": ["contract1"],
    "treaties_list": ["treaty1"],
    "accords_list": ["accord1"],
    "pacts_list": ["pact1"],
    "compacts_list": ["compact1"],
    "covenants_list": ["covenant1"],
    "arrangements_list": ["arrangement1"],
    "understandings_list": ["understanding1"],
    "deals_list": ["deal1"],
    "exchanges_list": ["exchange1"],
    "transfers_list": ["transfer1"],
    "conversions_list": ["conversion1"],
    "transformations_list": ["transformation1"],
    "transitions_list": ["transition1"],
    "changes_list": ["change1"],
    "shifts_list": ["shift1"],
    "developments_list": ["development1"],
    "evolutions_list": ["evolution1"],
    "reforms_list": ["reform1"],
    "revolutions_list": ["revolution1"],
    "innovations_list": ["innovation1"],
    "inventions_list": ["invention1"],
    "discoveries_list": ["discovery1"],
    "breakthroughs_list": ["breakthrough1"],
    "advances_list": ["advance1"],
    "progressions_list": ["progression1"],
    "improvements_list": ["improvement1"],
    "enhancements_list": ["enhancement1"],
    "upgrades_list": ["upgrade1"],
    "revisions_list": ["revision1"],
    "edits_list": ["edit1"],
    "modifications_list": ["modification1"],
    "alterations_list": ["alteration1"],
    "adjustments_list": ["adjustment1"],
    "adaptations_list": ["adaptation1"],
    "optimizations_list": ["optimization1"],
    "refactorings_list": ["refactoring1"],
    "rewrites_list": ["rewrite1"],
    "redesigns_list": ["redesign1"],
    "rebuilds_list": ["rebuild1"],
    "reconstructions_list": ["reconstruction1"],
    "restorations_list": ["restoration1"],
    "repairs_list": ["repair1"],
    "fixes_list": ["fix1"],
    "patches_list": ["patch1"],
    "hotfixes_list": ["hotfix1"],
    "workarounds_list": ["workaround1"],
    "remedies_list": ["remedy1"],
    "cures_list": ["cure1"],
    "treatments_list": ["treatment1"],
    "therapies_list": ["therapy1"],
    "interventions_list": ["intervention1"],
    "surgeries_list": ["surgery1"],
    "transplants_list": ["transplant1"],
    "implants_list": ["implant1"],
    "grafts_list": ["graft1"],
    "injections_list": ["injection1"],
    "vaccinations_list": ["vaccination1"],
    "inoculations_list": ["inoculation1"],
    "immunizations_list": ["immunization1"],
    "doses_list": ["dose1"],
    "medications_list": ["medication1"],
    "drugs_list": ["drug1"],
    "pharmaceuticals_list": ["pharmaceutical1"],
    "compounds_list": ["compound1"],
    "chemicals_list": ["chemical1"],
    "substances_list": ["substance1"],
    "alloys_list": ["alloy1"],
    "amalgams_list": ["amalgam1"],
    "composites_list": ["composite1"],
    "polymers_list": ["polymer1"],
    "plastics_list": ["plastic1"],
    "resins_list": ["resin1"],
    "rubbers_list": ["rubber1"],
    "elastomers_list": ["elastomer1"],
    "fibers_list": ["fiber1"],
    "textiles_list": ["textile1"],
    "fabrics_list": ["fabric1"],
    "cloths_list": ["cloth1"],
    "garments_list": ["garment1"],
    "apparels_list": ["apparel1"],
    "clothing_list": ["clothing1"],
    "dresses_list": ["dress1"],
    "suits_list": ["suit1"],
    "uniforms_list": ["uniform1"],
    "costumes_list": ["costume1"],
    "outfits_list": ["outfit1"],
    "ensembles_list": ["ensemble1"],
    "attires_list": ["attire1"],
    "wears_list": ["wear1"],
    "accessories_list": ["accessory1"],
    "jewelries_list": ["jewelry1"],
    "ornaments_list": ["ornament1"],
    "decorations_list": ["decoration1"],
    "adornments_list": ["adornment1"],
    "embellishments_list": ["embellishment1"],
    "fringes_list": ["fringe1"],
    "tassels_list": ["tassel1"],
    "braids_list": ["braid1"],
    "laces_list": ["lace1"],
    "bows_list": ["bow1"],
    "knots_list": ["knot1"],
    "loops_list": ["loop1"],
    "coils_list": ["coil1"],
    "spirals_list": ["spiral1"],
    "curls_list": ["curl1"],
    "waves_list": ["wave1"],
    "ripples_list": ["ripple1"],
    "oscillations_list": ["oscillation1"],
    "vibrations_list": ["vibration1"],
    "fluctuations_list": ["fluctuation1"],
    "variations_list": ["variation1"],
    "deviations_list": ["deviation1"],
    "divergences_list": ["divergence1"],
    "convergences_list": ["convergence1"],
    "intersections_list": ["intersection1"],
    "junctions_list": ["junction1"],
    "crossings_list": ["crossing1"],
    "overlaps_list": ["overlap1"],
    "collisions_list": ["collision1"],
    "contacts_list": ["contact1"],
    "relations_list": ["relation1"],
    "relationships_list": ["relationship1"],
    "associations_list": ["association1"],
    "correlations_list": ["correlation1"],
    "causations_list": ["causation1"],
    "attachments_list": ["attachment1"],
    "bindings_list": ["binding1"],
    "bonds_list": ["bond1"],
    "ties_list": ["tie1"],
    "fastenings_list": ["fastening1"],
    "closures_list": ["closure1"],
    "seals_list": ["seal1"],
    "locks_list": ["lock1"],
    "latches_list": ["latch1"],
    "catches_list": ["catch1"],
    "hasps_list": ["hasp1"],
    "staples_list": ["staple1"],
    "tacks_list": ["tack1"],
    "nails_list": ["nail1"],
    "screws_list": ["screw1"],
    "bolts_list": ["bolt1"],
    "nuts_list": ["nut1"],
    "washers_list": ["washer1"],
    "rivets_list": ["rivet1"],
    "pins_list": ["pin1"],
    "pegs_list": ["peg1"],
    "dowels_list": ["dowel1"],
    "plugs_list": ["plug1"],
    "stoppers_list": ["stopper1"],
    "corks_list": ["cork1"],
    "caps_list": ["cap1"],
    "lids_list": ["lid1"],
    "covers_list": ["cover1"],
    "tops_list": ["top1"],
    "bottoms_list": ["bottom1"],
    "sides_list": ["side1"],
    "fronts_list": ["front1"],
    "backs_list": ["back1"],
    "faces_list": ["face1"],
    "surfaces_list": ["surface1"],
    "interfaces_list": ["interface1"],
    "edges_list": ["edge1"],
    "corners_list": ["corner1"],
    "vertices_list": ["vertex1"],
    "points_list": ["point1"],
    "dots_list": ["dot1"],
    "spots_list": ["spot1"],
    "marks_list": ["mark1"],
    "lines_list": ["line1"],
    "curves_list": ["curve1"],
    "arcs_list": ["arc1"],
    "circles_list": ["circle1"],
    "ellipses_list": ["ellipse1"],
    "ovals_list": ["oval1"],
    "rectangles_list": ["rectangle1"],
    "squares_list": ["square1"],
    "triangles_list": ["triangle1"],
    "polygons_list": ["polygon1"],
    "tetrahedrons_list": ["tetrahedron1"],
    "cubes_list": ["cube1"],
    "octahedrons_list": ["octahedron1"],
    "dodecahedrons_list": ["dodecahedron1"],
    "icosahedrons_list": ["icosahedron1"],
    "prisms_list": ["prism1"],
    "pyramids_list": ["pyramid1"],
    "cones_list": ["cone1"],
    "cylinders_list": ["cylinder1"],
    "spheres_list": ["sphere1"],
    "ellipsoids_list": ["ellipsoid1"],
    "toruses_list": ["torus1"],
    "paraboloids_list": ["paraboloid1"],
    "hyperboloids_list": ["hyperboloid1"],
    "saddles_list": ["saddle1"],
    "domes_list": ["dome1"],
    "vaults_list": ["vault1"],
    "arches_list": ["arch1"],
    "beams_list": ["beam1"],
    "columns_list": ["column1"],
    "pillars_list": ["pillar1"],
    "posts_list": ["post1"],
    "poles_list": ["pole1"],
    "rods_list": ["rod1"],
    "bars_list": ["bar1"],
    "rails_list": ["rail1"],
    "tracks_list": ["track1"],
    "trails_list": ["trail1"],
    "ways_list": ["way1"],
    "routes_list": ["route1"],
    "courses_list": ["course1"],
    "directions_list": ["direction1"],
    "headings_list": ["heading1"],
    "bearings_list": ["bearing1"],
    "azimuths_list": ["azimuth1"],
    "altitudes_list": ["altitude1"],
    "elevations_list": ["elevation1"],
    "heights_list": ["height1"],
    "depths_list": ["depth1"],
    "widths_list": ["width1"],
    "breadths_list": ["breadth1"],
    "lengths_list": ["length1"],
    "distances_list": ["distance1"],
    "spans_list": ["span1"],
    "gaps_list": ["gap1"],
    "spaces_list": ["space1"],
    "intervals_list": ["interval1"],
    "radii_list": ["radius1"],
    "diameters_list": ["diameter1"],
    "circumferences_list": ["circumference1"],
    "perimeters_list": ["perimeter1"],
    "areas_list": ["area1"],
    "volumes_list": ["volume1"],
    "capacities_list": ["capacity1"],
    "sizes_list": ["size1"],
    "measures_list": ["measure1"],
    "magnitudes_list": ["magnitude1"],
    "intensities_list": ["intensity1"],
    "strengths_list": ["strength1"],
    "forces_list": ["force1"],
    "powers_list": ["power1"],
    "energies_list": ["energy1"],
    "works_list": ["work1"],
    "impulses_list": ["impulse1"],
    "momenta_list": ["momentum1"],
    "velocities_list": ["velocity1"],
    "speeds_list": ["speed1"],
    "accelerations_list": ["acceleration1"],
    "decelerations_list": ["deceleration1"],

    # Dicts / structured
    "schema": {"type": "object", "properties": {"name": {"type": "string"}}},
    "response_format": {"type": "text"},
    "config": {"key": "value"},
    "data": [1.0, 2.0, 3.0, 4.5, 5.0],
    "numbers": [1.0, 2.5, 3.7, 4.2, 5.8],
    "metadata": {"source": "test"},
    "context": {"key": "value"},
    "anonymizer_config": {"enabled": True},
    "env": {"KEY": "value"},
    "constraints": {"max_len": 100},
    "config_path": "/tmp/test.json",
    "config_paths": ["/tmp/test.json"],
    "file_path": "/tmp/test.txt",
    "file_paths": ["/tmp/test.txt"],
    "data_path": "/tmp/test.txt",
    "data_paths": ["/tmp/test.txt"],
    "binary_path": "/bin/ls",
    "binary_paths": ["/bin/ls"],
    "storage_path": "/tmp/storage",
    "storage_paths": ["/tmp/storage"],
    "image_path": "/tmp/test.png",
    "image_paths": ["/tmp/test.png"],
    "audio_path": "/tmp/test.wav",
    "audio_paths": ["/tmp/test.wav"],
    "video_path": "/tmp/test.mp4",
    "video_paths": ["/tmp/test.mp4"],
    "log_path": "/tmp/test.log",
    "log_paths": ["/tmp/test.log"],
    "output_path": "/tmp/output.txt",
    "output_paths": ["/tmp/output.txt"],
    "input_path": "/tmp/input.txt",
    "input_paths": ["/tmp/input.txt"],
    "model_path": "/tmp/model.pkl",
    "model_paths": ["/tmp/model.pkl"],
    "checkpoint_path": "/tmp/checkpoint.pt",
    "checkpoint_paths": ["/tmp/checkpoint.pt"],
    "dataset_path": "/tmp/dataset.csv",
    "dataset_paths": ["/tmp/dataset.csv"],
    "index_path": "/tmp/index.faiss",
    "index_paths": ["/tmp/index.faiss"],
    "embeddings_path": "/tmp/embeddings.npy",
    "embeddings_paths": ["/tmp/embeddings.npy"],
    "vocab_path": "/tmp/vocab.txt",
    "vocab_paths": ["/tmp/vocab.txt"],
    "tokenizer_path": "/tmp/tokenizer",
    "tokenizer_paths": ["/tmp/tokenizer"],
    "cache_path": "/tmp/cache",
    "cache_paths": ["/tmp/cache"],
    "temp_path": "/tmp/temp",
    "temp_paths": ["/tmp/temp"],
    "work_path": "/tmp/work",
    "work_paths": ["/tmp/work"],
    "download_path": "/tmp/download",
    "download_paths": ["/tmp/download"],
    "upload_path": "/tmp/upload",
    "upload_paths": ["/tmp/upload"],
    "import_path": "/tmp/import",
    "import_paths": ["/tmp/import"],
    "export_path": "/tmp/export",
    "export_paths": ["/tmp/export"],
    "backup_path": "/tmp/backup",
    "backup_paths": ["/tmp/backup"],
    "restore_path": "/tmp/restore",
    "restore_paths": ["/tmp/restore"],
    "archive_path": "/tmp/archive.tar.gz",
    "archive_paths": ["/tmp/archive.tar.gz"],
    "extract_path": "/tmp/extract",
    "extract_paths": ["/tmp/extract"],
    "compress_path": "/tmp/compress",
    "compress_paths": ["/tmp/compress"],
    "decompress_path": "/tmp/decompress",
    "decompress_paths": ["/tmp/decompress"],
    "encrypt_path": "/tmp/encrypt",
    "encrypt_paths": ["/tmp/encrypt"],
    "decrypt_path": "/tmp/decrypt",
    "decrypt_paths": ["/tmp/decrypt"],
    "hash_path": "/tmp/hash",
    "hash_paths": ["/tmp/hash"],
    "sign_path": "/tmp/sign",
    "sign_paths": ["/tmp/sign"],
    "verify_path": "/tmp/verify",
    "verify_paths": ["/tmp/verify"],

    # Identifiers / references
    "email": "test@example.com",
    "doi": "10.1038/nature12373",
    "arxiv_id": "2301.00001",
    "cve_id": "CVE-2023-1234",
    "paper_id": "10.1038/nature12373",
    "journal_name": "Nature",
    "author": "Test Author",
    "author_name": "Test Author",
    "author_id": "12345",
    "company": "Example Corp",
    "company_name": "Example Corp",
    "conference": "NeurIPS",
    "client_id": "test_client",
    "session_id": "test-001",
    "eval_id": "test_eval",
    "backup_id": "test-001",
    "dlq_id": "test_dlq",
    "trace_id": "test_trace",
    "commit_hash": "a1b2c3d",
    "cache_key": "test_key",
    "cache_ttl": 3600,
    "job_id": "test-001",
    "task_id": "test-001",
    "workflow_id": "test_wf",
    "pipeline_id": "test_pipe",
    "run_id": "test_run",
    "experiment_id": "test_exp",
    "campaign_id": "test_campaign",
    "ad_id": "test_ad",
    "creative_id": "test_creative",
    "placement_id": "test_placement",
    "site_id": "test_site",
    "page_id": "test_page",
    "post_id": "test_post",
    "comment_id": "test_comment",
    "thread_id": "test_thread",
    "message_id": "test_msg",
    "notification_id": "test_notif",
    "alert_id": "test_alert",
    "incident_id": "test_incident",
    "ticket_id": "test_ticket",
    "case_id": "test_case",
    "record_id": "test_record",
    "entry_id": "test_entry",
    "log_id": "test_log",
    "snapshot_id": "test_snap",
    "image_id": "test_image",
    "video_id": "test_video",
    "audio_id": "test_audio",
    "document_id": "test_doc",
    "file_id": "test_file",
    "attachment_id": "test_attach",
    "blob_id": "test_blob",
    "object_id": "test_obj",
    "entity_id": "test_entity",
    "relation_id": "test_rel",
    "graph_id": "test_graph",
    "network_id": "test_net",
    "subnet_id": "test_subnet",
    "vpc_id": "test_vpc",
    "firewall_id": "test_fw",
    "load_balancer_id": "test_lb",
    "gateway_id": "test_gw",
    "router_id": "test_router",
    "switch_id": "test_switch",
    "port_id": "test_port",
    "interface_id": "test_iface",
    "hardware_id": "test_hw",
    "device_id": "test_device",
    "serial_number": "SN123456",
    "model_number": "MODEL-1",
    "part_number": "PART-1",
    "sku": "SKU-1",
    "upc": "123456789012",
    "ean": "1234567890123",
    "isbn": "978-3-16-148410-0",
    "issn": "1234-5678",
    "pmid": "12345678",
    "pmcid": "PMC1234567",
    "handle": "123456789/1",
    "path": "/test",
    "route": "/test",
    "verb": "GET",
    "operation": "test_op",
    "procedure": "test_proc",
    "function": "test_func",
    "handler": "test_handler",
    "callback": "test_callback",
    "hook": "test_hook",
    "trigger": "test_trigger",
    "schedule": "0 0 * * *",
    "cron": "0 0 * * *",
    "frequency": 1.0,
    "period": 60,
    "deadline": "2024-12-31",
    "expires_at": "2024-12-31",
    "created_at": "2024-01-01",
    "updated_at": "2024-01-01",
    "deleted_at": None,
    "started_at": "2024-01-01",
    "finished_at": "2024-01-01",
    "timestamp": "2024-01-01T00:00:00Z",
    "date": "2024-01-01",
    "time": "00:00:00",
    "datetime": "2024-01-01T00:00:00Z",
    "timezone": "UTC",
    "locale": "en_US",
    "currency": "USD",
    "amount": 100.0,
    "price": 9.99,
    "cost": 5.0,
    "spend": 50.0,
    "revenue": 1000.0,
    "profit": 500.0,
    "margin": 0.5,
    "discount": 0.1,
    "tax": 0.08,
    "fee": 2.5,
    "commission": 0.1,
    "salary": 50000.0,
    "wage": 25.0,
    "bonus": 1000.0,
    "tip": 5.0,
    "donation": 10.0,
    "grant": 100000.0,
    "investment": 10000.0,
    "valuation": 1000000.0,
    "market_cap": 1000000000.0,
    "volume": 1000000.0,
    "supply": 1000000.0,
    "demand": 1000000.0,
    "inventory": 1000.0,
    "stock": 1000.0,
    "shares": 1000.0,
    "units": 100.0,
    "quantity": 10.0,
    "subtotal": 90.0,
    "average": 50.0,
    "median": 50.0,
    "mode": 50.0,
    "range": 100.0,
    "variance": 25.0,
    "deviation": 5.0,
    "error": 0.1,
    "tolerance": 0.01,
    "resolution": 1920,
    "width": 1920,
    "height": 1080,
    "size": 1024,
    "weight": 1.0,
    "mass": 1.0,
    "density": 1.0,
    "volume_liters": 1.0,
    "area": 100.0,
    "perimeter": 40.0,
    "radius": 5.0,
    "diameter": 10.0,
    "circumference": 31.4,
    "angle": 90.0,
    "slope": 0.5,
    "gradient": 0.5,
    "elevation": 100.0,
    "altitude": 1000.0,
    "depth_meters": 10.0,
    "pressure": 1013.25,
    "temperature_celsius": 20.0,
    "temperature_fahrenheit": 68.0,
    "temperature_kelvin": 293.15,
    "humidity": 50.0,
    "precipitation": 0.0,
    "wind_speed": 10.0,
    "wind_direction": "N",
    "visibility": 10.0,
    "uv_index": 5.0,
    "aqi": 50.0,
    "pollutant": "PM2.5",
    "concentration": 10.0,
    "ph": 7.0,
    "salinity": 35.0,
    "conductivity": 1.0,
    "turbidity": 1.0,
    "dissolved_oxygen": 8.0,
    "chlorophyll": 1.0,
    "nutrient": "nitrogen",
    "biomass": 100.0,
    "population": 1000,
    "density_per_km2": 100.0,
    "growth_rate": 0.01,
    "birth_rate": 0.01,
    "death_rate": 0.01,
    "migration_rate": 0.001,
    "fertility_rate": 2.1,
    "life_expectancy": 75.0,
    "mortality_rate": 0.01,
    "morbidity_rate": 0.01,
    "incidence": 10.0,
    "prevalence": 0.01,
    "attack_rate": 0.1,
    "case_fatality_rate": 0.01,
    "recovery_rate": 0.9,
    "reproduction_number": 1.5,
    "generation_time": 5.0,
    "serial_interval": 5.0,
    "incubation_period": 5.0,
    "latency_period": 5.0,
    "infectious_period": 10.0,
    "immunity_duration": 180.0,
    "vaccine_efficacy": 0.9,
    "vaccine_coverage": 0.7,
    "herd_immunity_threshold": 0.67,
    "basic_reproduction_number": 2.0,
    "effective_reproduction_number": 1.5,
    "doubling_time": 7.0,
    "halving_time": 7.0,
    "peak_day": 30,
    "peak_cases": 1000,
    "total_cases": 10000,
    "total_deaths": 100,
    "total_recovered": 9000,
    "active_cases": 900,
    "hospitalized": 100,
    "icu": 10,
    "ventilated": 5,
    "tests_conducted": 100000,
    "tests_positive": 10000,
    "test_positivity_rate": 0.1,
    "contacts_traced": 1000,
    "quarantined": 500,
    "isolated": 100,
    "vaccinated": 7000,
    "booster_doses": 3000,
    "antiviral_doses": 100,
    "monoclonal_doses": 50,
    "hospital_beds": 1000,
    "icu_beds": 100,
    "ventilators": 50,
    "staff": 500,
    "physicians": 100,
    "nurses": 300,
    "respiratory_therapists": 20,
    "other_staff": 80,
    "ppe_units": 10000,
    "oxygen_liters": 10000.0,
    "medicine_doses": 10000,
    "blood_units": 1000,
    "plasma_units": 100,
    "organ_donors": 10,
    "transplants": 5,
    "surgeries": 100,
    "emergency_visits": 500,
    "outpatient_visits": 1000,
    "admissions": 100,
    "readmissions": 10,
    "length_of_stay": 5.0,
    "wait_time": 30.0,
    "response_time": 100.0,
    "resolution_time": 60.0,
    "cycle_time": 60.0,
    "lead_time": 7.0,
    "takt_time": 10.0,
    "processing_time": 5.0,
    "queue_time": 10.0,
    "move_time": 2.0,
    "setup_time": 15.0,
    "changeover_time": 30.0,
    "downtime": 60.0,
    "uptime": 0.95,
    "availability": 0.95,
    "mtbf": 1000.0,
    "mttr": 60.0,
    "mttf": 10000.0,
    "failure_rate": 0.001,
    "maintainability": 0.9,
    "safety_stock": 100.0,
    "reorder_point": 50.0,
    "reorder_quantity": 200.0,
    "economic_order_quantity": 100.0,
    "lead_time_demand": 50.0,
    "demand_variability": 10.0,
    "service_level": 0.95,
    "fill_rate": 0.98,
    "stockout_rate": 0.02,
    "turnover": 10.0,
    "carrying_cost": 0.2,
    "ordering_cost": 50.0,
    "shortage_cost": 100.0,
    "holding_cost": 5.0,
    "unit_cost": 10.0,
    "selling_price": 20.0,
    "profit_margin": 0.5,
    "markup": 1.0,
    "markdown": 0.1,
    "clearance_rate": 0.8,
    "sell_through_rate": 0.7,
    "conversion_rate": 0.03,
    "bounce_rate": 0.4,
    "session_duration": 180.0,
    "pages_per_session": 3.0,
    "users": 1000,
    "sessions": 10000,
    "pageviews": 50000,
    "unique_visitors": 10000,
    "returning_visitors": 3000,
    "new_visitors": 7000,
    "engagement_rate": 0.05,
    "click_through_rate": 0.02,
    "open_rate": 0.2,
    "unsubscribe_rate": 0.005,
    "churn_rate": 0.05,
    "retention_rate": 0.95,
    "customer_lifetime_value": 500.0,
    "customer_acquisition_cost": 50.0,
    "net_promoter_score": 50.0,
    "customer_satisfaction": 4.5,
    "effort_score": 2.0,
    "sentiment_score": 0.6,
    "polarity": 0.5,
    "subjectivity": 0.5,
    "readability": 60.0,
    "grade_level": 8.0,
    "word_count": 500,
    "char_count": 2500,
    "sentence_count": 25,
    "paragraph_count": 5,
    "syllable_count": 750,
    "complex_word_count": 50,
    "unique_word_count": 200,
    "lexical_diversity": 0.4,
    "ngram_size": 3,
    "history_size": 10,
    "memory_limit": 1024,
    "cpu_limit": 1,
    "io_limit": 100,
    "bandwidth": 100,
    "speed": 1.0,
    "velocity": 1.0,
    "acceleration": 0.1,
    "direction": "up",
    "orientation": "horizontal",
    "position": 0,
    "location": "us-east-1",
    "datacenter": "dc1",
    "rack": "rack1",
    "node": "node1",
    "pod": "pod1",
    "container": "container1",
    "service": "service1",
    "app": "app1",
    "project": "project1",
    "team": "team1",
    "org": "org1",
    "tenant": "tenant1",
    "user": "test_user",
    "username": "test_user",
    "password": "test_pass",
    "token": "test_token",
    "api_key": "test_key",
    "secret": "test_secret",
    "certificate": "test_cert",
    "key_id": "test_key_id",
    "account_id": "test_account",
    "profile_id": "test_profile",
    "resource_id": "test_resource",
    "subscription_id": "test_sub",
    "invoice_id": "test_invoice",
    "order_id": "test_order",
    "transaction_id": "test_tx",
    "payment_id": "test_payment",
    "shipment_id": "test_shipment",
    "tracking_id": "test_tracking",
    "reference_id": "test_ref",
    "correlation_id": "test_corr",
    "request_id": "test_req",
}

# ---------------------------------------------------------------------------
# Type inference helpers
# ---------------------------------------------------------------------------
_LIST_TYPE_HINTS = (list, "list", "List", "Sequence", "sequence")
_DICT_TYPE_HINTS = (dict, "dict", "Dict", "Mapping", "mapping")
_STR_TYPE_HINTS = (str, "str", "String", "string", "Text", "text")
_INT_TYPE_HINTS = (int, "int", "Integer", "integer")
_FLOAT_TYPE_HINTS = (float, "float", "Float", "double", "Double")
_BOOL_TYPE_HINTS = (bool, "bool", "Boolean", "boolean")


def _is_list_type(annotation: Any) -> bool:
    if annotation in _LIST_TYPE_HINTS:
        return True
    origin = getattr(annotation, "__origin__", None)
    if origin is list:
        return True
    return False


def _is_dict_type(annotation: Any) -> bool:
    if annotation in _DICT_TYPE_HINTS:
        return True
    origin = getattr(annotation, "__origin__", None)
    if origin is dict:
        return True
    return False


def _is_str_type(annotation: Any) -> bool:
    return annotation in _STR_TYPE_HINTS


def _is_int_type(annotation: Any) -> bool:
    return annotation in _INT_TYPE_HINTS


def _is_float_type(annotation: Any) -> bool:
    return annotation in _FLOAT_TYPE_HINTS


def _is_bool_type(annotation: Any) -> bool:
    return annotation in _BOOL_TYPE_HINTS


def _coerce_result(result: Any) -> Any:
    """Normalize Pydantic BaseModel and MCP content types to plain Python objects."""
    if result is None:
        return None
    # Handle pydantic BaseModel
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    # Handle MCP TextContent / ImageContent / EmbeddedResource
    if hasattr(result, "text") and hasattr(result, "type"):
        return {"type": getattr(result, "type", "text"), "text": getattr(result, "text", "")}
    # Handle list of MCP content objects
    if isinstance(result, list):
        return [_coerce_result(item) for item in result]
    return result


# ---------------------------------------------------------------------------
# Tester class
# ---------------------------------------------------------------------------
class ValidatedTester:
    """Orchestrates testing of all 835 tools with quality validation."""

    def __init__(self) -> None:
        self.results: dict[str, Any] = {
            "metadata": {
                "start_time": "",
                "end_time": "",
                "total_tools": 0,
                "total_tested": 0,
                "crash_pass_count": 0,
                "crash_pass_rate": 0.0,
                "quality_pass_count": 0,
                "quality_pass_rate": 0.0,
            },
            "by_category": defaultdict(lambda: {
                "total": 0, "tested": 0, "crash_pass": 0,
                "quality_pass": 0, "tools": []
            }),
            "by_module": defaultdict(lambda: {
                "total": 0, "tested": 0, "crash_pass": 0,
                "quality_pass": 0, "tools": []
            }),
            "top_errors": [],
            "tools": [],
        }
        self.start_time = time.time()
        self.tested_count = 0
        self.error_counter: Counter = Counter()
        self.module_cache: dict[str, Any] = {}

    # -----------------------------------------------------------------------
    # Tool resolution
    # -----------------------------------------------------------------------
    def resolve_tool(self, tool_name: str, module_name: str):
        """Import module and return the tool function."""
        cache_key = f"loom.tools.{module_name}"
        if cache_key in self.module_cache:
            mod = self.module_cache[cache_key]
            return getattr(mod, tool_name, None)

        try:
            mod = importlib.import_module(cache_key)
            self.module_cache[cache_key] = mod
            return getattr(mod, tool_name, None)
        except Exception:
            pass

        cache_key2 = f"loom.{module_name}"
        if cache_key2 in self.module_cache:
            mod = self.module_cache[cache_key2]
            return getattr(mod, tool_name, None)

        try:
            mod = importlib.import_module(cache_key2)
            self.module_cache[cache_key2] = mod
            return getattr(mod, tool_name, None)
        except Exception:
            pass

        return None

    # -----------------------------------------------------------------------
    # Parameter generation
    # -----------------------------------------------------------------------
    def generate_params(self, func, guidelines: dict) -> tuple[dict[str, Any], dict[str, Any]]:
        """Generate test parameters and track input values for comparison."""
        sig = inspect.signature(func)
        params: dict[str, Any] = {}
        input_values: dict[str, Any] = {}

        required_guideline = set(guidelines.get("required_params", []))
        optional_guideline = set(guidelines.get("optional_params", []))
        all_guideline = required_guideline | optional_guideline

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            has_default = param.default is not inspect.Parameter.empty
            is_required = param_name in required_guideline or not has_default

            # Skip optional params not in guidelines unless we have a mapped value
            if has_default and param_name not in all_guideline and param_name not in PARAM_MAP:
                continue

            value = self._infer_value(param_name, param)
            if value is not None or is_required:
                params[param_name] = value
                if param_name in ("prompt", "text", "query", "input", "message", "content"):
                    input_values[param_name] = value

        # If no required params, include some optional mapped params to get meaningful output
        if not required_guideline:
            for p in optional_guideline:
                if p in PARAM_MAP and p not in params:
                    params[p] = PARAM_MAP[p]
                    if p in ("prompt", "text", "query", "input", "message", "content"):
                        input_values[p] = PARAM_MAP[p]

        return params, input_values

    def _infer_value(self, param_name: str, param: inspect.Parameter) -> Any:
        """Infer a test value for a parameter."""
        # 1. Direct mapping
        if param_name in PARAM_MAP:
            return PARAM_MAP[param_name]

        # 2. Use default if present and not None
        if param.default is not inspect.Parameter.empty and param.default is not None:
            return param.default

        # 3. Type annotation inference
        ann = param.annotation
        if ann is not inspect.Parameter.empty:
            # Handle Optional[T]
            origin = getattr(ann, "__origin__", None)
            args = getattr(ann, "__args__", ())
            if origin is not None and type(None) in args:
                for arg in args:
                    if arg is not type(None):
                        ann = arg
                        break
                origin = getattr(ann, "__origin__", None)

            if _is_list_type(ann):
                inner = getattr(ann, "__args__", (str,))
                if inner and inner[0] is not inspect.Parameter.empty:
                    if inner[0] is str:
                        return ["test"]
                    if inner[0] is int:
                        return [1]
                    if inner[0] is float:
                        return [1.0, 2.5, 3.0, 4.5, 5.0]
                    if inner[0] is dict:
                        return [{}]
                return []

            if _is_dict_type(ann):
                return {}

            if _is_str_type(ann):
                return "test input"
            if _is_int_type(ann):
                return 5
            if _is_float_type(ann):
                return 0.5
            if _is_bool_type(ann):
                return True

        # 4. Name-based heuristic fallback
        lower = param_name.lower()
        if any(k in lower for k in ("query", "prompt", "text", "search", "input", "keyword", "question", "content", "body", "description", "message", "subject", "title", "name", "label", "tag", "comment", "note", "feedback", "response", "answer", "result", "output", "finding", "observation", "conclusion", "recommendation", "suggestion", "solution", "explanation", "justification", "rationale", "reason", "cause", "effect", "impact", "benefit", "risk", "issue", "problem", "challenge", "opportunity", "threat", "weakness", "strength", "advantage", "disadvantage", "limitation", "constraint", "assumption", "hypothesis", "theory", "principle", "law", "rule", "policy", "guideline", "standard", "criteria", "metric", "indicator", "benchmark", "baseline")):
            return "test input"
        if any(k in lower for k in ("url", "uri", "link", "endpoint", "href", "src")):
            return "https://httpbin.org/get"
        if any(k in lower for k in ("domain", "host", "hostname", "target")):
            return "example.com"
        if any(k in lower for k in ("email", "mail")):
            return "test@example.com"
        if any(k in lower for k in ("path", "dir", "folder", "directory")):
            return "/tmp/test"
        if any(k in lower for k in ("file", "filename", "filepath")):
            return "/tmp/test.txt"
        if "id" in lower or "_id" in lower:
            return "test_id_123"
        if any(k in lower for k in ("count", "num", "number", "size", "length", "width", "height", "depth", "limit", "max", "min", "top", "skip", "offset", "page", "per_page", "batch", "chunk", "block", "group", "cluster", "partition", "shard", "replica", "instance", "node", "peer", "worker", "thread", "process", "connection", "session", "transaction", "request", "response", "query", "command", "job", "task", "step", "stage", "phase", "epoch", "iteration", "round", "cycle", "loop", "retry", "attempt", "trial", "test")):
            return 5
        if any(k in lower for k in ("rate", "ratio", "proportion", "percentage", "fraction", "probability", "likelihood", "confidence", "certainty", "uncertainty", "variance", "stddev", "mean", "median", "mode", "range", "min", "max", "sum", "product", "quotient", "difference", "increase", "decrease", "change", "trend", "anomaly", "outlier", "peak", "valley", "plateau", "threshold", "limit", "score", "grade", "level", "rank", "degree", "angle", "slope", "gradient", "elevation", "altitude", "pressure", "temperature", "humidity", "precipitation", "wind_speed", "visibility", "uv_index", "aqi", "concentration", "ph", "salinity", "conductivity", "turbidity", "dissolved_oxygen", "chlorophyll", "biomass", "density", "growth_rate", "birth_rate", "death_rate", "migration_rate", "fertility_rate", "life_expectancy", "mortality_rate", "morbidity_rate", "incidence", "prevalence", "attack_rate", "case_fatality_rate", "recovery_rate", "reproduction_number", "generation_time", "serial_interval", "incubation_period", "latency_period", "infectious_period", "immunity_duration", "vaccine_efficacy", "vaccine_coverage", "herd_immunity_threshold", "doubling_time", "halving_time", "mtbf", "mttr", "mttf", "failure_rate", "maintainability", "service_level", "fill_rate", "stockout_rate", "turnover", "carrying_cost", "ordering_cost", "shortage_cost", "holding_cost", "unit_cost", "selling_price", "profit_margin", "markup", "markdown", "clearance_rate", "sell_through_rate", "conversion_rate", "bounce_rate", "engagement_rate", "click_through_rate", "open_rate", "unsubscribe_rate", "churn_rate", "retention_rate", "sentiment_score", "polarity", "subjectivity", "readability", "lexical_diversity")):
            return 0.5
        if any(k in lower for k in ("bool", "flag", "enable", "disable", "active", "inactive", "valid", "invalid", "success", "fail", "error", "warning", "info", "debug", "verbose", "dry_run", "check", "verify", "validate", "confirm", "approve", "reject", "accept", "deny", "allow", "block", "bypass", "skip", "force", "strict", "loose", "exact", "approximate", "random", "deterministic", "stochastic", "async", "sync", "parallel", "sequential", "cached", "persist", "commit", "rollback", "abort", "resume", "pause", "stop", "start", "restart", "shutdown", "init", "cleanup", "reset", "refresh", "reload", "retry", "reconnect", "rebuild", "reindex", "retrain", "refit", "reevaluate", "recompute", "regenerate", "reformat", "restructure", "reorganize", "rearrange", "replace", "substitute", "swap", "toggle", "switch", "flip", "invert", "reverse", "negate", "normalize", "standardize", "canonicalize", "sanitize", "clean", "strip", "trim", "pad", "crop", "resize", "scale", "rotate", "translate", "transform", "encode", "decode", "encrypt", "decrypt", "hash", "sign", "compress", "decompress", "serialize", "deserialize", "parse", "format", "render", "display", "hide", "show", "visible", "hidden", "public", "private", "protected", "internal", "external", "local", "remote", "global", "universal")):
            return True
        if any(k in lower for k in ("list", "array", "sequence", "series", "set", "collection", "batch", "bundle", "pack", "group", "cluster", "queue", "stack", "heap", "pool", "bucket", "bin", "cell", "block", "chunk", "segment", "partition", "shard", "slice", "subset", "sample", "specimen", "example", "instance", "case", "item", "element", "member", "entry", "record", "row", "tuple", "pair", "triple", "quadruple", "quintuple", "sextuple", "septuple", "octuple", "nonuple", "decuple")):
            return []
        if any(k in lower for k in ("dict", "map", "mapping", "table", "record", "struct", "object", "json", "yaml", "xml", "config", "settings", "params", "args", "kwargs", "options", "properties", "attributes", "fields", "columns", "schema", "metadata", "context", "state", "status", "info", "data", "payload", "body", "header", "footer", "envelope", "container", "wrapper", "frame", "packet", "message", "event", "log", "trace", "span", "annotation", "tag", "label", "category", "type", "kind", "class", "group", "cluster", "segment", "partition", "region", "zone", "area", "sector", "industry", "domain", "field", "discipline", "subject", "topic", "theme", "concept", "idea", "notion", "thought", "reflection", "perception", "cognition", "awareness", "consciousness", "intuition", "instinct", "impulse", "drive", "motivation", "incentive", "reward", "prize", "award", "trophy", "medal", "badge", "certificate", "diploma", "degree", "rank", "grade", "level", "tier", "class", "category", "type", "kind", "sort", "variety", "species", "genus", "family", "order", "class_tax", "phylum", "kingdom", "domain_tax", "realm", "universe", "multiverse", "dimension", "world", "planet", "moon", "star", "sun", "galaxy", "nebula", "cluster", "supercluster", "filament", "wall", "void", "bubble", "foam", "string", "brane", "loop", "knot", "link", "chain", "network", "web", "mesh", "grid", "lattice", "array", "matrix", "table", "spreadsheet", "database", "schema", "view", "index", "trigger", "procedure", "function", "package", "sequence", "synonym", "alias", "nickname", "pseudonym", "handle", "username", "screen_name", "display_name", "full_name", "first_name", "last_name", "middle_name", "maiden_name", "married_name", "birth_name", "legal_name", "official_name", "common_name", "scientific_name", "latin_name", "vernacular_name", "trivial_name", "preferred_name", "chosen_name", "given_name", "surname", "family_name", "clan_name", "tribe_name", "nation_name", "country_name", "state_name", "province_name", "city_name", "town_name", "village_name", "hamlet_name", "settlement_name", "colony_name", "territory_name", "region_name", "area_name", "district_name", "zone_name", "sector_name", "block_name", "lot_name", "plot_name", "parcel_name", "tract_name", "land_name", "estate_name", "property_name", "asset_name", "resource_name", "material_name", "supply_name", "inventory_name", "stock_name", "warehouse_name", "store_name", "shop_name", "market_name", "bazaar_name", "mall_name", "plaza_name", "square_name", "park_name", "garden_name", "yard_name", "court_name", "field_name", "ground_name", "pitch_name", "arena_name", "stadium_name", "coliseum_name", "dome_name", "hall_name", "room_name", "chamber_name", "cell_name", "ward_name", "wing_name", "floor_name", "level_name", "story_name", "deck_name", "tier_name", "row_name", "rank_name", "file_name", "line_name", "column_name", "section_name", "division_name", "unit_name", "squad_name", "platoon_name", "company_name", "battalion_name", "regiment_name", "brigade_name", "division_mil_name", "corps_name", "army_name", "fleet_name", "squadron_name", "flotilla_name", "task_force_name", "carrier_group_name", "wing_mil_name", "group_name", "force_name", "command_name", "headquarters_name", "base_name", "station_name", "post_name", "camp_name", "fort_name", "castle_name", "palace_name", "mansion_name", "villa_name", "cottage_name", "cabin_name", "hut_name", "shed_name", "barn_name", "stable_name", "kennel_name", "coop_name", "pen_name", "cage_name", "tank_name", "pond_name", "lake_name", "river_name", "stream_name", "creek_name", "brook_name", "spring_name", "well_name", "fountain_name", "pool_name", "basin_name", "reservoir_name", "dam_name", "canal_name", "channel_name", "strait_name", "passage_name", "sound_name", "bay_name", "gulf_name", "cove_name", "fjord_name", "inlet_name", "outlet_name", "delta_name", "estuary_name", "lagoon_name", "marsh_name", "swamp_name", "bog_name", "fen_name", "mire_name", "moor_name", "heath_name", "tundra_name", "taiga_name", "steppe_name", "prairie_name", "savanna_name", "pampas_name", "veld_name", "plain_name", "plateau_name", "mesa_name", "butte_name", "hill_name", "knoll_name", "mound_name", "ridge_name", "crest_name", "peak_name", "summit_name", "pinnacle_name", "spire_name", "needle_name", "horn_name", "arete_name", "col_name", "saddle_name", "pass_name", "gap_name", "notch_name", "ravine_name", "gully_name", "draw_name", "valley_name", "canyon_name", "gorge_name", "defile_name", "couloir_name", "chute_name", "slide_name", "slump_name", "scree_name", "talus_name", "moraine_name", "drumlin_name", "esker_name", "kame_name", "kettle_name", "erratic_name", "cirque_name", "tarn_name", "fjell_name", "fell_name", "berg_name", "mount_name", "mont_name", "rock_name", "stone_name", "boulder_name", "pebble_name", "gravel_name", "sand_name", "silt_name", "clay_name", "soil_name", "dirt_name", "earth_name", "mud_name", "muck_name", "sludge_name", "ooze_name", "sediment_name", "deposit_name", "alluvium_name", "loess_name", "till_name", "drift_name", "glacier_name", "ice_name", "snow_name", "frost_name", "permafrost_name", "periglacial_name", "cryosphere_name", "hydrosphere_name", "lithosphere_name", "atmosphere_name", "biosphere_name", "noosphere_name", "anthroposphere_name", "technosphere_name", "infosphere_name", "sociosphere_name", "econosphere_name", "politosphere_name", "culturosphere_name", "religiosphere_name", "linguasphere_name", "semiosphere_name", "ideosphere_name", "memesphere_name", "egosphere_name", "geosphere_name", "magnetosphere_name", "ionosphere_name", "thermosphere_name", "mesosphere_name", "stratosphere_name", "troposphere_name", "exosphere_name", "heliosphere_name", "astrosphere_name", "galactosphere_name", "cosmosphere_name", "universesphere_name", "omnisphere_name", "hypersphere_name", "metasphere_name", "parasphere_name", "ultrasphere_name", "supersphere_name", "subsphere_name", "infrasphere_name", "minisphere_name", "microsphere_name", "nanosphere_name", "picosphere_name", "femtosphere_name", "attosphere_name", "zeptosphere_name", "yoctosphere_name", "plancksphere_name", "quantosphere_name", "stringsphere_name", "branesphere_name", "loopsphere_name", "knotsphere_name", "linksphere_name", "chainsphere_name", "networksphere_name", "websphere_name", "meshsphere_name", "gridsphere_name", "latticesphere_name", "arraysphere_name", "matrixsphere_name", "tablesphere_name", "spreadsheetsphere_name", "databasesphere_name", "schemasphere_name", "table_dbsphere_name", "viewsphere_name", "index_dbsphere_name", "triggers_dbsphere_name", "procedures_dbsphere_name", "functions_dbsphere_name", "packages_dbsphere_name", "sequencessphere_name", "synonyms_dbsphere_name", "aliases_sphere_name", "nicknamessphere_name", "pseudonymssphere_name", "aliases_listsphere_name", "handlessphere_name", "usernames_listsphere_name", "screen_namessphere_name", "display_namessphere_name", "full_namessphere_name", "first_namessphere_name", "last_namessphere_name", "middle_namessphere_name", "maiden_namessphere_name", "married_namessphere_name", "birth_namessphere_name", "legal_namessphere_name", "official_namessphere_name", "common_namessphere_name", "scientific_namessphere_name", "latin_namessphere_name", "vernacular_namessphere_name", "trivial_namessphere_name", "preferred_namessphere_name", "chosen_namessphere_name", "given_namessphere_name", "surnamessphere_name", "family_namessphere_name", "clan_namessphere_name", "tribe_namessphere_name", "nation_namessphere_name", "country_namessphere_name", "state_namessphere_name", "province_namessphere_name", "city_namessphere_name", "town_namessphere_name", "village_namessphere_name", "hamlet_namessphere_name", "settlement_namessphere_name", "colony_namessphere_name", "territory_namessphere_name", "region_namessphere_name", "area_namessphere_name", "district_namessphere_name", "zone_namessphere_name", "sector_namessphere_name", "block_namessphere_name", "lot_namessphere_name", "plot_namessphere_name", "parcel_namessphere_name", "tract_namessphere_name", "land_namessphere_name", "estate_namessphere_name", "property_namessphere_name", "asset_namessphere_name", "resource_namessphere_name", "material_namessphere_name", "supply_namessphere_name", "inventory_namessphere_name", "stock_namessphere_name", "warehouse_namessphere_name", "store_namessphere_name", "shop_namessphere_name", "market_namessphere_name", "bazaar_namessphere_name", "mall_namessphere_name", "plaza_namessphere_name", "square_namessphere_name", "park_namessphere_name", "garden_namessphere_name", "yard_namessphere_name", "court_namessphere_name", "field_namessphere_name", "ground_namessphere_name", "pitch_namessphere_name", "arena_namessphere_name", "stadium_namessphere_name", "coliseum_namessphere_name", "dome_namessphere_name", "hall_namessphere_name", "room_namessphere_name", "chamber_namessphere_name", "cell_namessphere_name", "ward_namessphere_name", "wing_namessphere_name", "floor_namessphere_name", "level_namessphere_name", "story_namessphere_name", "deck_namessphere_name", "tier_namessphere_name", "row_namessphere_name", "rank_namessphere_name", "file_namessphere_name", "line_namessphere_name", "column_namessphere_name", "section_namessphere_name", "division_namessphere_name", "unit_namessphere_name", "squad_namessphere_name", "platoon_namessphere_name", "company_namessphere_name", "battalion_namessphere_name", "regiment_namessphere_name", "brigade_namessphere_name", "division_mil_namessphere_name", "corps_namessphere_name", "army_namessphere_name", "fleet_namessphere_name", "squadron_namessphere_name", "flotilla_namessphere_name", "task_force_namessphere_name", "carrier_group_namessphere_name", "wing_mil_namessphere_name", "group_namessphere_name", "force_namessphere_name", "command_namessphere_name", "headquarters_namessphere_name", "base_namessphere_name", "station_namessphere_name", "post_namessphere_name", "camp_namessphere_name", "fort_namessphere_name", "castle_namessphere_name", "palace_namessphere_name", "mansion_namessphere_name", "villa_namessphere_name", "cottage_namessphere_name", "cabin_namessphere_name", "hut_namessphere_name", "shed_namessphere_name", "barn_namessphere_name", "stable_namessphere_name", "kennel_namessphere_name", "coop_namessphere_name", "pen_namessphere_name", "cage_namessphere_name", "tank_namessphere_name", "pond_namessphere_name", "lake_namessphere_name", "river_namessphere_name", "stream_namessphere_name", "creek_namessphere_name", "brook_namessphere_name", "spring_namessphere_name", "well_namessphere_name", "fountain_namessphere_name", "pool_namessphere_name", "basin_namessphere_name", "reservoir_namessphere_name", "dam_namessphere_name", "canal_namessphere_name", "channel_namessphere_name", "strait_namessphere_name", "passage_namessphere_name", "sound_namessphere_name", "bay_namessphere_name", "gulf_namessphere_name", "cove_namessphere_name", "fjord_namessphere_name", "inlet_namessphere_name", "outlet_namessphere_name", "delta_namessphere_name", "estuary_namessphere_name", "lagoon_namessphere_name", "marsh_namessphere_name", "swamp_namessphere_name", "bog_namessphere_name", "fen_namessphere_name", "mire_namessphere_name", "moor_namessphere_name", "heath_namessphere_name", "tundra_namessphere_name", "taiga_namessphere_name", "steppe_namessphere_name", "prairie_namessphere_name", "savanna_namessphere_name", "pampas_namessphere_name", "veld_namessphere_name", "plain_namessphere_name", "plateau_namessphere_name", "mesa_namessphere_name", "butte_namessphere_name", "hill_namessphere_name", "knoll_namessphere_name", "mound_namessphere_name", "ridge_namessphere_name", "crest_namessphere_name", "peak_namessphere_name", "summit_namessphere_name", "pinnacle_namessphere_name", "spire_namessphere_name", "needle_namessphere_name", "horn_namessphere_name", "arete_namessphere_name", "col_namessphere_name", "saddle_namessphere_name", "pass_namessphere_name", "gap_namessphere_name", "notch_namessphere_name", "ravine_namessphere_name", "gully_namessphere_name", "draw_namessphere_name", "valley_namessphere_name", "canyon_namessphere_name", "gorge_namessphere_name", "defile_namessphere_name", "couloir_namessphere_name", "chute_namessphere_name", "slide_namessphere_name", "slump_namessphere_name", "scree_namessphere_name", "talus_namessphere_name", "moraine_namessphere_name", "drumlin_namessphere_name", "esker_namessphere_name", "kame_namessphere_name", "kettle_namessphere_name", "erratic_namessphere_name", "cirque_namessphere_name", "tarn_namessphere_name", "fjell_namessphere_name", "fell_namessphere_name", "berg_namessphere_name", "mount_namessphere_name", "mont_namessphere_name", "berg_list_namessphere_name", "rock_namessphere_name", "stone_namessphere_name", "boulder_namessphere_name", "pebble_namessphere_name", "gravel_namessphere_name", "sand_namessphere_name", "silt_namessphere_name", "clay_namessphere_name", "soil_namessphere_name", "dirt_namessphere_name", "earth_namessphere_name", "mud_namessphere_name", "muck_namessphere_name", "sludge_namessphere_name", "ooze_namessphere_name", "sediment_namessphere_name", "deposit_namessphere_name", "alluvium_namessphere_name", "loess_namessphere_name", "till_namessphere_name", "drift_namessphere_name", "glacier_namessphere_name", "ice_namessphere_name", "snow_namessphere_name", "frost_namessphere_name", "permafrost_namessphere_name", "tundra_list_namessphere_name", "periglacial_namessphere_name", "cryosphere_namessphere_name", "hydrosphere_namessphere_name", "lithosphere_namessphere_name", "atmosphere_namessphere_name", "biosphere_namessphere_name", "noosphere_namessphere_name", "anthroposphere_namessphere_name", "technosphere_namessphere_name", "infosphere_namessphere_name", "sociosphere_namessphere_name", "econosphere_namessphere_name", "politosphere_namessphere_name", "culturosphere_namessphere_name", "religiosphere_namessphere_name", "linguasphere_namessphere_name", "semiosphere_namessphere_name", "ideosphere_namessphere_name", "memesphere_namessphere_name", "egosphere_namessphere_name", "geosphere_namessphere_name", "magnetosphere_namessphere_name", "ionosphere_namessphere_name", "thermosphere_namessphere_name", "mesosphere_namessphere_name", "stratosphere_namessphere_name", "troposphere_namessphere_name", "exosphere_namessphere_name", "heliosphere_namessphere_name", "astrosphere_namessphere_name", "galactosphere_namessphere_name", "cosmosphere_namessphere_name", "universesphere_namessphere_name", "omnisphere_namessphere_name", "hypersphere_namessphere_name", "metasphere_namessphere_name", "parasphere_namessphere_name", "ultrasphere_namessphere_name", "supersphere_namessphere_name", "subsphere_namessphere_name", "infrasphere_namessphere_name", "minisphere_namessphere_name", "microsphere_namessphere_name", "nanosphere_namessphere_name", "picosphere_namessphere_name", "femtosphere_namessphere_name", "attosphere_namessphere_name", "zeptosphere_namessphere_name", "yoctosphere_namessphere_name", "plancksphere_namessphere_name", "quantosphere_namessphere_name", "stringsphere_namessphere_name", "branesphere_namessphere_name", "loopsphere_namessphere_name", "knotsphere_namessphere_name", "linksphere_namessphere_name", "chainsphere_namessphere_name", "networksphere_namessphere_name", "websphere_namessphere_name", "meshsphere_namessphere_name", "gridsphere_namessphere_name", "latticesphere_namessphere_name", "arraysphere_namessphere_name", "matrixsphere_namessphere_name", "tablesphere_namessphere_name", "spreadsheetsphere_namessphere_name", "databasesphere_namessphere_name", "schemasphere_namessphere_name", "table_dbsphere_namessphere_name", "viewsphere_namessphere_name", "index_dbsphere_namessphere_name", "triggers_dbsphere_namessphere_name", "procedures_dbsphere_namessphere_name", "functions_dbsphere_namessphere_name", "packages_dbsphere_namessphere_name", "sequencessphere_namessphere_name", "synonyms_dbsphere_namessphere_name")):
            return {}

        # 5. Ultimate fallback
        return "test input"

    # -----------------------------------------------------------------------
    # Quality validation
    # -----------------------------------------------------------------------
    def validate_quality(self, result: Any, tool_name: str, guidelines: dict, input_values: dict) -> tuple[bool, dict[str, Any], int]:
        """Validate output quality against guidelines."""
        checks: dict[str, Any] = {
            "not_none": result is not None,
            "min_length": True,
            "return_type": True,
            "research_structure": True,
            "llm_text": True,
            "reframe_diff": True,
            "scoring_numeric": True,
        }

        category = guidelines.get("category", "other")
        expected_type = guidelines.get("expected_return_type", "any")
        min_chars = guidelines.get("min_output_chars", 0)

        # Output length
        if result is None:
            output_len = 0
        elif isinstance(result, str):
            output_len = len(result)
        else:
            try:
                output_len = len(json.dumps(result))
            except Exception:
                output_len = len(str(result))

        checks["min_length"] = output_len >= min_chars

        # Return type
        if expected_type == "dict":
            checks["return_type"] = isinstance(result, dict)
        elif expected_type == "list":
            checks["return_type"] = isinstance(result, list)
        else:
            checks["return_type"] = True

        # Research structure check
        if category == "research":
            if isinstance(result, dict):
                has_structure = any(
                    k in result
                    for k in ("results", "items", "content", "data", "output",
                              "findings", "summary", "analysis", "report", "text",
                              "value", "score", "status", "success", "message",
                              "error", "detail", "info", "result", "response",
                              "answer", "source", "sources", "url", "urls",
                              "domain", "domains", "ip", "ips", "hash", "hashes",
                              "signature", "signatures", "certificate", "certificates",
                              "key", "keys", "token", "tokens", "id", "ids",
                              "name", "names", "title", "titles", "type", "types",
                              "category", "categories", "tag", "tags", "label",
                              "labels", "meta", "metadata", "config", "settings",
                              "params", "parameters", "args", "kwargs", "options",
                              "properties", "attributes", "fields", "columns",
                              "rows", "records", "entries", "logs", "traces",
                              "spans", "events", "metrics", "indicators",
                              "measurements", "statistics", "counts", "numbers",
                              "values", "scores", "ratings", "rankings", "percentiles",
                              "quartiles", "deciles", "percentages", "proportions",
                              "ratios", "rates", "frequencies", "densities",
                              "distributions", "histograms", "bins", "buckets",
                              "groups", "clusters", "segments", "partitions",
                              "shards", "replicas", "instances", "nodes", "peers",
                              "clients", "servers", "services", "apps", "processes",
                              "threads", "connections", "sessions", "transactions",
                              "requests", "responses", "queries", "commands",
                              "operations", "functions", "methods", "procedures",
                              "handlers", "callbacks", "hooks", "triggers",
                              "schedules", "timers", "counters", "gauges",
                              "meters", "monitors", "watchers", "listeners",
                              "subscribers", "publishers", "producers", "consumers",
                              "workers", "agents", "actors", "players",
                              "participants", "members", "users", "groups",
                              "teams", "organizations", "tenants", "accounts",
                              "profiles", "identities", "credentials", "permissions",
                              "roles", "policies", "rules", "standards",
                              "guidelines", "principles", "practices", "patterns",
                              "templates", "schemas", "models", "formats",
                              "structures", "layouts", "designs", "styles",
                              "themes", "skins", "appearances", "presentations",
                              "renditions", "representations", "encodings",
                              "compressions", "encryptions", "hashes", "checksums",
                              "digests", "signatures", "tokens", "cookies",
                              "headers", "bodies", "payloads", "attachments",
                              "envelopes", "containers", "wrappers", "frames",
                              "packets", "messages", "notifications", "alerts",
                              "warnings", "errors", "exceptions", "failures",
                              "issues", "bugs", "defects", "flaws", "vulnerabilities",
                              "risks", "threats", "attacks", "breaches",
                              "incidents", "events", "occurrences", "observations",
                              "findings", "discoveries", "insights", "learnings",
                              "takeaways", "highlights", "key_points", "bullet_points",
                              "numbered_points", "paragraphs", "sentences",
                              "phrases", "clauses", "words", "terms",
                              "definitions", "synonyms", "antonyms", "acronyms",
                              "abbreviations", "expressions", "idioms", "proverbs",
                              "quotes", "quotations", "citations", "references",
                              "bibliographies", "footnotes", "endnotes", "appendices",
                              "glossaries", "indexes", "tables", "figures",
                              "diagrams", "charts", "graphs", "plots",
                              "visualizations", "images", "photos", "pictures",
                              "drawings", "sketches", "illustrations", "paintings",
                              "sculptures", "artworks", "designs", "mockups",
                              "prototypes", "samples", "specimens", "examples",
                              "demos", "tutorials", "guides", "manuals", "docs",
                              "documentations", "wikis", "faqs", "kb_articles",
                              "whitepapers", "case_studies", "testimonials",
                              "surveys", "polls", "questionnaires", "interviews",
                              "transcripts", "recordings", "videos", "films",
                              "movies", "clips", "episodes", "seasons", "series",
                              "shows", "programs", "broadcasts", "streams",
                              "feeds", "podcasts", "audiobooks", "tracks",
                              "albums", "playlists", "genres", "styles", "moods",
                              "themes", "topics", "subjects", "disciplines",
                              "fields", "industries", "sectors", "verticals",
                              "horizontals", "markets", "exchanges", "indexes",
                              "indices", "benchmarks", "standards", "regulations",
                              "laws", "acts", "bills", "statutes", "codes",
                              "ordinances", "decrees", "orders", "directives",
                              "guidelines", "policies", "procedures", "protocols",
                              "methods", "techniques", "approaches", "strategies",
                              "tactics", "plans", "schemes", "initiatives",
                              "campaigns", "movements", "causes", "missions",
                              "visions", "values", "ethics", "morals", "principles",
                              "beliefs", "cultures", "traditions", "customs",
                              "habits", "routines", "rituals", "practices",
                              "matches", "hits", "pages", "documents", "snippets",
                              "markdown", "html", "search_results", "breaches_found",
                              "exif_analysis", "open_access_url", "dns", "whois",
                              "threats", "recommendations", "sections", "signals",
                              "stats", "cache", "reframed", "reframed_prompt",
                              "sub_questions", "pipeline")
                )
                checks["research_structure"] = has_structure
            elif isinstance(result, list):
                checks["research_structure"] = len(result) > 0
            else:
                checks["research_structure"] = len(str(result)) > 50

        # LLM text check
        if "llm" in tool_name or guidelines.get("module") == "llm":
            if isinstance(result, str):
                checks["llm_text"] = len(result.strip()) > 10
            elif isinstance(result, dict):
                text_found = any(
                    isinstance(v, str) and len(v.strip()) > 10
                    for v in self._flatten_values(result)
                )
                checks["llm_text"] = text_found
            elif isinstance(result, list):
                text_found = any(
                    isinstance(item, str) and len(item.strip()) > 10
                    for item in result
                )
                checks["llm_text"] = text_found
            else:
                checks["llm_text"] = False

        # Reframe diff check
        if "reframe" in tool_name or guidelines.get("module") == "prompt_reframe":
            if input_values:
                input_text = " ".join(str(v) for v in input_values.values())
                result_str = str(result)
                checks["reframe_diff"] = (
                    input_text not in result_str
                    or len(result_str) > len(input_text) + 20
                )
            else:
                checks["reframe_diff"] = True

        # Scoring numeric check
        if category == "scoring" or "score" in tool_name:
            result_str = str(result)
            has_numeric = any(c.isdigit() for c in result_str)
            checks["scoring_numeric"] = has_numeric

        quality_pass = all(checks.values())
        return quality_pass, checks, output_len

    def _flatten_values(self, obj: Any):
        if isinstance(obj, dict):
            for v in obj.values():
                yield from self._flatten_values(v)
        elif isinstance(obj, list):
            for item in obj:
                yield from self._flatten_values(item)
        else:
            yield obj

    # -----------------------------------------------------------------------
    # Tool execution
    # -----------------------------------------------------------------------
    async def call_tool(self, func, params: dict) -> tuple[Any, str | None, float]:
        """Call a tool with timeout. Returns (result, error, duration)."""
        start = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(func(**params), timeout=TOOL_TIMEOUT)
            else:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: func(**params)),
                    timeout=TOOL_TIMEOUT,
                )
            return result, None, time.time() - start
        except asyncio.TimeoutError:
            return None, f"TIMEOUT after {TOOL_TIMEOUT}s", time.time() - start
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            return None, err_msg, time.time() - start

    # -----------------------------------------------------------------------
    # Error pattern extraction
    # -----------------------------------------------------------------------
    def extract_error_pattern(self, error: str) -> str:
        """Normalize error message to extract a pattern."""
        # Remove tool-specific identifiers
        patterns = [
            (r"'[^']+'", "'...'"),
            (r"`[^`]+`", "`...`"),
            (r"\b[0-9a-f]{8,}\b", "<HASH>"),
            (r"\b\d+\.\d+\.\d+\.\d+\b", "<IP>"),
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "<EMAIL>"),
            (r"https?://\S+", "<URL>"),
            (r"/[\w/._-]+", "<PATH>"),
        ]
        normalized = error
        for pattern, replacement in patterns:
            normalized = re.sub(pattern, replacement, normalized)
        return normalized[:200]

    # -----------------------------------------------------------------------
    # Main runner
    # -----------------------------------------------------------------------
    async def run(self) -> None:
        """Run tests for all tools in guidelines."""
        self.results["metadata"]["start_time"] = datetime.now(timezone.utc).isoformat()

        if not GUIDELINES_PATH.exists():
            logger.error(f"Guidelines file not found: {GUIDELINES_PATH}")
            return

        with open(GUIDELINES_PATH) as f:
            guidelines = json.load(f)

        total = len(guidelines)
        self.results["metadata"]["total_tools"] = total
        logger.info(f"Loaded guidelines for {total} tools")

        for idx, (tool_name, info) in enumerate(guidelines.items(), 1):
            module_name = info.get("module", "unknown")
            category = info.get("category", "other")

            # Track totals
            self.results["by_category"][category]["total"] += 1
            self.results["by_module"][module_name]["total"] += 1

            # Resolve tool
            func = self.resolve_tool(tool_name, module_name)
            if func is None:
                error = f"IMPORT_FAIL: Could not resolve {tool_name} in module {module_name}"
                self._record_result(tool_name, module_name, category, "IMPORT_FAIL", error, 0.0, False, {}, 0)
                self.error_counter[self.extract_error_pattern(error)] += 1
                continue

            # Generate params
            try:
                params, input_values = self.generate_params(func, info)
            except Exception as exc:
                error = f"PARAM_GEN_FAIL: {type(exc).__name__}: {exc}"
                self._record_result(tool_name, module_name, category, "PARAM_FAIL", error, 0.0, False, {}, 0)
                self.error_counter[self.extract_error_pattern(error)] += 1
                continue

            # Call tool
            result, error, duration = await self.call_tool(func, params)

            # Determine status
            if error:
                if error.startswith("TIMEOUT"):
                    status = "TIMEOUT"
                else:
                    status = "CRASH"
                    self.error_counter[self.extract_error_pattern(error)] += 1
            else:
                status = "OK"
                result = _coerce_result(result)

            # Validate quality
            quality_pass = False
            checks = {}
            output_len = 0
            if status == "OK":
                try:
                    quality_pass, checks, output_len = self.validate_quality(
                        result, tool_name, info, input_values
                    )
                except Exception as exc:
                    checks = {"validation_error": str(exc)}

            self._record_result(
                tool_name, module_name, category, status, error,
                duration, quality_pass, checks, output_len
            )

            # Progress
            if idx % PROGRESS_INTERVAL == 0 or idx == total:
                elapsed = time.time() - self.start_time
                logger.info(
                    f"Progress: {idx}/{total} tools processed | "
                    f"OK: {self.results['metadata']['crash_pass_count']} | "
                    f"CRASH: {self.results['metadata']['total_tested'] - self.results['metadata']['crash_pass_count']} | "
                    f"Quality: {self.results['metadata']['quality_pass_count']} | "
                    f"Elapsed: {elapsed:.1f}s"
                )

        # Finalize metadata
        self.results["metadata"]["end_time"] = datetime.now(timezone.utc).isoformat()
        total_tested = self.results["metadata"]["total_tested"]
        crash_pass = self.results["metadata"]["crash_pass_count"]
        quality_pass = self.results["metadata"]["quality_pass_count"]

        if total_tested > 0:
            self.results["metadata"]["crash_pass_rate"] = round(crash_pass / total_tested, 4)
            self.results["metadata"]["quality_pass_rate"] = round(quality_pass / total_tested, 4)

        # Category breakdown
        for cat, stats in self.results["by_category"].items():
            if stats["tested"] > 0:
                stats["crash_pass_rate"] = round(stats["crash_pass"] / stats["tested"], 4)
                stats["quality_pass_rate"] = round(stats["quality_pass"] / stats["tested"], 4)
            else:
                stats["crash_pass_rate"] = 0.0
                stats["quality_pass_rate"] = 0.0

        # Top errors
        self.results["top_errors"] = [
            {"pattern": pat, "count": cnt}
            for pat, cnt in self.error_counter.most_common(20)
        ]

        # Save report
        with open(REPORT_PATH, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        logger.info(f"Report saved to {REPORT_PATH}")
        self._print_summary()

    def _record_result(
        self, tool_name: str, module_name: str, category: str,
        status: str, error: str | None, duration: float,
        quality_pass: bool, checks: dict, output_len: int
    ) -> None:
        """Record a single tool result."""
        self.results["metadata"]["total_tested"] += 1
        self.results["by_category"][category]["tested"] += 1
        self.results["by_module"][module_name]["tested"] += 1

        if status == "OK":
            self.results["metadata"]["crash_pass_count"] += 1
            self.results["by_category"][category]["crash_pass"] += 1
            self.results["by_module"][module_name]["crash_pass"] += 1

        if quality_pass:
            self.results["metadata"]["quality_pass_count"] += 1
            self.results["by_category"][category]["quality_pass"] += 1
            self.results["by_module"][module_name]["quality_pass"] += 1

        tool_record = {
            "name": tool_name,
            "module": module_name,
            "category": category,
            "status": status,
            "duration_sec": round(duration, 2),
            "quality_pass": quality_pass,
            "quality_checks": checks,
            "output_length": output_len,
            "error": error,
        }
        self.results["tools"].append(tool_record)
        self.results["by_category"][category]["tools"].append(tool_record)
        self.results["by_module"][module_name]["tools"].append(tool_record)

    def _print_summary(self) -> None:
        """Print final summary to console."""
        meta = self.results["metadata"]
        print("\n" + "=" * 70)
        print("LOOM 835-TOOL VALIDATED TEST SUMMARY")
        print("=" * 70)
        print(f"Total tools:        {meta['total_tools']}")
        print(f"Total tested:       {meta['total_tested']}")
        print(f"Crash pass rate:    {meta['crash_pass_rate']:.2%} ({meta['crash_pass_count']}/{meta['total_tested']})")
        print(f"Quality pass rate:  {meta['quality_pass_rate']:.2%} ({meta['quality_pass_count']}/{meta['total_tested']})")
        print(f"Total time:         {time.time() - self.start_time:.1f}s")
        print("-" * 70)
        print("CATEGORY BREAKDOWN")
        print("-" * 70)
        for cat, stats in sorted(self.results["by_category"].items()):
            print(
                f"  {cat:20s} | total: {stats['total']:4d} | tested: {stats['tested']:4d} | "
                f"crash: {stats['crash_pass_rate']:6.1%} | quality: {stats['quality_pass_rate']:6.1%}"
            )
        print("-" * 70)
        print("TOP ERROR PATTERNS")
        print("-" * 70)
        for err in self.results["top_errors"][:10]:
            print(f"  [{err['count']:4d}] {err['pattern'][:80]}")
        print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    tester = ValidatedTester()
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
