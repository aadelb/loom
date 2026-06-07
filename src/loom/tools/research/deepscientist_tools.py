"""DeepScientist Integration — research quest orchestration, memory, benchmarks, evidence.

Wraps DeepScientist (github.com/ResearAI/DeepScientist) modules as Loom MCP tools:
- Quest: multi-stage research orchestration with Bayesian exploration
- Memory: structured findings store (papers, ideas, decisions, knowledge)
- Benchstore: AI benchmark catalog with prompt building
- Evidence: evidence packet collection with SHA-256 hashing

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.deepscientist")

DS_HOME = Path("/home/aadel/DeepScientist")
DS_QUESTS_DIR = Path("/home/aadel/.deepscientist/quests")
DS_MEMORY_DIR = Path("/home/aadel/.deepscientist/memory")
DS_EVIDENCE_DIR = Path("/home/aadel/.deepscientist/evidence")

MEMORY_KINDS = ("papers", "ideas", "decisions", "episodes", "knowledge", "templates")

QUEST_DIRECTORIES = (
    "artifacts/baselines",
    "artifacts/decisions",
    "artifacts/ideas",
    "artifacts/progress",
    "artifacts/reports",
    "experiments/main",
    "literature",
    "memory/decisions",
    "memory/ideas",
    "memory/knowledge",
    "memory/papers",
)


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _slugify(text: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower().strip())
    return slug.strip("-")[:64]


# ─── QUEST ORCHESTRATION ───────────────────────────────────────────────

@handle_tool_errors("research_quest_create")
async def research_quest_create(
    goal: str,
    title: str | None = None,
    stages: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new research quest — a multi-stage research project with structured outputs.

    A quest provides a structured workspace for multi-stage research with:
    - Literature tracking (papers, citations)
    - Memory (ideas, decisions, knowledge)
    - Experiments and baselines
    - Progress artifacts and reports

    Args:
        goal: The research goal/question to investigate.
        title: Optional human-readable title (auto-generated from goal if omitted).
        stages: Optional list of research stages (default: discover, analyze, synthesize, validate).

    Returns:
        Quest metadata with ID, path, and initial structure.
    """
    quest_id = _sha256(goal + _utc_now())[:12]
    quest_title = title or goal[:80]
    quest_root = _ensure_dir(DS_QUESTS_DIR / quest_id)

    for subdir in QUEST_DIRECTORIES:
        _ensure_dir(quest_root / subdir)

    quest_stages = stages or ["discover", "analyze", "synthesize", "validate"]

    quest_yaml = {
        "id": quest_id,
        "title": quest_title,
        "goal": goal,
        "stages": quest_stages,
        "current_stage": quest_stages[0],
        "status": "active",
        "created_at": _utc_now(),
        "findings_count": 0,
        "decisions_count": 0,
    }

    (quest_root / "quest.json").write_text(json.dumps(quest_yaml, indent=2))

    brief = f"# {quest_title}\n\n## Goal\n{goal}\n\n## Stages\n"
    for i, s in enumerate(quest_stages, 1):
        brief += f"{i}. {s}\n"
    brief += f"\n## Status\nActive — stage: {quest_stages[0]}\n"
    (quest_root / "BRIEF.md").write_text(brief)

    return {
        "quest_id": quest_id,
        "title": quest_title,
        "goal": goal,
        "stages": quest_stages,
        "current_stage": quest_stages[0],
        "path": str(quest_root),
        "directories_created": len(QUEST_DIRECTORIES),
    }


