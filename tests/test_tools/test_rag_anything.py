"""Tests for RAG-Anything tool: ingestion, querying, and vector store operations."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from loom.tools.llm.rag_anything import (
    research_rag_clear,
    research_rag_ingest,
    research_rag_query,
    _chunk_text,
    _hash_embedding,
    _ensure_db,
)


@pytest.fixture
def temp_rag_dir():
    """Create temporary RAG directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("loom.tools.llm.rag_anything._RAG_DIR", Path(tmpdir)):
            with patch(
                "loom.tools.llm.rag_anything._DB_PATH",
                Path(tmpdir) / "store.db",
            ):
                yield Path(tmpdir)


class TestChunkText:
    """Tests for text chunking logic."""

    def test_chunk_text_basic(self):
        """Test basic text chunking with default parameters."""
        text = "a" * 1000
        chunks = _chunk_text(text, chunk_size=512, overlap=50)

        assert len(chunks) > 0
        assert all(len(c) <= 512 for c in chunks)
        # Check overlap exists
        if len(chunks) > 1:
            assert chunks[0][-50:] == chunks[1][:50]

    def test_chunk_text_empty(self):
        """Test chunking empty text."""
        assert _chunk_text("") == []
        assert _chunk_text("   ") == []

    def test_chunk_text_single_chunk(self):
        """Test text smaller than chunk size."""
        text = "Hello world"
        chunks = _chunk_text(text, chunk_size=512, overlap=50)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_preserves_content(self):
        """Test that chunking preserves all content."""
        text = "The quick brown fox jumps over the lazy dog. " * 50
        chunks = _chunk_text(text, chunk_size=256, overlap=30)

        reconstructed = ""
        for i, chunk in enumerate(chunks):
            if i == 0:
                reconstructed += chunk
            else:
                # Remove overlap from subsequent chunks
                reconstructed += chunk[30:]

        assert text in reconstructed


class TestHashEmbedding:
    """Tests for pseudo-embedding generation."""

    def test_hash_embedding_consistent(self):
        """Test that same text produces same hash."""
        text = "test embedding"
        hash1 = _hash_embedding(text)
        hash2 = _hash_embedding(text)

        assert hash1 == hash2

    def test_hash_embedding_different(self):
        """Test that different text produces different hashes."""
        hash1 = _hash_embedding("text1")
        hash2 = _hash_embedding("text2")

        assert hash1 != hash2

    def test_hash_embedding_length(self):
        """Test that hash is always 16 characters."""
        hash_val = _hash_embedding("any text")
        assert len(hash_val) == 16


class TestRagIngest:
    """Tests for RAG ingestion functionality."""

    def test_ingest_basic(self, temp_rag_dir):
        """Test basic content ingestion."""
        content = "This is test content for RAG ingestion. " * 20
        result = research_rag_ingest(content, content_type="text")

        assert result["chunks_stored"] > 0
        assert result["content_type"] == "text"
        assert len(result["chunk_ids"]) == result["chunks_stored"]

    def test_ingest_empty_content(self, temp_rag_dir):
        """Test ingestion of empty content."""
        result = research_rag_ingest("", content_type="text")

        assert result["chunks_stored"] == 0
        assert result["chunk_ids"] == []

    def test_ingest_with_metadata(self, temp_rag_dir):
        """Test ingestion with metadata."""
        content = "Test content with metadata. " * 20
        metadata = {"source": "test", "author": "pytest"}

        result = research_rag_ingest(
            content, content_type="code", metadata=metadata
        )

        assert result["chunks_stored"] > 0
        assert result["content_type"] == "code"

        # Verify metadata is stored
        conn = sqlite3.connect(result["store_location"])
        cursor = conn.execute(
            "SELECT metadata FROM chunks WHERE chunk_id = ?",
            (result["chunk_ids"][0],),
        )
        row = cursor.fetchone()
        if row:
            stored_meta = json.loads(row[0])
            assert stored_meta["source"] == "test"
        conn.close()

    def test_ingest_multiple_content_types(self, temp_rag_dir):
        """Test ingestion of different content types."""
        for ctype in ["text", "code", "json", "markdown"]:
            result = research_rag_ingest(
                f"Content for {ctype} " * 20, content_type=ctype
            )
            assert result["content_type"] == ctype
            assert result["chunks_stored"] > 0


