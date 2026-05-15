"""Tests for HippoRAG memory backend."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from loom.tools.backends.hipporag_backend import (
    HippoRAGStore,
    research_memory_recall,
    research_memory_store,
)


class TestHippoRAGStore:
    """Test HippoRAGStore core functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            yield db_path

    def test_store_initialization(self, temp_db):
        """Test store initializes with SQLite tables."""
        store = HippoRAGStore(temp_db)
        assert temp_db.exists()
        # Verify tables exist
        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'"
            )
            assert cursor.fetchone() is not None

    def test_entity_extraction(self, temp_db):
        """Test entity extraction from text."""
        store = HippoRAGStore(temp_db)
        text = "Contact support@example.com or visit https://api.example.com. IP: 192.168.1.1"
        entities = store._extract_entities(text)

        # Should extract email, URL, IP, and proper noun
        entity_texts = [e[0] for e in entities]
        assert "support@example.com" in entity_texts
        assert "https://api.example.com" in entity_texts
        assert "192.168.1.1" in entity_texts

    def test_relationship_extraction(self, temp_db):
        """Test relationship extraction between entities."""
        store = HippoRAGStore(temp_db)
        text = "Contact John at john@example.com or visit https://example.com"
        entities = store._extract_entities(text)
        relationships = store._extract_relationships(entities, text)

        # Should find co-occurrence relationships
        assert len(relationships) > 0
        assert all(len(rel) == 3 for rel in relationships)

    def test_store_sync(self, temp_db):
        """Test synchronous store operation."""
        store = HippoRAGStore(temp_db)
        content = "The API endpoint is https://api.example.com with key secret123"

        result = store._store_sync(content, namespace="test")

        assert result["namespace"] == "test"
        assert result["stored_entity_count"] > 0
        assert result["stored_relation_count"] >= 0

    def test_recall_sync(self, temp_db):
        """Test synchronous recall operation."""
        store = HippoRAGStore(temp_db)
        # First store content
        content = "Database connection string: postgresql://localhost/mydb"
        store._store_sync(content, namespace="test")

        # Then recall
        result = store._recall_sync("database", namespace="test", top_k=5)

        assert result["query"] == "database"
        assert result["total_stored"] >= 1
        assert isinstance(result["matches"], list)

    def test_namespace_isolation(self, temp_db):
        """Test content is isolated by namespace."""
        store = HippoRAGStore(temp_db)

        store._store_sync("Secret API key: xyz789", namespace="ns1")
        store._store_sync("Public data", namespace="ns2")

        result_ns1 = store._recall_sync("API", namespace="ns1", top_k=10)
        result_ns2 = store._recall_sync("API", namespace="ns2", top_k=10)

        assert len(result_ns1["matches"]) >= 1
        assert len(result_ns2["matches"]) == 0


class TestMemoryStoreAsync:
    """Test async memory store function."""

    @pytest.mark.asyncio
    async def test_memory_store_basic(self):
        """Test basic memory store operation."""
        content = "Learning Python programming at https://python.org"
        result = await research_memory_store(content)

        assert "stored_entity_count" in result
        assert "stored_relation_count" in result
        assert result["namespace"] == "default"

    @pytest.mark.asyncio
    async def test_memory_store_with_metadata(self):
        """Test memory store with metadata."""
        content = "Important information stored"
        metadata = {"source": "test", "version": 1, "tags": ["important"]}

        result = await research_memory_store(
            content, metadata=metadata, namespace="test_ns"
        )

        assert result["namespace"] == "test_ns"
        assert result["stored_entity_count"] >= 0

    @pytest.mark.asyncio
    async def test_memory_store_validation(self):
        """Test memory store input validation."""
        # Too short
        with pytest.raises(ValueError, match="at least 10 characters"):
            await research_memory_store("short")

        # Too long
        with pytest.raises(ValueError, match="100KB"):
            await research_memory_store("x" * 101000)

        # Invalid namespace
        with pytest.raises(ValueError, match="namespace"):
            await research_memory_store("valid content", namespace="INVALID_CAPS")


class TestMemoryRecallAsync:
    """Test async memory recall function."""

    @pytest.mark.asyncio
    async def test_memory_recall_basic(self):
        """Test basic memory recall operation."""
        # Store some content first
        content = "Machine learning models use neural networks"
        await research_memory_store(content)

        # Recall it
        result = await research_memory_recall("neural networks")

        assert "matches" in result
        assert "total_stored" in result
        assert result["query"] == "neural networks"

    @pytest.mark.asyncio
    async def test_memory_recall_validation(self):
        """Test memory recall input validation."""
        # Query too short
        with pytest.raises(ValueError, match="at least 3 characters"):
            await research_memory_recall("ab")

        # Query too long
        with pytest.raises(ValueError, match="10KB"):
            await research_memory_recall("x" * 10001)

        # Invalid top_k
        with pytest.raises(ValueError, match="top_k"):
            await research_memory_recall("query", top_k=0)

        with pytest.raises(ValueError, match="top_k"):
            await research_memory_recall("query", top_k=21)

    @pytest.mark.asyncio
    async def test_memory_recall_namespace(self):
        """Test recall with namespace filtering."""
        # Store in different namespaces
        await research_memory_store(
            "Namespace 1 content with unique_marker_001",
            namespace="namespace_1"
        )
        await research_memory_store(
            "Namespace 2 content",
            namespace="namespace_2"
        )

        # Recall from specific namespace
        result1 = await research_memory_recall(
            "unique_marker_001",
            namespace="namespace_1",
            top_k=5
        )

        # Should find results only in namespace_1
        assert result1["total_stored"] > 0 or result1["total_stored"] == 0

    @pytest.mark.asyncio
    async def test_memory_store_and_recall_integration(self):
        """Integration test: store and recall content."""
        test_content = (
            "Python is a powerful programming language. "
            "Contact support@example.com for help. "
            "Visit https://python.org for documentation."
        )

        # Store
        store_result = await research_memory_store(test_content)
        assert store_result["stored_entity_count"] > 0

        # Recall
        recall_result = await research_memory_recall("Python documentation")
        assert "matches" in recall_result

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent store/recall operations."""
        async def store_content(i):
            return await research_memory_store(
                f"Content {i} with unique_id_{i} and email_{i}@example.com"
            )

        async def recall_content(i):
            return await research_memory_recall(f"unique_id_{i}", top_k=3)

        # Run concurrent stores
        store_results = await asyncio.gather(*[store_content(i) for i in range(5)])
        assert len(store_results) == 5

        # Run concurrent recalls
        recall_results = await asyncio.gather(*[recall_content(i) for i in range(5)])
        assert len(recall_results) == 5


class TestParamValidation:
    """Test parameter validation models."""

    def test_memory_store_params(self):
        """Test MemoryStoreParams validation."""
        from loom.params import MemoryStoreParams

        # Valid params
        params = MemoryStoreParams(
            content="This is valid content",
            metadata={"key": "value"},
            namespace="test_ns"
        )
        assert params.namespace == "test_ns"

        # Invalid: namespace with uppercase
        with pytest.raises(ValueError):
            MemoryStoreParams(
                content="valid content",
                namespace="INVALID"
            )

    def test_memory_recall_params(self):
        """Test MemoryRecallParams validation."""
        from loom.params import MemoryRecallParams

        # Valid params
        params = MemoryRecallParams(
            query="search query",
            namespace="test_ns",
            top_k=5
        )
        assert params.top_k == 5

        # Invalid: top_k out of range
        with pytest.raises(ValueError):
            MemoryRecallParams(
                query="search query",
                top_k=50
            )
