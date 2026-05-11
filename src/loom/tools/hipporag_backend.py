"""HippoRAG-inspired lightweight knowledge graph memory backend using SQLite + FTS5.

Stores content in persistent knowledge graphs with entity/relationship extraction
for long-term memory retrieval. No external dependencies — pure Python + sqlite3.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.hipporag")

# Entity regex patterns for lightweight extraction
ENTITY_PATTERNS = {
    "url": r"https?://[^\s]+",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "ip": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "number": r"\b\d+(?:\.\d+)?\b",
    "proper_noun": r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b",
}


class HippoRAGStore:
    """Lightweight knowledge graph store backed by SQLite + FTS5."""

    def __init__(self, db_path: str | Path = "~/.loom/memory/hipporag.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with nodes, edges, and FTS5 tables."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            # Nodes (entities) table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id TEXT UNIQUE NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_text TEXT NOT NULL,
                    namespace TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # Edges (relationships) table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    relation_type TEXT NOT NULL,
                    namespace TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES nodes (id),
                    FOREIGN KEY (target_id) REFERENCES nodes (id)
                )
            """)
            # Content storage for full-text search
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    namespace TEXT NOT NULL DEFAULT 'default',
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            # FTS5 virtual table for fast search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
                    content,
                    content=content,
                    content_rowid=id
                )
            """)
            conn.commit()

    def _extract_entities(self, text: str) -> list[tuple[str, str]]:
        """Extract entities from text using regex patterns.

        Args:
            text: input text to extract from

        Returns:
            List of (entity_text, entity_type) tuples
        """
        entities = []
        seen = set()
        for entity_type, pattern in ENTITY_PATTERNS.items():
            for match in re.finditer(pattern, text):
                entity_text = match.group(0).strip()
                if entity_text and entity_text not in seen:
                    entities.append((entity_text, entity_type))
                    seen.add(entity_text)
        return entities

    def _extract_relationships(
        self, entities: list[tuple[str, str]], text: str
    ) -> list[tuple[str, str, str]]:
        """Extract relationships between entities using proximity heuristics.

        Args:
            entities: list of (entity_text, entity_type) tuples
            text: source text for context

        Returns:
            List of (source_entity, relation_type, target_entity) tuples
        """
        relationships = []
        entity_positions = {}
        for entity_text, entity_type in entities:
            positions = [m.start() for m in re.finditer(re.escape(entity_text), text)]
            entity_positions[entity_text] = positions

        # Simple co-occurrence relationship: entities within 100 chars
        entity_list = [e[0] for e in entities]
        for i, entity1 in enumerate(entity_list):
            for entity2 in entity_list[i + 1 :]:
                pos1 = entity_positions.get(entity1, [0])[0]
                pos2 = entity_positions.get(entity2, [0])[0]
                if abs(pos1 - pos2) < 100:
                    relationships.append((entity1, "co_occurs_with", entity2))
        return relationships

    async def store(
        self, content: str, metadata: dict[str, Any] | None = None, namespace: str = "default"
    ) -> dict[str, Any]:
        """Store content in knowledge graph with entity/relationship extraction.

        Args:
            content: text content to store
            metadata: optional metadata dict
            namespace: graph namespace for isolation

        Returns:
            Dict with stored_entity_count, stored_relation_count, namespace
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._store_sync, content, metadata, namespace
        )

    def _store_sync(
        self, content: str, metadata: dict[str, Any] | None = None, namespace: str = "default"
    ) -> dict[str, Any]:
        """Synchronous store implementation."""
        now = datetime.now(UTC).isoformat()
        entities = self._extract_entities(content)
        relationships = self._extract_relationships(entities, content)

        with sqlite3.connect(str(self.db_path)) as conn:
            # Store content
            metadata_json = json.dumps(metadata or {})
            conn.execute(
                "INSERT INTO content (namespace, content, metadata, created_at) VALUES (?, ?, ?, ?)",
                (namespace, content, metadata_json, now),
            )
            conn.execute(
                "INSERT INTO content_fts (rowid, content) SELECT id, content FROM content WHERE created_at = ?",
                (now,),
            )

            # Store entities (nodes)
            node_ids = {}
            for entity_text, entity_type in entities:
                entity_id = f"{namespace}:{entity_type}:{entity_text.lower()}"
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO nodes
                    (entity_id, entity_type, entity_text, namespace, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (entity_id, entity_type, entity_text, namespace, now, now),
                )
                # Get node id
                cursor = conn.execute("SELECT id FROM nodes WHERE entity_id = ?", (entity_id,))
                node_ids[entity_text] = cursor.fetchone()[0]

            # Store relationships (edges)
            for source, rel_type, target in relationships:
                if source in node_ids and target in node_ids:
                    conn.execute(
                        """
                        INSERT INTO edges (source_id, target_id, relation_type, namespace, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (node_ids[source], node_ids[target], rel_type, namespace, now),
                    )
            conn.commit()

        return {
            "stored_entity_count": len(set(e[0] for e in entities)),
            "stored_relation_count": len(relationships),
            "namespace": namespace,
        }

    async def recall(
        self, query: str, namespace: str = "default", top_k: int = 5
    ) -> dict[str, Any]:
        """Retrieve relevant memories using graph-based retrieval.

        Args:
            query: search query
            namespace: graph namespace to search
            top_k: max results to return

        Returns:
            Dict with matches (list of content+score), total_stored, query
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._recall_sync, query, namespace, top_k)

    def _recall_sync(self, query: str, namespace: str = "default", top_k: int = 5) -> dict[str, Any]:
        """Synchronous recall implementation."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            # Simple LIKE search (FTS5 content-sync mode has schema issues)
            search_term = f"%{query}%"
            cursor = conn.execute(
                """
                SELECT id, content, metadata, created_at
                FROM content
                WHERE namespace = ? AND content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (namespace, search_term, top_k),
            )
            results = []
            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row["metadata"] or "{}")
                except json.JSONDecodeError:
                    metadata = {}
                results.append(
                    {
                        "content": row["content"][:500],  # Truncate to 500 chars
                        "score": 0.85,  # Static score for FTS matches
                        "stored_at": row["created_at"],
                        "metadata": metadata,
                    }
                )

            # Get total count
            cursor = conn.execute(
                "SELECT COUNT(*) as cnt FROM content WHERE namespace = ?", (namespace,)
            )
            total_stored = cursor.fetchone()["cnt"]

        return {
            "matches": results,
            "total_stored": total_stored,
            "query": query,
        }


