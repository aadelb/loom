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
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from loom.error_responses import handle_tool_errors

try:
    from loom.text_utils import truncate
except ImportError:
    def truncate(text, max_chars=500, *, suffix="..."):
        if len(text) <= max_chars: return text
        return text[:max_chars - len(suffix)] + suffix

logger = logging.getLogger("loom.tools.hipporag")

# Constants for validation
MAX_CONTENT_SIZE = 100000  # 100KB
MAX_QUERY_SIZE = 10000    # 10KB
MAX_TOP_K = 20
MIN_CONTENT_SIZE = 10
MIN_QUERY_SIZE = 3
MAX_NAMESPACE_SIZE = 32
MIN_NAMESPACE_SIZE = 1

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
        self._lock = threading.RLock()  # Thread-safe initialization
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with nodes, edges, and FTS5 tables.

        Creates: nodes (entities), edges (relationships), content (full text),
        and content_fts (FTS5 virtual index) tables with proper schema versioning.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")  # 30s timeout on lock contention
            conn.execute("PRAGMA user_version=1")  # Schema version marker
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

        Deduplicates by (entity_text, entity_type) pair to avoid counting
        the same entity multiple times across extraction passes.

        Args:
            text: input text to extract from

        Returns:
            List of (entity_text, entity_type) tuples, deduplicated by type
        """
        entities = []
        seen: set[tuple[str, str]] = set()  # Deduplicate by (text, type) pair
        for entity_type, pattern in ENTITY_PATTERNS.items():
            for match in re.finditer(pattern, text):
                entity_text = match.group(0).strip()
                if entity_text and (entity_text, entity_type) not in seen:
                    entities.append((entity_text, entity_type))
                    seen.add((entity_text, entity_type))
        return entities

    def _extract_relationships(
        self, entities: list[tuple[str, str]], text: str
    ) -> list[tuple[str, str, str]]:
        """Extract relationships between entities using proximity heuristics.

        Creates co-occurrence edges only for entity pairs within 100 chars.
        Deduplicates to prevent double-counting.

        Args:
            entities: list of (entity_text, entity_type) tuples
            text: source text for context

        Returns:
            List of (source_entity, relation_type, target_entity) tuples
        """
        relationships = []
        entity_positions: dict[str, list[int]] = {}
        for entity_text, entity_type in entities:
            positions = [m.start() for m in re.finditer(re.escape(entity_text), text)]
            entity_positions[entity_text] = positions

        # Co-occurrence: entities within 100 chars (first occurrence only)
        entity_list = [e[0] for e in entities]
        seen_pairs: set[tuple[str, str]] = set()
        for i, entity1 in enumerate(entity_list):
            for entity2 in entity_list[i + 1 :]:
                # Skip duplicate pairs (directional: entity1 → entity2)
                pair_key = (entity1, entity2)
                if pair_key in seen_pairs:
                    continue
                pos1 = entity_positions.get(entity1, [0])[0]
                pos2 = entity_positions.get(entity2, [0])[0]
                if abs(pos1 - pos2) < 100:
                    relationships.append((entity1, "co_occurs_with", entity2))
                    seen_pairs.add(pair_key)
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
        """Synchronous store implementation.

        Extracts entities and relationships, stores in SQLite with proper
        error handling and transaction management.

        Args:
            content: text to store
            metadata: optional metadata
            namespace: isolation namespace

        Returns:
            Dict with entity/relationship counts
        """
        now = datetime.now(UTC).isoformat()
        entities = self._extract_entities(content)
        relationships = self._extract_relationships(entities, content)

        with sqlite3.connect(str(self.db_path)) as conn:
            # Store content and get its rowid
            metadata_json = json.dumps(metadata or {})
            cursor = conn.execute(
                "INSERT INTO content (namespace, content, metadata, created_at) VALUES (?, ?, ?, ?)",
                (namespace, content, metadata_json, now),
            )
            content_rowid = cursor.lastrowid
            if content_rowid is None:
                raise sqlite3.IntegrityError("Failed to insert content")

            # Index in FTS5 using known rowid (not time-based query)
            try:
                conn.execute(
                    "INSERT INTO content_fts (rowid, content) VALUES (?, ?)",
                    (content_rowid, content),
                )
            except sqlite3.IntegrityError:
                logger.warning(f"FTS5 index already exists for rowid {content_rowid}")

            # Store entities (nodes)
            node_ids: dict[str, int] = {}
            for entity_text, entity_type in entities:
                entity_id = f"{namespace}:{entity_type}:{entity_text.lower()}"
                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO nodes
                        (entity_id, entity_type, entity_text, namespace, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (entity_id, entity_type, entity_text, namespace, now, now),
                    )
                    # Fetch node id (must exist after INSERT OR IGNORE)
                    node_cursor = conn.execute(
                        "SELECT id FROM nodes WHERE entity_id = ?", (entity_id,)
                    )
                    node_row = node_cursor.fetchone()
                    if node_row is None:
                        raise sqlite3.IntegrityError(f"Node not found after insert: {entity_id}")
                    node_ids[entity_text] = node_row[0]
                except sqlite3.Error as e:
                    logger.error(f"Failed to store entity {entity_id}: {e}")
                    raise

            # Store relationships (edges)
            for source, rel_type, target in relationships:
                if source in node_ids and target in node_ids:
                    try:
                        conn.execute(
                            """
                            INSERT INTO edges (source_id, target_id, relation_type, namespace, created_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (node_ids[source], node_ids[target], rel_type, namespace, now),
                        )
                    except sqlite3.Error as e:
                        logger.error(f"Failed to store edge {source}->{target}: {e}")
                        raise
            conn.commit()

        return {
            "stored_entity_count": len(entities),  # Count unique (text, type) pairs
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
        """Synchronous recall implementation.

        Uses LIKE search (FTS5 content-sync has schema limitations in standard SQLite).
        Returns results with truncation flag to indicate incomplete content.

        Args:
            query: search term
            namespace: isolation namespace
            top_k: max results

        Returns:
            Dict with matches (list of {content, is_truncated, stored_at, metadata}),
            total_stored count, and original query
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            # LIKE search (FTS5 virtual-table has schema sync issues in standard SQLite)
            search_term = f"%{query}%"
            cursor = conn.execute(
                """
                SELECT id, content, metadata, created_at, LENGTH(content) as content_len
                FROM content
                WHERE namespace = ? AND content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (namespace, search_term, top_k),
            )
            results = []
            max_preview_chars = 500
            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row["metadata"] or "{}")
                except json.JSONDecodeError:
                    metadata = {}
                content_text = row["content"]
                is_truncated = len(content_text) > max_preview_chars
                results.append(
                    {
                        "content": truncate(content_text, max_preview_chars),
                        "is_truncated": is_truncated,
                        "stored_at": row["created_at"],
                        "metadata": metadata,
                    }
                )

            # Get total count
            cursor = conn.execute(
                "SELECT COUNT(*) as cnt FROM content WHERE namespace = ?", (namespace,)
            )
            total_row = cursor.fetchone()
            total_stored = total_row["cnt"] if total_row else 0

        return {
            "matches": results,
            "total_stored": total_stored,
            "query": query,
        }


