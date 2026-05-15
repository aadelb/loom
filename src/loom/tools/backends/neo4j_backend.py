"""Neo4j-backed graph via SQLite. Stores entities/relationships with FTS and traversal.

DEPRECATED: Use research_graph() unified interface instead.
- research_graph_store → use research_graph(action="merge", ...)
- research_graph_query → use research_graph(action="query", ...)
- research_graph_visualize → use research_graph(action="visualize", ...)
"""
from __future__ import annotations
import json, logging, sqlite3
from datetime import UTC, datetime
from loom.error_responses import handle_tool_errors
from loom.db_helpers import get_db_path, init_db, db_connection
from typing import Any

logger = logging.getLogger("loom.tools.neo4j_backend")
_GRAPH_DB = get_db_path("knowledge_graph")

def _init_graph_db() -> None:
	"""Initialize SQLite schema."""
	schema = """
	CREATE TABLE IF NOT EXISTS nodes (id INTEGER PRIMARY KEY, name TEXT UNIQUE, type TEXT, properties TEXT, created_at TEXT);
	CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(name, type, properties UNINDEXED);
	CREATE TABLE IF NOT EXISTS edges (id INTEGER PRIMARY KEY, source_id INTEGER, target_id INTEGER, relation TEXT, properties TEXT, created_at TEXT, FOREIGN KEY (source_id) REFERENCES nodes(id), FOREIGN KEY (target_id) REFERENCES nodes(id), UNIQUE(source_id, target_id, relation));
	CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
	CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
	"""
	init_db(_GRAPH_DB, schema)

@handle_tool_errors("research_graph_store")
def research_graph_store(entities: list[dict[str, Any]] | dict | str, relationships: list[dict[str, Any]] | dict | str) -> dict[str, Any]:
	"""Store entities and relationships in graph database.

	DEPRECATED: Use research_graph(action="merge", graphs=[...]) instead.

	Returns {nodes_created, edges_created, total_nodes, total_edges, timestamp}
	"""
	logger.warning(
		"research_graph_store is deprecated; use research_graph(action='merge', ...) instead"
	)

	# Coerce string or dict inputs to lists
	if isinstance(entities, str):
		entities = [{"name": entities, "type": "unknown", "properties": {}}]
	elif isinstance(entities, dict):
		entities = [entities]

	if isinstance(relationships, str):
		relationships = [{"source": "unknown", "target": relationships, "relation": "unknown", "properties": {}}]
	elif isinstance(relationships, dict):
		relationships = [relationships]

	_init_graph_db()
	try:
		with db_connection(_GRAPH_DB) as conn:
			c = conn.cursor()
			nodes_created = edges_created = 0
			now = datetime.now(UTC).isoformat()
			for entity in entities:
				name, entity_type = (entity.get("name") or "").strip(), (entity.get("type") or "").strip()
				if not name or not entity_type: continue
				props = json.dumps(entity.get("properties", {}))
				try:
					c.execute("INSERT INTO nodes (name, type, properties, created_at) VALUES (?, ?, ?, ?)", (name, entity_type, props, now))
					c.execute("INSERT INTO nodes_fts (name, type, properties) VALUES (?, ?, ?)", (name, entity_type, props))
					nodes_created += 1
				except sqlite3.IntegrityError: pass
			for rel in relationships:
				source, target, relation = (rel.get("source") or "").strip(), (rel.get("target") or "").strip(), (rel.get("relation") or "").strip()
				if not source or not target or not relation: continue
				props = json.dumps(rel.get("properties", {}))
				c.execute("SELECT id FROM nodes WHERE name = ?", (source,))
				source_row = c.fetchone()
				c.execute("SELECT id FROM nodes WHERE name = ?", (target,))
				target_row = c.fetchone()
				if source_row and target_row:
					try:
						c.execute("INSERT INTO edges (source_id, target_id, relation, properties, created_at) VALUES (?, ?, ?, ?, ?)", (source_row[0], target_row[0], relation, props, now))
						edges_created += 1
					except sqlite3.IntegrityError: pass
			conn.commit()
			c.execute("SELECT COUNT(*) FROM nodes")
			total_nodes = c.fetchone()[0]
			c.execute("SELECT COUNT(*) FROM edges")
			total_edges = c.fetchone()[0]
			return {"nodes_created": nodes_created, "edges_created": edges_created, "total_nodes": total_nodes, "total_edges": total_edges, "timestamp": now}
	except Exception as e:
		logger.error("Graph store failed: %s", e)
		raise

