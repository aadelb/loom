"""research_graph and research_knowledge_graph — Unified graph interface.

Provides a unified graph tool with action-based dispatch:
- action="extract" (default): Build knowledge graphs from research data (Semantic Scholar, Wikipedia, Wikidata)
- action="query": Query existing graph in SQLite backend
- action="merge": Merge two or more graphs
- action="visualize": Generate DOT/mermaid graph visualization

Also exposes legacy research_knowledge_graph for backward compatibility.
"""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import asyncio
import json
import logging
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import httpx

from loom.http_helpers import fetch_json
from loom.db_helpers import get_db_path, init_db, db_connection

logger = logging.getLogger("loom.tools.knowledge_graph")

_GRAPH_DB = get_db_path("knowledge_graph")


async def _search_semantic_scholar(
	client: httpx.AsyncClient, query: str
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str]]]:
	"""Search Semantic Scholar and extract nodes (papers, authors) and edges.

	Returns:
		(nodes, edges) where edges are tuples of (source_id, target_id, relation)
	"""
	url = (
		f"https://api.semanticscholar.org/graph/v1/paper/search?"
		f"query={quote(query)}&limit=10&"
		f"fields=title,abstract,authors,references,citations,year"
	)
	data = await fetch_json(client, url, timeout=20.0)
	if not data or "papers" not in data:
		return [], []

	nodes: list[dict[str, Any]] = []
	edges: list[tuple[str, str, str]] = []
	paper_ids = set()

	for paper in data.get("papers", []):
		paper_id = paper.get("paperId", "")
		if not paper_id or paper_id in paper_ids:
			continue
		paper_ids.add(paper_id)

		# Add paper node
		nodes.append({
			"id": f"paper_{paper_id}",
			"type": "paper",
			"name": paper.get("title", "Unknown"),
			"metadata": {
				"year": paper.get("year"),
				"abstract": paper.get("abstract", ""),
				"citation_count": paper.get("citationCount", 0),
				"semantic_scholar_id": paper_id,
			},
		})

		# Add author nodes and edges
		for author in paper.get("authors", []):
			author_id = author.get("authorId", "")
			author_name = author.get("name", "")
			if author_id and author_name:
				author_node_id = f"author_{author_id}"
				nodes.append({
					"id": author_node_id,
					"type": "author",
					"name": author_name,
					"metadata": {"semantic_scholar_id": author_id},
				})
				edges.append((author_node_id, f"paper_{paper_id}", "authored"))

		# Add citation edges
		for ref in paper.get("references", [])[:3]:  # Limit references
			ref_id = ref.get("paperId", "")
			if ref_id:
				edges.append((f"paper_{paper_id}", f"paper_{ref_id}", "cites"))

	return nodes, edges


async def _search_wikipedia(
	client: httpx.AsyncClient, query: str
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str]]]:
	"""Search Wikipedia and extract concept nodes and relationships."""
	url = (
		f"https://en.wikipedia.org/w/api.php?"
		f"action=query&titles={quote(query)}&"
		f"prop=links|categories&pllimit=50&cllimit=50&"
		f"format=json"
	)
	data = await fetch_json(client, url)
	if not data or "query" not in data:
		return [], []

	nodes: list[dict[str, Any]] = []
	edges: list[tuple[str, str, str]] = []
	concept_ids = set()

	pages = data.get("query", {}).get("pages", {})
	for page_id, page_data in pages.items():
		if "missing" in page_data:
			continue

		concept_name = page_data.get("title", "")
		if concept_name and concept_name not in concept_ids:
			concept_ids.add(concept_name)
			concept_node_id = f"concept_{concept_name.replace(' ', '_')}"

			nodes.append({
				"id": concept_node_id,
				"type": "concept",
				"name": concept_name,
				"metadata": {
					"wikipedia_pageid": page_id,
					"source": "wikipedia",
				},
			})

			# Add category nodes and edges
			for cat in page_data.get("categories", []):
				cat_name = cat.get("title", "").replace("Category:", "")
				if cat_name:
					cat_node_id = f"category_{cat_name.replace(' ', '_')}"
					nodes.append({
						"id": cat_node_id,
						"type": "category",
						"name": cat_name,
						"metadata": {"source": "wikipedia"},
					})
					edges.append((concept_node_id, cat_node_id, "belongs_to"))

			# Add link edges
			for link in page_data.get("links", [])[:5]:  # Limit related links
				link_name = link.get("title", "")
				if link_name:
					link_node_id = f"concept_{link_name.replace(' ', '_')}"
					edges.append((concept_node_id, link_node_id, "related_to"))

	return nodes, edges