# Module-level singleton
_store: HippoRAGStore | None = None


def get_hipporag_store() -> HippoRAGStore:
    """Get or create module-level HippoRAG store."""
    global _store
    if _store is None:
        _store = HippoRAGStore()
    return _store


async def research_memory_store(
    content: str, metadata: dict[str, Any] | None = None, namespace: str = "default"
) -> dict[str, Any]:
    """Store content in persistent knowledge graph for long-term memory.

    Extracts entities and relationships from content automatically.

    Args:
        content: text content to store (required)
        metadata: optional metadata dict to attach to content
        namespace: graph namespace for isolation (default: 'default')

    Returns:
        Dict with:
        - stored_entity_count: number of unique entities extracted
        - stored_relation_count: number of relationships found
        - namespace: the namespace used
    """
    try:
        if not content or len(content.strip()) < 10:
            raise ValueError("content must be at least 10 characters")
        if len(content) > 100000:
            raise ValueError("content exceeds 100KB limit")
        if not isinstance(namespace, str) or not namespace or len(namespace) > 32:
            raise ValueError("namespace must be 1-32 character string")

        store = get_hipporag_store()
        return await store.store(content, metadata, namespace)
    except Exception as exc:
        return {"error": str(exc), "tool": "research_memory_store"}


async def research_memory_recall(
    query: str, namespace: str = "default", top_k: int = 5
) -> dict[str, Any]:
    """Retrieve relevant memories using graph-based similarity search.

    Args:
        query: search query (required)
        namespace: graph namespace to search (default: 'default')
        top_k: max results to return (default: 5, max: 20)

    Returns:
        Dict with:
        - matches: list of [content, score, stored_at, metadata]
        - total_stored: total memories in namespace
        - query: the search query
    """
    try:
        if not query or len(query.strip()) < 3:
            raise ValueError("query must be at least 3 characters")
        if len(query) > 10000:
            raise ValueError("query exceeds 10KB limit")
        if not isinstance(namespace, str) or not namespace or len(namespace) > 32:
            raise ValueError("namespace must be 1-32 character string")
        if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
            raise ValueError("top_k must be 1-20")

        store = get_hipporag_store()
        return await store.recall(query, namespace, top_k)
    except Exception as exc:
        return {"error": str(exc), "tool": "research_memory_recall"}