@handle_tool_errors("research_graph_query")
def research_graph_query(query: str, max_depth: int = 2) -> dict[str, Any]:
	"""Search and traverse the graph database.

	DEPRECATED: Use research_graph(action="query", search_query=...) instead.

	Returns {query, matches, paths, subgraph {nodes, edges}, path_count}
	"""
	logger.warning(
		"research_graph_query is deprecated; use research_graph(action='query', ...) instead"
	)
	max_depth = max(1, min(max_depth, 5))
	_init_graph_db()
	try:
		with db_connection(_GRAPH_DB) as conn:
			c = conn.cursor()
			safe_query = query.replace('"', '').replace("'", "").replace("*", "").replace("(", "").replace(")", "")
			fts_query = '"' + safe_query + '"'
			c.execute("SELECT DISTINCT n.id, n.name, n.type, n.properties FROM nodes n WHERE n.id IN (SELECT rowid FROM nodes_fts WHERE nodes_fts MATCH ?) OR n.name LIKE ? OR n.type LIKE ? LIMIT 100", (fts_query, f"%{safe_query}%", f"%{safe_query}%"))
			matches = []
			for row in c.fetchall():
				try:
					props = json.loads(row[3]) if row[3] else {}
				except (json.JSONDecodeError, ValueError):
					logger.warning("Malformed JSON in node properties: %s", row[0])
					props = {}
				matches.append({"id": row[0], "name": row[1], "type": row[2], "properties": props})
			subgraph_nodes, subgraph_edges, paths = {}, [], []
			for match in matches:
				subgraph_nodes[match["id"]] = match
				_traverse(c, match["id"], max_depth, 0, subgraph_nodes, subgraph_edges, paths, [match])
			return {"query": query, "matches": matches, "paths": paths[:50], "subgraph": {"nodes": list(subgraph_nodes.values()), "edges": subgraph_edges}, "path_count": len(paths)}
	except Exception as e:
		logger.error("Graph query failed: %s", e)
		raise

def _traverse(c: sqlite3.Cursor, node_id: int, max_depth: int, current_depth: int, nodes: dict[int, Any], edges: list[dict[str, Any]], paths: list[list[dict[str, Any]]], current_path: list[dict[str, Any]]) -> None:
	"""Recursively traverse graph."""
	c.execute("SELECT e.id, e.target_id, e.relation, e.properties, n.name, n.type, n.properties FROM edges e JOIN nodes n ON e.target_id = n.id WHERE e.source_id = ?", (node_id,))
	found_any = False
	for edge_row in c.fetchall():
		found_any = True
		edge_id, target_id, relation, edge_props, target_name, target_type, target_props = edge_row
		if target_id not in nodes:
			try:
				target_node_props = json.loads(target_props) if target_props else {}
			except (json.JSONDecodeError, ValueError):
				logger.warning("Malformed JSON in node properties: %s", target_id)
				target_node_props = {}
			nodes[target_id] = {"id": target_id, "name": target_name, "type": target_type, "properties": target_node_props}
		if not any(e["id"] == edge_id for e in edges):
			try:
				edge_props_dict = json.loads(edge_props) if edge_props else {}
			except (json.JSONDecodeError, ValueError):
				logger.warning("Malformed JSON in edge properties: %s", edge_id)
				edge_props_dict = {}
			edges.append({"id": edge_id, "source": node_id, "target": target_id, "relation": relation, "properties": edge_props_dict})
		if current_depth < max_depth:
			current_path.append(nodes[target_id])
			_traverse(c, target_id, max_depth, current_depth + 1, nodes, edges, paths, current_path)
			current_path.pop()
	if not found_any or current_depth >= max_depth:
		paths.append(current_path[:])

