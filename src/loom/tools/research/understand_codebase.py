"""research_understand_codebase — Turn any codebase into an interactive knowledge graph.

Mirrors the Understand-Anything plugin (https://github.com/Egonex-AI/Understand-Anything)
node/edge schema faithfully. Supports local paths, GitHub repos (owner/name), and git URLs.

Actions:
- graph: Build a queryable knowledge graph from codebase/docs (analyze files → extract nodes/edges → store)
- ask: Query the graph to answer questions about the codebase
- explain: Deep-dive explanation of a specific file/function/module and its connections
- onboard: Guided onboarding summary with entry points, data flows, key modules
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from loom.db_helpers import db_connection, get_db_path, init_db
from loom.error_responses import handle_tool_errors
from loom.subprocess_helpers import run_command
from loom.tools.research.knowledge_graph import _generate_mermaid_visualization

logger = logging.getLogger("loom.tools.understand_codebase")

# Node and edge types from Understand-Anything repo
NODE_TYPES = {
    "code": {"file", "function", "class", "module", "concept"},
    "non_code": {"config", "document", "service", "table", "endpoint", "pipeline", "schema", "resource"},
    "domain": {"domain", "flow", "step"},
    "knowledge": {"article", "entity", "topic", "claim", "source"},
}
ALL_NODE_TYPES = set().union(*NODE_TYPES.values())

EDGE_TYPES = {
    "structural": {"imports", "exports", "contains", "inherits", "implements"},
    "behavioral": {"calls", "subscribes", "publishes", "middleware"},
    "data_flow": {"reads_from", "writes_to", "transforms", "validates"},
    "dependencies": {"depends_on", "tested_by", "configures"},
    "semantic": {"related", "similar_to"},
    "infrastructure": {"deploys", "serves", "provisions", "triggers"},
    "schema_data": {"migrates", "documents", "routes", "defines_schema"},
    "domain": {"contains_flow", "flow_step", "cross_domain"},
    "knowledge": {"cites", "contradicts", "builds_on", "exemplifies", "categorized_under", "authored_by"},
}
ALL_EDGE_TYPES = set().union(*EDGE_TYPES.values())

# Default file extensions for code + docs
DEFAULT_GLOBS = ["*.py", "*.ts", "*.js", "*.jsx", "*.tsx", "*.md", "*.json", "*.yml", "*.yaml", "*.toml", "*.txt"]

_UNDERSTAND_DB = get_db_path("understand_graphs")


def _generate_graph_id(target: str) -> str:
    """Generate a deterministic graph ID from target path/URL."""
    h = hashlib.sha256(target.encode()).hexdigest()[:12]
    return f"graph_{h}"


def _init_graph_db(graph_id: str) -> str:
    """Initialize SQLite schema for a codebase graph."""
    graph_db = get_db_path(f"understand_graphs/{graph_id}")
    schema = """
    CREATE TABLE IF NOT EXISTS nodes (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        file_path TEXT,
        summary TEXT,
        tags TEXT,
        complexity TEXT,
        line_start INTEGER,
        line_end INTEGER,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS edges (
        id INTEGER PRIMARY KEY,
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        edge_type TEXT NOT NULL,
        direction TEXT NOT NULL,
        weight REAL,
        description TEXT,
        UNIQUE(source_id, target_id, edge_type),
        FOREIGN KEY(source_id) REFERENCES nodes(id),
        FOREIGN KEY(target_id) REFERENCES nodes(id)
    );

    CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
    CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_path);
    CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
    CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
    """
    init_db(graph_db, schema)
    return str(graph_db)


def _resolve_target(target: str) -> tuple[Path, bool]:
    """Resolve target to a local path.

    Returns: (path, was_cloned)
    - If target is a local path, return it as-is
    - If target is owner/name or a URL, shallow-clone to temp dir
    """
    # Check if it's a local path
    local_path = Path(target).expanduser()
    if local_path.exists() and local_path.is_dir():
        return local_path, False

    # Treat as remote — clone via gh or git
    temp_dir = Path(tempfile.mkdtemp(prefix="understand_"))
    try:
        # Try gh repo clone first (faster, GitHub-aware)
        if "/" in target and not "://" in target:
            # Assume owner/name format
            run_command(f"gh repo clone {quote(target, safe='/')} {temp_dir} -- --depth 1", timeout=60)
        else:
            # Assume full git URL
            run_command(f"git clone --depth 1 {quote(target, safe=':/')} {temp_dir}", timeout=60)
        return temp_dir, True
    except Exception as e:
        logger.error("Failed to clone %s: %s", target, e)
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def _walk_files(root: Path, include_globs: list[str] | None = None, max_files: int = 60) -> list[tuple[Path, str]]:
    """Walk directory and yield (path, relative_path) tuples, capped at max_files."""
    if include_globs is None:
        include_globs = DEFAULT_GLOBS

    patterns = [re.compile(f"^.*{g.replace('*', '.*')}$") for g in include_globs]
    skip_dirs = {".git", "__pycache__", "node_modules", "dist", ".next", "build", ".venv", "venv"}

    files = []
    for item in sorted(root.rglob("*")):
        if len(files) >= max_files:
            break
        if item.is_dir():
            if any(p.name in skip_dirs for p in item.parents) or item.name in skip_dirs:
                continue
        elif item.is_file():
            if any(p.match(item.name) for p in patterns):
                try:
                    rel_path = item.relative_to(root)
                    files.append((item, str(rel_path)))
                except ValueError:
                    pass

    return files[:max_files]


async def _extract_nodes_and_edges(file_path: Path, content: str, root_path: Path) -> tuple[list[dict], list[dict]]:
    """Extract nodes and edges from a single file using LLM.

    Returns: (nodes, edges) where each node/edge matches the Understand-Anything schema.
    """
    try:
        from loom.tools.llm.llm import _call_with_cascade

        rel_path = str(file_path.relative_to(root_path))

        # Limit content to first 8000 chars to control tokens
        truncated = content[:8000]
        if len(content) > 8000:
            truncated += f"\n... [truncated, total {len(content)} chars]"

        extraction_prompt = f"""Analyze this file and extract all code entities and relationships.