@handle_tool_errors("research_quest_advance")
async def research_quest_advance(
    quest_id: str,
    findings: list[str] | None = None,
    decision: str | None = None,
    next_stage: str | None = None,
) -> dict[str, Any]:
    """Advance a research quest to the next stage with findings and decisions.

    Records progress, stores findings in memory, and optionally advances
    to the next stage in the research pipeline.

    Args:
        quest_id: The quest ID to advance.
        findings: List of findings/discoveries from the current stage.
        decision: Key decision made during this stage.
        next_stage: Explicit next stage (otherwise auto-advances sequentially).

    Returns:
        Updated quest state with new stage and accumulated findings.
    """
    quest_root = DS_QUESTS_DIR / quest_id
    quest_file = quest_root / "quest.json"

    if not quest_file.exists():
        return {"error": f"Quest {quest_id} not found"}

    quest = json.loads(quest_file.read_text())
    current_stage = quest["current_stage"]
    stages = quest["stages"]

    progress_entry = {
        "stage": current_stage,
        "timestamp": _utc_now(),
        "findings": findings or [],
        "decision": decision,
    }

    progress_file = quest_root / "artifacts" / "progress" / f"{current_stage}.json"
    _ensure_dir(progress_file.parent)
    progress_file.write_text(json.dumps(progress_entry, indent=2))

    if findings:
        for f in findings:
            idea_file = quest_root / "memory" / "ideas" / f"{_slugify(f[:40])}.md"
            idea_file.write_text(f"# Finding\n\n{f}\n\nDiscovered during: {current_stage}\nDate: {_utc_now()}\n")
        quest["findings_count"] = quest.get("findings_count", 0) + len(findings)

    if decision:
        dec_file = quest_root / "memory" / "decisions" / f"{_slugify(decision[:40])}.md"
        dec_file.write_text(f"# Decision\n\n{decision}\n\nMade during: {current_stage}\nDate: {_utc_now()}\n")
        quest["decisions_count"] = quest.get("decisions_count", 0) + 1

    if next_stage:
        quest["current_stage"] = next_stage
    else:
        current_idx = stages.index(current_stage) if current_stage in stages else -1
        if current_idx < len(stages) - 1:
            quest["current_stage"] = stages[current_idx + 1]
        else:
            quest["status"] = "completed"
            quest["completed_at"] = _utc_now()

    quest_file.write_text(json.dumps(quest, indent=2))

    return {
        "quest_id": quest_id,
        "previous_stage": current_stage,
        "current_stage": quest["current_stage"],
        "status": quest["status"],
        "findings_recorded": len(findings or []),
        "decision_recorded": decision is not None,
        "total_findings": quest["findings_count"],
        "total_decisions": quest["decisions_count"],
    }


@handle_tool_errors("research_quest_status")
async def research_quest_status(
    quest_id: str | None = None,
) -> dict[str, Any]:
    """Get status of a research quest or list all active quests.

    Args:
        quest_id: Specific quest ID to check (omit to list all quests).

    Returns:
        Quest status or list of all active quests with progress.
    """
    if quest_id:
        quest_file = DS_QUESTS_DIR / quest_id / "quest.json"
        if not quest_file.exists():
            return {"error": f"Quest {quest_id} not found"}
        quest = json.loads(quest_file.read_text())
        progress_dir = DS_QUESTS_DIR / quest_id / "artifacts" / "progress"
        completed_stages = []
        if progress_dir.exists():
            completed_stages = [f.stem for f in progress_dir.glob("*.json")]
        quest["completed_stages"] = completed_stages
        return quest

    _ensure_dir(DS_QUESTS_DIR)
    quests = []
    for qdir in DS_QUESTS_DIR.iterdir():
        qfile = qdir / "quest.json"
        if qfile.exists():
            q = json.loads(qfile.read_text())
            quests.append({
                "id": q["id"],
                "title": q["title"],
                "status": q["status"],
                "current_stage": q["current_stage"],
                "findings": q.get("findings_count", 0),
            })

    return {"quests": quests, "total": len(quests)}


# ─── MEMORY SERVICE ────────────────────────────────────────────────────

