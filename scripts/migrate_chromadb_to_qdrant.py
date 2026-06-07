#!/usr/bin/env python3
"""Migrate ChromaDB data to Qdrant — bypasses version incompatibility.

Reads 70,500 text chunks directly from ChromaDB's SQLite storage,
re-embeds with MiniLM-L6-v2 (384-dim), and upserts to a new Qdrant
collection 'ummro_chromadb_migrated'.

This bypasses the ChromaDB Python API version mismatch by reading
raw SQLite data directly.

Usage:
    PYTHONPATH=/opt/loom-v3/src python3 scripts/migrate_chromadb_to_qdrant.py

Author: Ahmed Adel Bakr Alderai
"""
import asyncio
import json
import sqlite3
import sys
import time

import aiohttp

CHROMADB_PATH = "/data/chromadb-storage/chroma.sqlite3"
QDRANT_URL = "http://localhost:6333"
COLLECTION = "ummro_chromadb_migrated"
VECTOR_DIM = 384
BATCH_SIZE = 100


async def create_collection():
    """Create Qdrant collection if not exists."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{QDRANT_URL}/collections/{COLLECTION}") as resp:
            if resp.status == 200:
                data = await resp.json()
                count = data.get("result", {}).get("points_count", 0)
                print(f"Collection exists with {count} points")
                return count

        body = {
            "vectors": {"size": VECTOR_DIM, "distance": "Cosine"},
            "on_disk_payload": True,
        }
        async with session.put(
            f"{QDRANT_URL}/collections/{COLLECTION}", json=body
        ) as resp:
            data = await resp.json()
            print(f"Created collection: {data.get('status')}")
            return 0


async def upsert_batch(points: list) -> bool:
    """Upsert a batch of points to Qdrant."""
    async with aiohttp.ClientSession() as session:
        async with session.put(
            f"{QDRANT_URL}/collections/{COLLECTION}/points",
            json={"points": points},
        ) as resp:
            data = await resp.json()
            return data.get("status") == "ok" or "completed" in str(data)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts with MiniLM-L6-v2."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return [emb.tolist() for emb in embeddings]


def extract_chunks(db_path: str, offset: int = 0, limit: int = 1000) -> list[dict]:
    """Extract text chunks with metadata from ChromaDB SQLite."""
    db = sqlite3.connect(db_path)
    cur = db.cursor()

    cur.execute(f"""
        SELECT e.id, e.embedding_id, fc.c0
        FROM embeddings e
        JOIN embedding_fulltext_search_content fc ON e.id = fc.rowid
        WHERE fc.c0 IS NOT NULL AND LENGTH(fc.c0) > 50
        ORDER BY e.id
        LIMIT {limit} OFFSET {offset}
    """)
    rows = cur.fetchall()

    chunks = []
    for row_id, emb_id, text in rows:
        cur.execute(
            "SELECT key, string_value FROM embedding_metadata WHERE id=?",
            (row_id,),
        )
        meta = {r[0]: r[1] for r in cur.fetchall() if r[1]}

        chunks.append({
            "id": row_id,
            "text": text[:2000],
            "path": meta.get("path", ""),
            "ext": meta.get("file_ext", ""),
            "indexed_at": meta.get("indexed_at", ""),
        })

    db.close()
    return chunks


async def main():
    start = time.time()
    print(f"ChromaDB → Qdrant Migration")
    print(f"Source: {CHROMADB_PATH}")
    print(f"Target: {QDRANT_URL}/collections/{COLLECTION}")

    existing = await create_collection()

    db = sqlite3.connect(CHROMADB_PATH)
    cur = db.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM embedding_fulltext_search_content WHERE c0 IS NOT NULL AND LENGTH(c0) > 50"
    )
    total = cur.fetchone()[0]
    db.close()
    print(f"Total chunks to migrate: {total}")

    if existing >= total * 0.9:
        print("Already migrated (>90% present). Skipping.")
        return

    migrated = 0
    offset = existing

    while offset < total:
        chunks = extract_chunks(CHROMADB_PATH, offset=offset, limit=BATCH_SIZE)
        if not chunks:
            break

        texts = [c["text"] for c in chunks]
        vectors = embed_texts(texts)

        points = []
        for chunk, vector in zip(chunks, vectors):
            points.append({
                "id": chunk["id"],
                "vector": vector,
                "payload": {
                    "text": chunk["text"],
                    "path": chunk["path"],
                    "ext": chunk["ext"],
                    "indexed_at": chunk["indexed_at"],
                    "source": "chromadb_migration",
                },
            })

        success = await upsert_batch(points)
        if success:
            migrated += len(points)
        else:
            print(f"  UPSERT FAILED at offset {offset}")
            break

        offset += len(chunks)
        elapsed = time.time() - start
        rate = migrated / max(elapsed, 1) * 60
        print(f"  Migrated {migrated}/{total} ({migrated*100//total}%) rate={rate:.0f}/min")

    print(f"\nDone. Migrated {migrated} chunks in {time.time()-start:.0f}s")
    print(f"Collection '{COLLECTION}' now has {existing + migrated} points")


if __name__ == "__main__":
    asyncio.run(main())