File: {rel_path}
Content (first 8000 chars):
```
{truncated}
```

Return valid JSON with exactly this structure (no markdown, no extra text):
{{
  "nodes": [
    {{"id": "<type>:<rel_path>:<name>", "type": "<type from: {','.join(sorted(ALL_NODE_TYPES))}>" , "name": "<entity_name>", "summary": "<one-line summary>", "tags": ["<tag1>", "<tag2>"], "complexity": "<simple|moderate|complex>", "line_start": <int or null>, "line_end": <int or null>}}
  ],
  "edges": [
    {{"source_id": "<id>", "target_id": "<id>", "type": "<type from: {','.join(sorted(list(ALL_EDGE_TYPES)[:10]))}...>", "direction": "<forward|backward|bidirectional>", "weight": <0.0-1.0>, "description": "<relationship>"}}
  ]
}}

Be concise. Extract 3-10 nodes and 2-5 edges per file."""

        result = await _call_with_cascade(extraction_prompt)
        text_result = result.text if hasattr(result, "text") else str(result)

        # Try to extract JSON from response
        json_match = re.search(r"\{.*\}", text_result, re.DOTALL)
        if not json_match:
            logger.warning("No JSON in extraction response for %s", rel_path)
            return [], []

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.debug("Invalid JSON in extraction for %s", rel_path)
            return [], []

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        # Validate and normalize nodes
        validated_nodes = []
        for node in nodes:
            if not all(k in node for k in ["id", "type", "name", "summary"]):
                continue
            if node["type"] not in ALL_NODE_TYPES:
                node["type"] = "concept"  # fallback
            validated_nodes.append({
                "id": node["id"],
                "type": node["type"],
                "name": node["name"],
                "file_path": rel_path,
                "summary": node.get("summary", ""),
                "tags": node.get("tags", []),
                "complexity": node.get("complexity", "moderate"),
                "line_start": node.get("line_start"),
                "line_end": node.get("line_end"),
            })

        # Validate and normalize edges
        validated_edges = []
        for edge in edges:
            if not all(k in edge for k in ["source_id", "target_id", "type"]):
                continue
            if edge["type"] not in ALL_EDGE_TYPES:
                continue
            validated_edges.append({
                "source_id": edge["source_id"],
                "target_id": edge["target_id"],
                "type": edge["type"],
                "direction": edge.get("direction", "forward"),
                "weight": edge.get("weight", 0.5),
                "description": edge.get("description", ""),
            })

        return validated_nodes, validated_edges

    except Exception as e:
        logger.debug("Extraction failed for %s: %s", file_path, e)
        return [], []


def _store_graph_in_db(graph_db: str, nodes: list[dict], edges: list[dict]) -> None:
    """Store nodes and edges in SQLite graph database."""
    with db_connection(graph_db) as conn:
        c = conn.cursor()

        # Insert nodes
        for node in nodes:
            try:
                c.execute(
                    """INSERT OR REPLACE INTO nodes
                       (id, name, type, file_path, summary, tags, complexity, line_start, line_end, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                    (
                        node["id"],
                        node["name"],
                        node["type"],
                        node["file_path"],
                        node["summary"],
                        json.dumps(node.get("tags", [])),
                        node["complexity"],
                        node.get("line_start"),
                        node.get("line_end"),
                    ),
                )
            except Exception as e:
                logger.debug("Failed to insert node %s: %s", node["id"], e)

        # Insert edges
        for edge in edges:
            try:
                c.execute(
                    """INSERT OR IGNORE INTO edges
                       (source_id, target_id, edge_type, direction, weight, description)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        edge["source_id"],
                        edge["target_id"],
                        edge["type"],
                        edge["direction"],
                        edge["weight"],
                        edge["description"],
                    ),
                )
            except Exception as e:
                logger.debug("Failed to insert edge %s -> %s: %s", edge["source_id"], edge["target_id"], e)

        conn.commit()


def _load_graph_from_db(graph_db: str) -> tuple[list[dict], list[dict]]:
    """Load all nodes and edges from SQLite graph database."""
    nodes = []
    edges = []

    with db_connection(graph_db) as conn:
        c = conn.cursor()

        # Load nodes
        c.execute("""SELECT id, name, type, file_path, summary, tags, complexity, line_start, line_end FROM nodes""")
        for row in c.fetchall():
            nodes.append({
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "file_path": row[3],
                "summary": row[4],
                "tags": json.loads(row[5]) if row[5] else [],
                "complexity": row[6],
                "line_start": row[7],
                "line_end": row[8],
            })

        # Load edges
        c.execute("""SELECT source_id, target_id, edge_type, direction, weight, description FROM edges""")
        for row in c.fetchall():
            edges.append({
                "source_id": row[0],
                "target_id": row[1],
                "type": row[2],
                "direction": row[3],
                "weight": row[4],
                "description": row[5],
            })

    return nodes, edges


def _find_top_nodes(nodes: list[dict], edges: list[dict], limit: int = 10) -> list[dict]:
    """Find top nodes by connectivity and importance."""
    in_degree = {}
    out_degree = {}

    for node in nodes:
        in_degree[node["id"]] = 0
        out_degree[node["id"]] = 0

    for edge in edges:
        in_degree[edge["target_id"]] = in_degree.get(edge["target_id"], 0) + 1
        out_degree[edge["source_id"]] = out_degree.get(edge["source_id"], 0) + 1

    scored = []
    for node in nodes:
        score = in_degree.get(node["id"], 0) + out_degree.get(node["id"], 0)
        scored.append((score, node))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [n for _, n in scored[:limit]]


def _generate_mermaid_from_graph(nodes: list[dict], edges: list[dict]) -> str:
    """Generate Mermaid diagram from nodes and edges."""
    # Reuse knowledge_graph helper
    mermaid_nodes = [{"id": n["id"], "name": n["name"], "type": n["type"]} for n in nodes]
    mermaid_edges = [{"source": e["source_id"], "target": e["target_id"], "relation": e["type"]} for e in edges]
    return _generate_mermaid_visualization(mermaid_nodes, mermaid_edges)


@handle_tool_errors("research_understand_codebase")
async def research_understand_codebase(
    target: str,
    action: str = "graph",
    question: str = "",
    focus: str = "",
    max_files: int = 60,
    include_globs: list[str] | None = None,
    model: str = "auto",
) -> dict[str, Any]:
    """Turn any codebase into an interactive knowledge graph.

    Mirrors the Understand-Anything plugin schema (nodes: 21 types, edges: 35 types).
    Supports local paths, GitHub repos (owner/name), and git URLs.

    Args:
        target: Local path, GitHub repo (owner/name), or git URL
        action: "graph" | "ask" | "explain" | "onboard"
        question: Question to ask the graph (for action="ask")
        focus: File/function path to explain (for action="explain")
        max_files: Max files to analyze (1-500, default 60)
        include_globs: File patterns (default: code + doc extensions)
        model: LLM model to use ("auto" for cascade)

    Returns:
        Dict with action-specific structure:
        - graph: {graph_id, target, node_count, edge_count, node_types, mermaid, top_nodes}
        - ask: {question, answer, cited_nodes}
        - explain: {focus, explanation, related}
        - onboard: {onboarding, key_modules, entry_points}
    """
    graph_id = _generate_graph_id(target)
    graph_db = _init_graph_db(graph_id)

    try:
        if action == "graph":
            return await _action_graph(target, graph_id, graph_db, max_files, include_globs)
        elif action == "ask":
            if not question:
                return {"error": "question required for action='ask'"}
            return await _action_ask(graph_db, question)
        elif action == "explain":
            if not focus:
                return {"error": "focus required for action='explain'"}
            return await _action_explain(graph_db, focus)
        elif action == "onboard":
            return await _action_onboard(graph_db)
        else:
            return {"error": f"Unknown action: {action}. Use: graph, ask, explain, onboard"}
    except Exception as e:
        logger.error("understand_codebase failed: %s", e)
        return {"error": str(e), "tool": "research_understand_codebase"}


async def _action_graph(
    target: str, graph_id: str, graph_db: str, max_files: int, include_globs: list[str] | None
) -> dict[str, Any]:
    """Build knowledge graph from codebase."""
    root_path, was_cloned = _resolve_target(target)
    try:
        files = _walk_files(root_path, include_globs, max_files)
        all_nodes = []
        all_edges = []

        # Extract from each file
        for file_path, rel_path in files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            nodes, edges = await _extract_nodes_and_edges(file_path, content, root_path)
            all_nodes.extend(nodes)
            all_edges.extend(edges)

        # Dedup nodes by id
        nodes_by_id = {n["id"]: n for n in all_nodes}
        dedup_nodes = list(nodes_by_id.values())

        # Dedup edges
        edge_key_set = set()
        dedup_edges = []
        for e in all_edges:
            key = (e["source_id"], e["target_id"], e["type"])
            if key not in edge_key_set:
                dedup_edges.append(e)
                edge_key_set.add(key)

        # Store in DB
        _store_graph_in_db(graph_db, dedup_nodes, dedup_edges)

        # Generate mermaid for top nodes
        top_nodes = _find_top_nodes(dedup_nodes, dedup_edges, limit=20)
        mermaid = _generate_mermaid_from_graph(top_nodes, dedup_edges)

        # Collect node types distribution
        node_types_dist = {}
        for node in dedup_nodes:
            nt = node["type"]
            node_types_dist[nt] = node_types_dist.get(nt, 0) + 1

        return {
            "action": "graph",
            "graph_id": graph_id,
            "target": target,
            "node_count": len(dedup_nodes),
            "edge_count": len(dedup_edges),
            "node_types": node_types_dist,
            "mermaid": mermaid[:3000],  # Truncate for output
            "top_nodes": [{"id": n["id"], "name": n["name"], "type": n["type"], "summary": n["summary"]} for n in top_nodes[:10]],
            "files_analyzed": len(files),
        }
    finally:
        if was_cloned:
            shutil.rmtree(root_path, ignore_errors=True)


async def _action_ask(graph_db: str, question: str) -> dict[str, Any]:
    """Ask a question about the codebase using the graph."""
    nodes, edges = _load_graph_from_db(graph_db)

    if not nodes:
        return {"error": "Graph is empty. Run action='graph' first."}

    try:
        from loom.tools.llm.llm import _call_with_cascade

        # Search nodes for keyword matches
        q_lower = question.lower()
        relevant_nodes = [n for n in nodes if q_lower in n["name"].lower() or q_lower in n["summary"].lower()][:10]

        if not relevant_nodes:
            relevant_nodes = nodes[:10]

        context = "Graph nodes:\n"
        for node in relevant_nodes:
            context += f"- {node['type']}:{node['name']}: {node['summary']}\n"

        ask_prompt = f"""Using this codebase knowledge graph, answer the question:

{context}

Question: {question}

Provide a concise, specific answer based on the graph."""

        result = await _call_with_cascade(ask_prompt)
        answer = result.text if hasattr(result, "text") else str(result)

        return {
            "action": "ask",
            "question": question,
            "answer": answer[:1000],
            "cited_nodes": [{"id": n["id"], "name": n["name"], "type": n["type"]} for n in relevant_nodes],
        }
    except Exception as e:
        logger.error("ask action failed: %s", e)
        return {"error": str(e)}


async def _action_explain(graph_db: str, focus: str) -> dict[str, Any]:
    """Explain a specific file/function and its connections."""
    nodes, edges = _load_graph_from_db(graph_db)

    if not nodes:
        return {"error": "Graph is empty. Run action='graph' first."}

    try:
        from loom.tools.llm.llm import _call_with_cascade

        # Find node by focus
        focus_lower = focus.lower()
        focus_node = next((n for n in nodes if focus_lower in n["name"].lower() or focus in n["file_path"]), None)

        if not focus_node:
            return {"error": f"Could not find node matching '{focus}'"}

        # Find neighbors
        incoming = [e for e in edges if e["target_id"] == focus_node["id"]]
        outgoing = [e for e in edges if e["source_id"] == focus_node["id"]]

        related_nodes = []
        for e in incoming + outgoing:
            other_id = e["source_id"] if e["target_id"] == focus_node["id"] else e["target_id"]
            other = next((n for n in nodes if n["id"] == other_id), None)
            if other:
                related_nodes.append(other)

        context = f"Target: {focus_node['type']}:{focus_node['name']}\nSummary: {focus_node['summary']}\n\nRelated nodes:\n"
        for node in related_nodes[:10]:
            context += f"- {node['type']}:{node['name']}: {node['summary']}\n"

        explain_prompt = f"""Provide a deep-dive explanation of this codebase component:

{context}

Explain its role, how it connects to other components, and its architectural importance."""

        result = await _call_with_cascade(explain_prompt)
        explanation = result.text if hasattr(result, "text") else str(result)

        return {
            "action": "explain",
            "focus": focus,
            "explanation": explanation[:1500],
            "related": [{"id": n["id"], "name": n["name"], "type": n["type"]} for n in related_nodes[:10]],
        }
    except Exception as e:
        logger.error("explain action failed: %s", e)
        return {"error": str(e)}


async def _action_onboard(graph_db: str) -> dict[str, Any]:
    """Generate onboarding guide from the codebase graph."""
    nodes, edges = _load_graph_from_db(graph_db)

    if not nodes:
        return {"error": "Graph is empty. Run action='graph' first."}

    try:
        from loom.tools.llm.llm import _call_with_cascade

        # Find entry points (top-level files, modules)
        entry_points = [n for n in nodes if n["type"] in {"file", "module"}][:10]

        # Find key hubs (high connectivity)
        top_nodes = _find_top_nodes(nodes, edges, limit=10)

        context = "Key modules and entry points:\n"
        for node in entry_points + top_nodes:
            context += f"- {node['type']}:{node['name']}: {node['summary']}\n"

        onboard_prompt = f"""Create a concise onboarding guide for someone new to this codebase:

{context}

Cover:
1. Entry points (where to start)
2. Key modules and their roles
3. Main data flows and interactions
4. Architectural patterns
Keep it under 500 words."""

        result = await _call_with_cascade(onboard_prompt)
        onboarding = result.text if hasattr(result, "text") else str(result)

        return {
            "action": "onboard",
            "onboarding": onboarding[:1500],
            "key_modules": [{"id": n["id"], "name": n["name"], "type": n["type"]} for n in top_nodes[:10]],
            "entry_points": [{"id": n["id"], "name": n["name"], "file_path": n["file_path"]} for n in entry_points[:10]],
        }
    except Exception as e:
        logger.error("onboard action failed: %s", e)
        return {"error": str(e)}