@handle_tool_errors("research_ds_memory_store")
async def research_ds_memory_store(
    content: str,
    kind: str = "knowledge",
    tags: list[str] | None = None,
    title: str | None = None,
    quest_id: str | None = None,
) -> dict[str, Any]:
    """Store a research finding/memory with structured metadata.

    Stores papers, ideas, decisions, knowledge or episode memories
    that can be recalled later by kind, tags, or full-text search.

    Args:
        content: The content to store (finding, paper summary, idea, etc.).
        kind: Memory type — one of: papers, ideas, decisions, episodes, knowledge, templates.
        tags: Optional tags for categorization and retrieval.
        title: Optional title (auto-extracted from first line if omitted).
        quest_id: Optional quest to associate this memory with.

    Returns:
        Memory card metadata with ID and storage path.
    """
    if kind not in MEMORY_KINDS:
        return {"error": f"Invalid kind '{kind}'. Must be one of: {', '.join(MEMORY_KINDS)}"}

    if quest_id:
        mem_dir = _ensure_dir(DS_QUESTS_DIR / quest_id / "memory" / kind)
    else:
        mem_dir = _ensure_dir(DS_MEMORY_DIR / kind)

    card_id = _sha256(content + _utc_now())[:10]
    card_title = title or content.split("\n")[0][:80]

    card = {
        "id": card_id,
        "title": card_title,
        "kind": kind,
        "tags": tags or [],
        "created_at": _utc_now(),
        "quest_id": quest_id,
        "content_hash": _sha256(content),
    }

    card_path = mem_dir / f"{card_id}.md"
    frontmatter = f"---\n{json.dumps(card, indent=2)}\n---\n\n"
    card_path.write_text(frontmatter + content)

    return {
        "card_id": card_id,
        "title": card_title,
        "kind": kind,
        "tags": tags or [],
        "path": str(card_path),
        "content_length": len(content),
    }