@handle_tool_errors("research_graph_visualize")
def research_graph_visualize(entity: str) -> dict[str, Any]:
	"""Return ego-graph (1-hop neighbors) around an entity.

	DEPRECATED: Use research_graph(action="visualize", nodes=[...], edges=[...]) instead.

	Returns {center, nodes, edges, node_count, edge_count}
	"""
	logger.warning(
		"research_graph_visualize is deprecated; use research_graph(action='visualize', ...) instead"
	)
	_init_graph_db()
	try:
		with db_connection(_GRAPH_DB) as conn:
			c = conn.cursor()
			c.execute("SELECT id, name, type, properties FROM nodes WHERE name = ?", (entity,))
			center_row = c.fetchone()
			if not center_row:
				return {"center": None, "nodes": [], "edges": [], "node_count": 0, "edge_count": 0, "error": f"Entity '{entity}' not found"}
			center_id, center_name, center_type, center_props = center_row
			try:
				center_props_dict = json.loads(center_props) if center_props else {}
			except (json.JSONDecodeError, ValueError):
				logger.warning("Malformed JSON in center node properties: %s", center_id)
				center_props_dict = {}
			center = {"id": center_id, "name": center_name, "type": center_type, "properties": center_props_dict}
			nodes: dict[int, Any] = {center_id: center}
			edges_list: list[dict[str, Any]] = []
			c.execute("SELECT e.id, e.target_id, e.relation, e.properties, n.name, n.type, n.properties FROM edges e JOIN nodes n ON e.target_id = n.id WHERE e.source_id = ?", (center_id,))
			for edge_row in c.fetchall():
				edge_id, target_id, relation, edge_props, target_name, target_type, target_props = edge_row
				if target_id not in nodes:
					try:
						target_props_dict = json.loads(target_props) if target_props else {}
					except (json.JSONDecodeError, ValueError):
						logger.warning("Malformed JSON in target node properties: %s", target_id)
						target_props_dict = {}
					nodes[target_id] = {"id": target_id, "name": target_name, "type": target_type, "properties": target_props_dict}
				try:
					edge_props_dict = json.loads(edge_props) if edge_props else {}
				except (json.JSONDecodeError, ValueError):
					logger.warning("Malformed JSON in edge properties: %s", edge_id)
					edge_props_dict = {}
				edges_list.append({"id": edge_id, "source": center_id, "target": target_id, "relation": relation, "properties": edge_props_dict})
			c.execute("SELECT e.id, e.source_id, e.relation, e.properties, n.name, n.type, n.properties FROM edges e JOIN nodes n ON e.source_id = n.id WHERE e.target_id = ?", (center_id,))
			for edge_row in c.fetchall():
				edge_id, source_id, relation, edge_props, source_name, source_type, source_props = edge_row
				if source_id not in nodes:
					try:
						source_props_dict = json.loads(source_props) if source_props else {}
					except (json.JSONDecodeError, ValueError):
						logger.warning("Malformed JSON in source node properties: %s", source_id)
						source_props_dict = {}
					nodes[source_id] = {"id": source_id, "name": source_name, "type": source_type, "properties": source_props_dict}
				try:
					edge_props_dict = json.loads(edge_props) if edge_props else {}
				except (json.JSONDecodeError, ValueError):
					logger.warning("Malformed JSON in edge properties: %s", edge_id)
					edge_props_dict = {}
				edges_list.append({"id": edge_id, "source": source_id, "target": center_id, "relation": relation, "properties": edge_props_dict})
			return {"center": center, "nodes": list(nodes.values()), "edges": edges_list, "node_count": len(nodes), "edge_count": len(edges_list)}
	except Exception as e:
		logger.error("Graph visualization failed: %s", e)
		raise