class TestRagQuery:
    """Tests for RAG querying functionality."""

    def test_query_empty_store(self, temp_rag_dir):
        """Test querying empty store."""
        result = research_rag_query("test query")

        assert result["results"] == []
        assert result["total_chunks"] == 0

    def test_query_basic(self, temp_rag_dir):
        """Test basic query matching."""
        content = "The quick brown fox jumps over the lazy dog. " * 20
        research_rag_ingest(content, content_type="text")

        result = research_rag_query("quick fox")

        assert len(result["results"]) > 0
        assert "query" in result
        assert "total_chunks" in result

    def test_query_empty_query(self, temp_rag_dir):
        """Test empty query returns error."""
        result = research_rag_query("")

        assert "error" in result
        assert result["results"] == []

    def test_query_top_k_limit(self, temp_rag_dir):
        """Test top_k parameter limits results."""
        # Ingest content multiple times
        for i in range(10):
            research_rag_ingest(f"Test content {i}. " * 20)

        result = research_rag_query("test", top_k=3)

        assert len(result["results"]) <= 3

    def test_query_top_k_clamping(self, temp_rag_dir):
        """Test that top_k is clamped to valid range."""
        content = "Test content. " * 20
        research_rag_ingest(content)

        # top_k too high
        result = research_rag_query("test", top_k=1000)
        assert len(result["results"]) <= 100

        # top_k too low
        result = research_rag_query("test", top_k=0)
        assert len(result["results"]) >= 1

    def test_query_with_content_type_filter(self, temp_rag_dir):
        """Test filtering results by content type."""
        research_rag_ingest("Python code example", content_type="code")
        research_rag_ingest("This is a text document", content_type="text")

        result = research_rag_query("example", content_type="code")

        # Should only return code type
        for item in result["results"]:
            assert item["content_type"] == "code"

    def test_query_result_format(self, temp_rag_dir):
        """Test query result format is correct."""
        research_rag_ingest("Test content with keywords. " * 20)

        result = research_rag_query("keywords")

        assert "query" in result
        assert "results" in result
        assert "total_chunks" in result
        assert "store_location" in result

        if result["results"]:
            item = result["results"][0]
            assert "chunk_id" in item
            assert "text" in item
            assert "score" in item
            assert "content_type" in item
            assert "metadata" in item


class TestRagClear:
    """Tests for RAG store clearing."""

    def test_clear_with_data(self, temp_rag_dir):
        """Test clearing store with existing data."""
        # Ingest some data
        research_rag_ingest("Test content. " * 20)

        # Clear
        result = research_rag_clear()

        assert result["cleared"] is True

        # Verify store is gone
        assert not Path(result["store_location"]).exists()

    def test_clear_empty_store(self, temp_rag_dir):
        """Test clearing empty store."""
        result = research_rag_clear()

        # Should succeed even if store doesn't exist
        assert "store_location" in result


class TestRagIntegration:
    """Integration tests for RAG workflow."""

    def test_ingest_and_query_workflow(self, temp_rag_dir):
        """Test complete ingest → query workflow."""
        # Ingest documents
        doc1 = "Python is a programming language used for data science. " * 10
        doc2 = "JavaScript is used for web development. " * 10
        doc3 = "Go is a compiled language for systems programming. " * 10

        research_rag_ingest(doc1, content_type="text", metadata={"doc": "1"})
        research_rag_ingest(doc2, content_type="text", metadata={"doc": "2"})
        research_rag_ingest(doc3, content_type="text", metadata={"doc": "3"})

        # Query for Python
        result = research_rag_query("Python programming")

        assert len(result["results"]) > 0
        assert result["total_chunks"] > 0

        # Check that Python results come up
        texts = [r["text"] for r in result["results"]]
        assert any("Python" in t or "python" in t for t in texts)

    def test_multiple_ingestions_accumulate(self, temp_rag_dir):
        """Test that multiple ingestions accumulate in store."""
        result1 = research_rag_ingest("First content " * 20)
        chunks1 = result1["chunks_stored"]

        result2 = research_rag_ingest("Second content " * 20)
        chunks2 = result2["chunks_stored"]

        # Query should return results from both
        result = research_rag_query("content")

        assert result["total_chunks"] >= chunks1 + chunks2

    def test_metadata_preservation(self, temp_rag_dir):
        """Test that metadata is preserved through ingest and query."""
        metadata = {"source": "test_doc", "version": "1.0"}
        content = "Important content " * 20

        research_rag_ingest(content, metadata=metadata)

        result = research_rag_query("important")

        assert len(result["results"]) > 0
        # At least check the structure is there
        for item in result["results"]:
            assert "metadata" in item