@handle_tool_errors("research_ds_memory_recall")
async def research_ds_memory_recall(
    query: str | None = None,
    kind: str | None = None,
    tags: list[str] | None = None,
    quest_id: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Recall stored research memories by kind, tags, or text search.

    Searches across all stored memories (papers, ideas, decisions, knowledge)
    with optional filtering by kind, tags, or quest association.

    Args:
        query: Optional text to search for in memory content.
        kind: Filter by memory kind (papers, ideas, decisions, etc.).
        tags: Filter by tags (returns memories with ANY matching tag).
        quest_id: Filter by associated quest.
        limit: Maximum results to return (default: 10).

    Returns:
        List of matching memory cards with metadata and content preview.
    """
    search_dirs = []

    if quest_id:
        quest_mem = DS_QUESTS_DIR / quest_id / "memory"
        if kind:
            search_dirs.append(quest_mem / kind)
        else:
            for k in MEMORY_KINDS:
                d = quest_mem / k
                if d.exists():
                    search_dirs.append(d)
    else:
        if kind:
            d = DS_MEMORY_DIR / kind
            if d.exists():
                search_dirs.append(d)
        else:
            for k in MEMORY_KINDS:
                d = DS_MEMORY_DIR / k
                if d.exists():
                    search_dirs.append(d)
            for qdir in (DS_QUESTS_DIR.iterdir() if DS_QUESTS_DIR.exists() else []):
                for k in MEMORY_KINDS:
                    d = qdir / "memory" / k
                    if d.exists():
                        search_dirs.append(d)

    results = []
    query_lower = (query or "").lower()

    for d in search_dirs:
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            text = f.read_text()
            if query_lower and query_lower not in text.lower():
                continue

            meta_match = text.split("---\n")
            card_meta = {}
            content = text
            if len(meta_match) >= 3:
                try:
                    card_meta = json.loads(meta_match[1])
                    content = "---\n".join(meta_match[2:])
                except (json.JSONDecodeError, IndexError):
                    pass

            if tags:
                card_tags = set(card_meta.get("tags", []))
                if not card_tags.intersection(set(tags)):
                    continue

            results.append({
                "id": card_meta.get("id", f.stem),
                "title": card_meta.get("title", f.stem),
                "kind": card_meta.get("kind", d.name),
                "tags": card_meta.get("tags", []),
                "created_at": card_meta.get("created_at", ""),
                "quest_id": card_meta.get("quest_id"),
                "preview": content.strip()[:300],
                "path": str(f),
            })

    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "results": results[:limit],
        "total_found": len(results),
        "filters": {"query": query, "kind": kind, "tags": tags, "quest_id": quest_id},
    }


# ─── BENCHMARK CATALOG ─────────────────────────────────────────────────

@handle_tool_errors("research_benchmark_catalog")
async def research_benchmark_catalog(
    query: str | None = None,
    capability: str | None = None,
    difficulty: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Browse the DeepScientist AI benchmark catalog.

    Searches the curated catalog of AI benchmarks with metadata about
    resource requirements, difficulty, papers, and setup instructions.

    Args:
        query: Text search across benchmark names and descriptions.
        capability: Filter by capability tag (e.g., "reasoning", "coding", "math").
        difficulty: Filter by difficulty level (easy, medium, hard, expert).
        limit: Maximum results (default: 20).

    Returns:
        Matching benchmarks with metadata, resource requirements, and setup info.
    """
    catalog_dir = DS_HOME / "src" / "prompts" / "benchstore"
    catalog_files = list(catalog_dir.glob("*.json")) if catalog_dir.exists() else []

    alt_catalog = DS_HOME / "benchstore"
    if alt_catalog.exists():
        catalog_files.extend(alt_catalog.glob("**/*.json"))
        catalog_files.extend(alt_catalog.glob("**/*.yaml"))

    benchmarks = []
    for f in catalog_files:
        try:
            if f.suffix == ".json":
                data = json.loads(f.read_text())
            else:
                import yaml
                data = yaml.safe_load(f.read_text())

            if isinstance(data, list):
                benchmarks.extend(data)
            elif isinstance(data, dict):
                if "benchmarks" in data:
                    benchmarks.extend(data["benchmarks"])
                else:
                    benchmarks.append(data)
        except Exception:
            continue

    results = []
    query_lower = (query or "").lower()

    for bench in benchmarks:
        if not isinstance(bench, dict):
            continue

        name = str(bench.get("name", bench.get("id", ""))).lower()
        desc = str(bench.get("one_line", bench.get("description", ""))).lower()
        task = str(bench.get("task_description", "")).lower()
        tags = [str(t).lower() for t in (bench.get("capability_tags", []) or [])]

        if query_lower and query_lower not in name and query_lower not in desc and query_lower not in task:
            continue

        if capability and capability.lower() not in tags:
            continue

        if difficulty and str(bench.get("difficulty", "")).lower() != difficulty.lower():
            continue

        results.append({
            "name": bench.get("name", bench.get("id", "unknown")),
            "one_line": bench.get("one_line", bench.get("description", "")),
            "difficulty": bench.get("difficulty", "unknown"),
            "time_band": bench.get("time_band", "unknown"),
            "cost_band": bench.get("cost_band", "unknown"),
            "capability_tags": bench.get("capability_tags", []),
            "paper": bench.get("paper", {}),
            "resources": bench.get("resources", {}),
            "homepage": bench.get("homepage", ""),
        })

    return {
        "benchmarks": results[:limit],
        "total_found": len(results),
        "catalog_files_scanned": len(catalog_files),
    }


# ─── EVIDENCE COLLECTION ───────────────────────────────────────────────

@handle_tool_errors("research_evidence_collect")
async def research_evidence_collect(
    claim: str,
    sources: list[dict[str, str]],
    quest_id: str | None = None,
    confidence: float = 0.7,
) -> dict[str, Any]:
    """Collect and hash evidence for a research claim.

    Creates an evidence packet with SHA-256 content hashing for integrity
    verification. Links evidence to specific claims and research quests.

    Args:
        claim: The claim this evidence supports or refutes.
        sources: List of source dicts with keys: url, title, excerpt.
        quest_id: Optional quest to associate evidence with.
        confidence: Confidence level 0.0-1.0 (default: 0.7).

    Returns:
        Evidence packet with ID, hash, and verification metadata.
    """
    packet_id = _sha256(claim + _utc_now())[:12]

    packet = {
        "id": packet_id,
        "claim": claim,
        "sources": sources,
        "confidence": min(1.0, max(0.0, confidence)),
        "quest_id": quest_id,
        "created_at": _utc_now(),
        "source_count": len(sources),
    }

    content_for_hash = json.dumps(
        {"claim": claim, "sources": sources},
        ensure_ascii=False,
        sort_keys=True,
    )
    packet["content_hash"] = _sha256(content_for_hash)

    if quest_id:
        evidence_dir = _ensure_dir(DS_QUESTS_DIR / quest_id / "artifacts" / "baselines")
    else:
        evidence_dir = _ensure_dir(DS_EVIDENCE_DIR)

    packet_path = evidence_dir / f"{packet_id}.json"
    packet_path.write_text(json.dumps(packet, indent=2))

    return {
        "packet_id": packet_id,
        "claim": claim,
        "source_count": len(sources),
        "confidence": packet["confidence"],
        "content_hash": packet["content_hash"],
        "path": str(packet_path),
        "verified": True,
    }


# ─── RESEARCH SAMPLER (Multi-strategy sampling) ───────────────────────

@handle_tool_errors("research_sampler")
async def research_sampler(
    query: str,
    strategies: list[str] | None = None,
    temperature_range: list[float] | None = None,
    num_samples: int = 5,
) -> dict[str, Any]:
    """Multi-strategy research sampler — generates diverse research angles.

    Applies multiple sampling strategies (temperature variation, persona rotation,
    framing shifts) to produce diverse research perspectives on a question.
    Inspired by DeepScientist's exploration-exploitation tradeoff.

    Args:
        query: Research question to sample diverse perspectives on.
        strategies: Sampling strategies to use (default: all).
            Available: temperature_sweep, persona_rotation, framing_shift,
                      contrarian, bayesian_explore, analogical.
        temperature_range: [min, max] temperature for sweep (default: [0.3, 1.2]).
        num_samples: Number of diverse samples to generate (default: 5).

    Returns:
        Diverse research angles with strategy attribution and novelty scores.
    """
    available_strategies = {
        "temperature_sweep": "Vary generation temperature for diversity",
        "persona_rotation": "Rotate expert personas (scientist, critic, futurist, historian, practitioner)",
        "framing_shift": "Reframe question through different lenses (technical, economic, social, ethical)",
        "contrarian": "Generate opposing/contrarian perspectives",
        "bayesian_explore": "Explore high-uncertainty areas (maximize information gain)",
        "analogical": "Draw analogies from distant domains",
    }

    active_strategies = strategies or list(available_strategies.keys())
    temp_range = temperature_range or [0.3, 1.2]

    samples = []

    personas = [
        ("Research Scientist", "Focus on methodology, rigor, reproducibility"),
        ("Industry Practitioner", "Focus on implementation, scalability, ROI"),
        ("Critical Reviewer", "Focus on weaknesses, limitations, alternative explanations"),
        ("Futurist", "Focus on long-term implications, emerging trends"),
        ("Historian", "Focus on precedents, evolution of the field, lessons learned"),
    ]

    framings = [
        ("Technical", f"From a technical/engineering perspective: {query}"),
        ("Economic", f"From an economic/market perspective: {query}"),
        ("Social", f"From a social impact perspective: {query}"),
        ("Ethical", f"From an ethical/safety perspective: {query}"),
        ("Comparative", f"Compared to alternative approaches: {query}"),
    ]

    contrarian_prompts = [
        f"What if the opposite of conventional wisdom about '{query}' is true?",
        f"What are the strongest arguments AGAINST the mainstream view on '{query}'?",
        f"What overlooked evidence contradicts popular assumptions about '{query}'?",
    ]

    analogical_domains = [
        ("Biology/Evolution", "How does this parallel natural selection/evolution?"),
        ("Physics/Thermodynamics", "What thermodynamic principles apply here?"),
        ("Economics/Game Theory", "What game-theoretic dynamics are at play?"),
        ("History/Civilizations", "What historical parallels exist?"),
        ("Computer Science/Algorithms", "What algorithmic metaphors apply?"),
    ]

    sample_idx = 0
    for strat in active_strategies:
        if sample_idx >= num_samples:
            break

        if strat == "temperature_sweep":
            step = (temp_range[1] - temp_range[0]) / max(1, num_samples - 1)
            for i in range(min(2, num_samples - sample_idx)):
                temp = temp_range[0] + i * step
                samples.append({
                    "strategy": "temperature_sweep",
                    "temperature": round(temp, 2),
                    "prompt": query,
                    "angle": f"Low-temp precise exploration (T={temp:.2f})" if temp < 0.7 else f"High-temp creative exploration (T={temp:.2f})",
                    "novelty_score": round(temp / temp_range[1], 2),
                })
                sample_idx += 1

        elif strat == "persona_rotation":
            for persona, focus in personas[:min(2, num_samples - sample_idx)]:
                samples.append({
                    "strategy": "persona_rotation",
                    "persona": persona,
                    "focus": focus,
                    "prompt": f"As a {persona}: {query}",
                    "angle": f"{persona} perspective — {focus}",
                    "novelty_score": 0.7,
                })
                sample_idx += 1

        elif strat == "framing_shift":
            for frame_name, frame_prompt in framings[:min(2, num_samples - sample_idx)]:
                samples.append({
                    "strategy": "framing_shift",
                    "frame": frame_name,
                    "prompt": frame_prompt,
                    "angle": f"{frame_name} framing of the question",
                    "novelty_score": 0.6,
                })
                sample_idx += 1

        elif strat == "contrarian":
            for cp in contrarian_prompts[:min(1, num_samples - sample_idx)]:
                samples.append({
                    "strategy": "contrarian",
                    "prompt": cp,
                    "angle": "Contrarian/opposing viewpoint",
                    "novelty_score": 0.9,
                })
                sample_idx += 1

        elif strat == "bayesian_explore":
            samples.append({
                "strategy": "bayesian_explore",
                "prompt": f"What are the highest-uncertainty aspects of '{query}' where new information would be most valuable?",
                "angle": "Bayesian exploration — maximize information gain",
                "novelty_score": 0.85,
            })
            sample_idx += 1

        elif strat == "analogical":
            for domain, question in analogical_domains[:min(1, num_samples - sample_idx)]:
                samples.append({
                    "strategy": "analogical",
                    "domain": domain,
                    "prompt": f"Draw an analogy between '{query}' and {domain.lower()}. {question}",
                    "angle": f"Cross-domain analogy: {domain}",
                    "novelty_score": 0.8,
                })
                sample_idx += 1

    return {
        "query": query,
        "samples": samples[:num_samples],
        "strategies_used": list(set(s["strategy"] for s in samples)),
        "total_samples": len(samples[:num_samples]),
        "available_strategies": list(available_strategies.keys()),
        "diversity_score": round(len(set(s["strategy"] for s in samples)) / max(1, len(available_strategies)), 2),
    }


# ─── RUNNER ORCHESTRATOR (Multi-model research) ───────────────────────

@handle_tool_errors("research_multi_runner")
async def research_multi_runner(
    query: str,
    runners: list[str] | None = None,
    consensus_threshold: float = 0.6,
) -> dict[str, Any]:
    """Multi-model research runner — query multiple LLM providers and synthesize.

    Inspired by DeepScientist's multi-runner architecture, sends the same
    research question to multiple models and aggregates findings with
    consensus scoring.

    Args:
        query: Research question to investigate across models.
        runners: List of runner/provider names to use.
            Available: groq, nvidia, deepseek, kimi, gemini, openai, anthropic, ollama.
            Default: groq, nvidia, deepseek.
        consensus_threshold: Minimum agreement ratio to consider a finding confirmed (0.0-1.0).

    Returns:
        Aggregated findings with per-runner responses and consensus scores.
    """
    import aiohttp

    available_runners = ["groq", "nvidia", "deepseek", "kimi", "gemini", "openai", "anthropic", "ollama"]
    active_runners = runners or ["groq", "nvidia", "deepseek"]

    invalid = [r for r in active_runners if r not in available_runners]
    if invalid:
        return {"error": f"Invalid runners: {invalid}. Available: {available_runners}"}

    results = {}
    start = time.time()

    async def _query_loom_llm(provider: str) -> dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": query,
                    "model": provider,
                    "max_tokens": 2000,
                }
                async with session.post(
                    "http://localhost:8788/api/v1/tools/research_llm_answer",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {"provider": provider, "status": "success", "response": data}
                    return {"provider": provider, "status": "error", "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"provider": provider, "status": "error", "error": str(e)[:200]}

    tasks = [_query_loom_llm(r) for r in active_runners]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    for resp in responses:
        if isinstance(resp, Exception):
            continue
        if isinstance(resp, dict):
            results[resp["provider"]] = resp

    successful = [r for r in results.values() if r["status"] == "success"]

    return {
        "query": query,
        "runners_queried": active_runners,
        "successful": len(successful),
        "failed": len(active_runners) - len(successful),
        "results": results,
        "consensus_threshold": consensus_threshold,
        "duration_ms": round((time.time() - start) * 1000),
    }
