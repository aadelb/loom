"""Fix research_uae_law meta-tool to use local DB first."""
path = "/data/opt/research-toolbox/loom-legal/src/loom_legal/tools/uae_law.py"
content = open(path).read()

DB_FUNC = '''
import sqlite3
import asyncio

async def _search_uae_law_db(query, limit=10):
    def _sync():
        try:
            db = sqlite3.connect("/opt/research-toolbox/uae-law-mcp/data/database.db")
            db.row_factory = sqlite3.Row
            try:
                rows = db.execute(
                    "SELECT p.content, p.provision_ref, d.title as doc_title "
                    "FROM legal_provisions p JOIN legal_documents d ON p.document_id=d.id "
                    "WHERE p.id IN (SELECT rowid FROM provisions_fts WHERE provisions_fts MATCH ?) LIMIT ?",
                    (query, limit)).fetchall()
            except Exception:
                rows = db.execute(
                    "SELECT p.content, p.provision_ref, d.title as doc_title "
                    "FROM legal_provisions p JOIN legal_documents d ON p.document_id=d.id "
                    "WHERE p.content LIKE ? LIMIT ?",
                    (f"%{query}%", limit)).fetchall()
            db.close()
            return [{"title_en": r["doc_title"][:200], "provision": r["provision_ref"] or "", "content": r["content"][:500], "source": "uae_law_db"} for r in rows]
        except Exception:
            return []
    return await asyncio.to_thread(_sync)

'''

# Insert DB function before main function
idx = content.find("async def research_uae_law")
content = content[:idx] + DB_FUNC + content[idx:]

# Find docstring end
doc1 = content.find('"""', content.find("async def research_uae_law"))
doc2 = content.find('"""', doc1 + 3) + 3
next_line = content.find("\n", doc2) + 1

DB_FIRST = '''
    # PRIMARY: Local DB (instant, 113K provisions)
    try:
        db_results = await _search_uae_law_db(query, limit=10)
        if db_results:
            return {
                "query": query,
                "total_results": len(db_results),
                "results": db_results,
                "source": "uae_law_db",
            }
    except Exception:
        pass
    # Fallback to chained tools below
'''

content = content[:next_line] + DB_FIRST + content[next_line:]
open(path, "w").write(content)
print("Fixed research_uae_law with DB-first")