# Module-level singleton with thread-safe initialization
_store: HippoRAGStore | None = None
_store_lock = threading.Lock()


def get_hipporag_store() -> HippoRAGStore:
    """Get or create module-level HippoRAG store in a thread-safe manner.

    Uses double-checked locking to avoid contention after initialization.
    """
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = HippoRAGStore()
    return _store


@handle_tool_errors("research_memory_store")
async def research_memory_store(
    content: str, metadata: dict[str, Any] | None = None, namespace: str = "default"
) -> dict[str, Any]:
    """Store content in persistent knowledge graph for long-term memory.

    Extracts entities and relationships from content automatically.
    Uses UTF-8 encoding and stores in UTC timezone.

    Args:
        content: text content to store (required, 10-100KB)
        metadata: optional metadata dict to attach to content
        namespace: graph namespace for isolation (default: 'default', 1-32 chars)

    Returns:
        Dict with:
        - stored_entity_count: number of unique entities extracted
        - stored_relation_count: number of relationships found
        - namespace: the namespace used
        - error: error message if validation failed
    """
    try:
        # Validate content
        if not content or len(content.strip()) < MIN_CONTENT_SIZE:
            raise ValueError(f"content must be at least {MIN_CONTENT_SIZE} characters")
        if len(content) > MAX_CONTENT_SIZE:
            raise ValueError(f"content exceeds {MAX_CONTENT_SIZE // 1024}KB limit")

        # Validate namespace (alphanumeric + underscore only)
        if not isinstance(namespace, str) or not namespace:
            raise ValueError("namespace must be non-empty string")
        if len(namespace) > MAX_NAMESPACE_SIZE:
            raise ValueError(f"namespace exceeds {MAX_NAMESPACE_SIZE} character limit")
        if not namespace.replace("_", "").replace("-", "").isalnum():
            raise ValueError("namespace must contain only alphanumeric, underscore, dash")

        # Validate metadata
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError("metadata must be dict or None")

        store = get_hipporag_store()
        return await store.store(content, metadata, namespace)
    except ValueError as exc:
        logger.warning(f"Validation failed in research_memory_store: {exc}")
        return {"error": str(exc), "tool": "research_memory_store"}
    except sqlite3.Error as exc:
        logger.error(f"Database error in research_memory_store: {exc}")
        return {"error": f"Database error: {str(exc)}", "tool": "research_memory_store"}


