"""RAG-Anything: Universal RAG with SQLite FTS5 backend."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any
from loom.error_responses import handle_tool_errors
from loom.db_helpers import get_db_path, init_db, db_connection

logger = logging.getLogger("loom.tools.rag_anything")
_DB_PATH = get_db_path("rag_store")


def _ensure_db() -> None:
	"""Create RAG database with FTS5."""
	schema = """
	CREATE TABLE IF NOT EXISTS chunks(
		chunk_id TEXT PRIMARY KEY, text TEXT NOT NULL, content_type TEXT NOT NULL,
		metadata TEXT, embedding_hash TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);

	CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
		chunk_id UNINDEXED, text, content_type UNINDEXED, metadata UNINDEXED);
	"""
	init_db(_DB_PATH, schema)


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
	"""Split text into overlapping chunks."""
	if not (text and text.strip()):
		return []
	chunks, step = [], chunk_size - overlap
	for i in range(0, len(text), step):
		chunk = text[i : i + chunk_size]
		if chunk.strip():
			chunks.append(chunk)
		if i + chunk_size >= len(text):
			break
	return chunks


def _hash_embedding(text: str) -> str:
	"""SHA-256 hash for pseudo-embeddings."""
	return hashlib.sha256(text.encode()).hexdigest()[:16]


@handle_tool_errors("research_rag_ingest")
def research_rag_ingest(
	content: str, content_type: str = "text", metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
	"""Ingest content into RAG store. Returns: chunks_stored, content_type, chunk_ids, store_location."""
	if not (content and content.strip()):
		return {"chunks_stored": 0, "content_type": content_type, "chunk_ids": [], "store_location": str(_DB_PATH)}

	metadata = metadata or {}
	chunks, chunk_ids = _chunk_text(content), []
	_ensure_db()

	try:
		with db_connection(_DB_PATH) as conn:
			for chunk_text in chunks:
				chunk_id, embedding_hash = str(uuid.uuid4())[:8], _hash_embedding(chunk_text)
				meta_json = json.dumps(metadata)
				conn.execute(
					"INSERT INTO chunks(chunk_id, text, content_type, metadata, embedding_hash) VALUES(?, ?, ?, ?, ?)",
					(chunk_id, chunk_text, content_type, meta_json, embedding_hash),
				)
				conn.execute(
					"INSERT INTO chunks_fts(chunk_id, text, content_type, metadata) VALUES(?, ?, ?, ?)",
					(chunk_id, chunk_text, content_type, meta_json),
				)
				chunk_ids.append(chunk_id)

			conn.commit()
		logger.info("rag_ingest_success chunks_stored=%s content_type=%s", len(chunk_ids), content_type)
		return {"chunks_stored": len(chunk_ids), "content_type": content_type, "chunk_ids": chunk_ids, "store_location": str(_DB_PATH)}
	except sqlite3.Error as e:
		logger.error("rag_ingest_failed error=%s", str(e))
		return {"chunks_stored": 0, "error": str(e), "store_location": str(_DB_PATH)}


@handle_tool_errors("research_rag_query")
def research_rag_query(
	query: str, top_k: int = 5, content_type: str | None = None
) -> dict[str, Any]:
	"""Search RAG store. Returns: query, results, total_chunks, query_hash."""
	if not (query and query.strip()):
		return {"query": query, "results": [], "total_chunks": 0, "error": "Empty query"}

	query_text, top_k = query.strip(), max(1, min(top_k, 100))
	_ensure_db()

	try:
		with db_connection(_DB_PATH) as conn:
			fts_query = " OR ".join(re.findall(r"\w+", query_text)) or query_text
			sql = "SELECT c.chunk_id, c.text, c.content_type, c.metadata FROM chunks_fts f JOIN chunks c ON f.chunk_id = c.chunk_id WHERE f.text MATCH ?"
			params: list[Any] = [fts_query]

			if content_type:
				sql += " AND c.content_type = ?"
				params.append(content_type)

			sql += " ORDER BY rank DESC LIMIT ?"
			params.append(top_k)

			rows = conn.execute(sql, params).fetchall()
			results = [
				{
					"chunk_id": chunk_id,
					"text": text[:200] + ("..." if len(text) > 200 else ""),
					"score": 1.0,
					"content_type": ctype,
					"metadata": json.loads(meta_json) if meta_json else {},
				}
				for chunk_id, text, ctype, meta_json in rows
			]

			total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
			total_chunks = total[0] if total else 0

		logger.info("rag_query_success query_len=%s results_found=%s", len(query_text), len(results))
		return {
			"query": query_text,
			"results": results,
			"total_chunks": total_chunks,
			"store_location": str(_DB_PATH),
			"query_hash": _hash_embedding(query_text),
		}
	except sqlite3.Error as e:
		logger.error("rag_query_failed error=%s query=%s", str(e), query_text)
		return {"query": query_text, "results": [], "error": str(e), "store_location": str(_DB_PATH)}


@handle_tool_errors("research_rag_clear")
def research_rag_clear() -> dict[str, Any]:
	"""Clear RAG store. Returns: cleared, store_location."""
	try:
		if _DB_PATH.exists():
			_DB_PATH.unlink()
			logger.info("rag_clear_success")
			return {"cleared": True, "store_location": str(_DB_PATH)}
		return {"cleared": False, "message": "Store not found", "store_location": str(_DB_PATH)}
	except OSError as e:
		logger.error("rag_clear_failed error=%s", str(e))
		return {"cleared": False, "error": str(e), "store_location": str(_DB_PATH)}