async def _search_wikidata(
	client: httpx.AsyncClient, query: str
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str]]]:
	"""Search Wikidata for structured entity data."""
	url = (
		f"https://www.wikidata.org/w/api.php?"
		f"action=wbsearchentities&search={quote(query)}&"
		f"language=en&format=json&limit=10"
	)
	data = await fetch_json(client, url)
	if not data or "search" not in data:
		return [], []

	nodes: list[dict[str, Any]] = []
	edges: list[tuple[str, str, str]] = []
	entity_ids = set()

	for entity in data.get("search", []):
		entity_id = entity.get("id", "")
		entity_label = entity.get("label", "")
		entity_desc = entity.get("description", "")

		if entity_id and entity_id not in entity_ids:
			entity_ids.add(entity_id)
			nodes.append({
				"id": f"entity_{entity_id}",
				"type": "entity",
				"name": entity_label,
				"metadata": {
					"wikidata_id": entity_id,
					"description": entity_desc,
					"source": "wikidata",
				},
			})

	return nodes, edges


def _deduplicate_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Deduplicate nodes by name and id, keeping metadata from all duplicates."""
	seen_names: dict[str, dict[str, Any]] = {}
	seen_ids: dict[str, dict[str, Any]] = {}

	for node in nodes:
		node_id = node["id"]
		node_name = node["name"].lower().strip()

		# Already seen by exact ID
		if node_id in seen_ids:
			continue

		# Merge if seen by name
		if node_name in seen_names:
			existing = seen_names[node_name]
			# Merge metadata
			if "metadata" in node and "metadata" in existing:
				existing["metadata"].update(node["metadata"])
			continue

		# New node
		seen_names[node_name] = node
		seen_ids[node_id] = node

	return list(seen_ids.values())


def _deduplicate_edges(
	edges: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
	"""Remove duplicate edges."""
	return list(set(edges))


def _init_graph_db() -> None:
	"""Initialize SQLite schema for graph storage."""
	schema = """
	CREATE TABLE IF NOT EXISTS nodes (
		id INTEGER PRIMARY KEY,
		node_id TEXT UNIQUE,
		name TEXT,
		type TEXT,
		properties TEXT,
		created_at TEXT
	);

	CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts
	USING fts5(node_id, name, type, properties UNINDEXED);

	CREATE TABLE IF NOT EXISTS edges (
		id INTEGER PRIMARY KEY,
		source_id TEXT,
		target_id TEXT,
		relation TEXT,
		properties TEXT,
		created_at TEXT,
		UNIQUE(source_id, target_id, relation)
	);

	CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
	CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
	"""
	init_db(_GRAPH_DB, schema)


def _graph_extract_nodes_and_edges(
	data: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
	"""Extract nodes and edges from graph data dict."""
	nodes = data.get("nodes", [])
	edges = data.get("edges", [])
	return nodes, edges


def _generate_dot_visualization(
	nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> str:
	"""Generate DOT format graph visualization."""
	lines = ["digraph G {"]
	lines.append('  rankdir=LR;')
	lines.append('  node [shape=box, style=rounded];')

	# Add nodes
	node_ids = set()
	for node in nodes:
		node_id = node.get("id", "").replace('"', '\\"')
		node_name = node.get("name", "").replace('"', '\\"')
		node_type = node.get("type", "unknown")
		node_ids.add(node.get("id"))
		lines.append(f'  "{node_id}" [label="{node_name}", type="{node_type}"];')

	# Add edges
	for edge in edges:
		src = edge.get("source", "").replace('"', '\\"')
		tgt = edge.get("target", "").replace('"', '\\"')
		relation = edge.get("relation", "").replace('"', '\\"')
		if src in node_ids and tgt in node_ids:
			lines.append(f'  "{src}" -> "{tgt}" [label="{relation}"];')

	lines.append("}")
	return "\n".join(lines)


def _generate_mermaid_visualization(
	nodes: list[dict[str, Any]], edges: list[dict[str, Any]]
) -> str:
	"""Generate Mermaid format graph visualization."""
	lines = ["graph LR"]

	# Add nodes with types as comments
	node_ids = set()
	for node in nodes:
		node_id = node.get("id", "")
		node_name = node.get("name", "")
		node_type = node.get("type", "")
		node_ids.add(node_id)
		safe_id = node_id.replace("-", "_").replace(" ", "_")
		safe_name = node_name[:30].replace('"', "'")
		if node_type:
			lines.append(f"  {safe_id}[\"{safe_name}<br/>{node_type}\"]")
		else:
			lines.append(f"  {safe_id}[\"{safe_name}\"]")

	# Add edges
	for edge in edges:
		src = edge.get("source", "")
		tgt = edge.get("target", "")
		relation = edge.get("relation", "")
		if src in node_ids and tgt in node_ids:
			safe_src = src.replace("-", "_").replace(" ", "_")
			safe_tgt = tgt.replace("-", "_").replace(" ", "_")
			if relation:
				lines.append(f"  {safe_src} -->|{relation}| {safe_tgt}")
			else:
				lines.append(f"  {safe_src} --> {safe_tgt}")

	return "\n".join(lines)


async def _graph_action_extract(
	query: str,
	max_nodes: int = 100,
	sources: list[str] | None = None,
) -> dict[str, Any]:
	"""Extract knowledge graph from research data."""
	if sources is None:
		sources = ["semantic_scholar", "wikipedia", "wikidata"]

	max_nodes = max(1, min(max_nodes, 500))
	sources = [s.lower().strip() for s in sources if s]

	logger.info("graph extract query=%s sources=%s", query[:50], sources)

	async with httpx.AsyncClient(
		follow_redirects=True,
		headers={"User-Agent": "Loom-Research/1.0"},
		timeout=30.0,
	) as client:
		tasks = []

		if "semantic_scholar" in sources:
			tasks.append(_search_semantic_scholar(client, query))
		else:
			tasks.append(asyncio.sleep(0, result=([], [])))  # type: ignore[arg-type]

		if "wikipedia" in sources:
			tasks.append(_search_wikipedia(client, query))
		else:
			tasks.append(asyncio.sleep(0, result=([], [])))  # type: ignore[arg-type]

		if "wikidata" in sources:
			tasks.append(_search_wikidata(client, query))
		else:
			tasks.append(asyncio.sleep(0, result=([], [])))  # type: ignore[arg-type]

		results = await asyncio.gather(*tasks, return_exceptions=True)

		all_nodes: list[dict[str, Any]] = []
		all_edges: list[tuple[str, str, str]] = []

		for result in results:
			if isinstance(result, tuple) and not isinstance(result, Exception):
				nodes, edges = result
				all_nodes.extend(nodes)
				all_edges.extend(edges)

		dedup_nodes = _deduplicate_nodes(all_nodes)
		dedup_edges = _deduplicate_edges(all_edges)

		if len(dedup_nodes) > max_nodes:
			dedup_nodes = dedup_nodes[:max_nodes]

		node_ids = {n["id"] for n in dedup_nodes}
		dedup_edges = [
			e for e in dedup_edges
			if e[0] in node_ids and e[1] in node_ids
		]

		edge_dicts = [
			{"source": src, "target": tgt, "relation": rel}
			for src, tgt, rel in dedup_edges
		]

		return {
			"action": "extract",
			"query": query,
			"nodes": dedup_nodes,
			"edges": edge_dicts,
			"total_nodes": len(dedup_nodes),
			"total_edges": len(edge_dicts),
			"sources_used": sources,
		}


def _graph_action_query(search_query: str, max_depth: int = 2) -> dict[str, Any]:
	"""Query existing graph from SQLite backend."""
	max_depth = max(1, min(max_depth, 5))
	_init_graph_db()
	with db_connection(_GRAPH_DB) as conn:
		c = conn.cursor()
		try:
			c.execute(
				"""SELECT DISTINCT n.node_id, n.name, n.type, n.properties
				FROM nodes n
				WHERE n.node_id IN (
					SELECT node_id FROM nodes_fts WHERE nodes_fts MATCH ? || '*'
				) OR n.name LIKE ? OR n.type LIKE ?
				LIMIT 100""",
				(search_query, f"%{search_query}%", f"%{search_query}%"),
			)
			matches = [
				{
					"id": row[0],
					"name": row[1],
					"type": row[2],
					"properties": json.loads(row[3]) if row[3] else {},
				}
				for row in c.fetchall()
			]

			subgraph_nodes: dict[str, dict[str, Any]] = {}
			subgraph_edges: list[dict[str, Any]] = []

			for match in matches:
				subgraph_nodes[match["id"]] = match

			return {
				"action": "query",
				"query": search_query,
				"matches": matches,
				"subgraph": {"nodes": list(subgraph_nodes.values()), "edges": subgraph_edges},
				"match_count": len(matches),
			}
		except Exception as e:
			logger.error("Graph query failed: %s", e)
			return {"action": "query", "query": search_query, "error": str(e), "matches": []}


def _graph_action_merge(
	graphs: list[dict[str, Any]],
) -> dict[str, Any]:
	"""Merge multiple graphs into one."""
	merged_nodes: dict[str, dict[str, Any]] = {}
	merged_edges: list[dict[str, Any]] = []

	for graph in graphs:
		if not isinstance(graph, dict):
			continue

		nodes, edges = _graph_extract_nodes_and_edges(graph)

		# Merge nodes with deduplication by id
		for node in nodes:
			node_id = node.get("id")
			if node_id:
				if node_id in merged_nodes:
					# Merge metadata
					if "metadata" in node and "metadata" in merged_nodes[node_id]:
						merged_nodes[node_id]["metadata"].update(node["metadata"])
				else:
					merged_nodes[node_id] = node

		# Merge edges
		seen_edges = set()
		for edge in edges:
			src = edge.get("source")
			tgt = edge.get("target")
			rel = edge.get("relation", "")
			edge_key = (src, tgt, rel)
			if edge_key not in seen_edges:
				merged_edges.append(edge)
				seen_edges.add(edge_key)

	return {
		"action": "merge",
		"nodes": list(merged_nodes.values()),
		"edges": merged_edges,
		"total_nodes": len(merged_nodes),
		"total_edges": len(merged_edges),
		"graphs_merged": len(graphs),
	}


def _graph_action_visualize(
	nodes: list[dict[str, Any]],
	edges: list[dict[str, Any]],
	format: Literal["dot", "mermaid"] = "mermaid",
) -> dict[str, Any]:
	"""Generate graph visualization."""
	if format == "dot":
		viz = _generate_dot_visualization(nodes, edges)
	elif format == "mermaid":
		viz = _generate_mermaid_visualization(nodes, edges)
	else:
		viz = _generate_mermaid_visualization(nodes, edges)

	return {
		"action": "visualize",
		"format": format,
		"visualization": viz,
		"node_count": len(nodes),
		"edge_count": len(edges),
	}


@handle_tool_errors("research_graph")
async def research_graph(
	action: Literal["extract", "query", "merge", "visualize"] = "extract",
	query: str | None = None,
	max_nodes: int = 100,
	sources: list[str] | None = None,
	graphs: list[dict[str, Any]] | None = None,
	nodes: list[dict[str, Any]] | None = None,
	edges: list[dict[str, Any]] | None = None,
	search_query: str | None = None,
	max_depth: int = 2,
	format: Literal["dot", "mermaid"] = "mermaid",
) -> dict[str, Any]:
	"""Unified graph interface with action-based dispatch.

	This tool provides a unified interface for graph operations:
	- extract: Build knowledge graphs from Semantic Scholar, Wikipedia, Wikidata
	- query: Search and traverse existing graph in SQLite backend
	- merge: Merge two or more graphs
	- visualize: Generate DOT or Mermaid visualization

	Args:
		action: Operation to perform (extract, query, merge, visualize)
		query: Search query for extraction (used with action="extract")
		max_nodes: Max nodes to return (1-500, used with action="extract")
		sources: List of sources for extraction (semantic_scholar, wikipedia, wikidata)
		graphs: List of graphs to merge (used with action="merge")
		nodes: Node list for visualization (used with action="visualize")
		edges: Edge list for visualization (used with action="visualize")
		search_query: Search query for graph lookup (used with action="query")
		max_depth: Traversal depth for query (1-5, used with action="query")
		format: Visualization format (dot, mermaid, used with action="visualize")

	Returns:
		Dict with action-specific structure. All responses include "action" key.
	"""
	try:
		if action == "extract":
			if not query:
				return {"action": "extract", "error": "query parameter required for extract action"}
			return await _graph_action_extract(query, max_nodes, sources)

		elif action == "query":
			if not search_query:
				return {"action": "query", "error": "search_query parameter required for query action"}
			return _graph_action_query(search_query, max_depth)

		elif action == "merge":
			if not graphs:
				return {"action": "merge", "error": "graphs parameter required for merge action"}
			return _graph_action_merge(graphs)

		elif action == "visualize":
			if not nodes or not edges:
				return {"action": "visualize", "error": "nodes and edges parameters required for visualize action"}
			return _graph_action_visualize(nodes, edges, format)

		else:
			return {"action": action, "error": f"Unknown action: {action}"}
	except Exception as exc:
		return {"error": str(exc), "tool": "research_graph"}


@handle_tool_errors("research_knowledge_graph")
async def research_knowledge_graph(
	query: str,
	max_nodes: int = 100,
	sources: list[str] | None = None,
) -> dict[str, Any]:
	"""Build a knowledge graph from research data.

	DEPRECATED: Use research_graph(action="extract", ...) instead.

	Combines Semantic Scholar (papers & authors), Wikipedia (concepts & categories),
	and Wikidata (structured entities) to construct an entity-relationship graph.
	Automatically deduplicates nodes by name and merges metadata.

	Args:
		query: search query (e.g., "machine learning safety")
		max_nodes: maximum number of nodes to return (1-500)
		sources: list of sources to include (semantic_scholar, wikipedia, wikidata).
			If None, uses all sources.

	Returns:
		Dict with keys:
		- query: original query
		- nodes: list of {id, type, name, metadata}
		- edges: list of {source, target, relation}
		- total_nodes: count of deduplicated nodes
		- total_edges: count of edges
		- sources_used: list of sources queried
	"""
	try:
		logger.warning(
			"research_knowledge_graph is deprecated; use research_graph(action='extract', ...) instead"
		)
		result = await _graph_action_extract(query, max_nodes, sources)
		# Remove action key for backward compatibility
		result.pop("action", None)
		return result
	except Exception as exc:
		return {"error": str(exc), "tool": "research_knowledge_graph"}