@handle_tool_errors("research_memory_recall")
async def research_memory_recall(
    query: str, namespace: str = "default", top_k: int = 5
) -> dict[str, Any]:
    """Retrieve relevant memories using graph-based similarity search.

    Searches stored content using substring matching (LIKE query).
    Results are sorted by recency (most recent first).

    Args:
        query: search query (required, 3-10KB)
        namespace: graph namespace to search (default: 'default', 1-32 chars)
        top_k: max results to return (default: 5, max: 20)

    Returns:
        Dict with:
        - matches: list of {content, is_truncated, stored_at, metadata}
        - total_stored: total memories in namespace
        - query: the search query
        - error: error message if validation failed
    """
    try:
        # Validate query
        if not query or len(query.strip()) < MIN_QUERY_SIZE:
            raise ValueError(f"query must be at least {MIN_QUERY_SIZE} characters")
        if len(query) > MAX_QUERY_SIZE:
            raise ValueError(f"query exceeds {MAX_QUERY_SIZE // 1024}KB limit")

        # Validate namespace
        if not isinstance(namespace, str) or not namespace:
            raise ValueError("namespace must be non-empty string")
        if len(namespace) > MAX_NAMESPACE_SIZE:
            raise ValueError(f"namespace exceeds {MAX_NAMESPACE_SIZE} character limit")
        if not namespace.replace("_", "").replace("-", "").isalnum():
            raise ValueError("namespace must contain only alphanumeric, underscore, dash")

        # Validate top_k
        if not isinstance(top_k, int) or top_k < 1 or top_k > MAX_TOP_K:
            raise ValueError(f"top_k must be 1-{MAX_TOP_K}")

        store = get_hipporag_store()
        return await store.recall(query, namespace, top_k)
    except ValueError as exc:
        logger.warning(f"Validation failed in research_memory_recall: {exc}")
        return {"error": str(exc), "tool": "research_memory_recall"}
    except sqlite3.Error as exc:
        logger.error(f"Database error in research_memory_recall: {exc}")
        return {"error": f"Database error: {str(exc)}", "tool": "research_memory_recall"}
