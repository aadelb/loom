"""ROOT CAUSE FIX: Make tools query local UAE Law DB FIRST, skip unreachable gov sites.

The 17 PARTIAL tools fail because gov sites block Hetzner IP.
Fix: Query the local SQLite DB (113K provisions) as PRIMARY source.
Only try scraping as secondary. LLM as tertiary.
"""
import os
import re

tools_dir = "/data/opt/research-toolbox/loom-legal/src/loom_legal/tools"
DB_PATH = "/opt/research-toolbox/uae-law-mcp/data/database.db"

partial_tools = [
    "legislation.py", "dubai_law.py", "elaws.py", "federal_law.py",
    "difc.py", "adgm.py", "criminal.py", "labor.py", "commercial.py",
    "personal_status.py", "court_decisions.py",
    "aml_compliance.py", "trademark.py", "dubai_decree.py",
    "municipality.py", "labor_dispute.py"
]

# The local DB search function to inject at top of each tool
LOCAL_DB_SEARCH = '''
async def _search_uae_law_db(query: str, limit: int = 10) -> list[dict]:
    """Search local UAE Law DB (113K provisions) — primary data source."""
    import sqlite3
    import asyncio
    def _sync_search():
        try:
            db = sqlite3.connect("{db_path}")
            db.row_factory = sqlite3.Row
            # Use FTS5 for fast search
            try:
                rows = db.execute(
                    "SELECT p.content, p.provision_ref, p.chapter, p.title, d.title as doc_title "
                    "FROM legal_provisions p JOIN legal_documents d ON p.document_id=d.id "
                    "WHERE p.id IN (SELECT rowid FROM provisions_fts WHERE provisions_fts MATCH ?) "
                    "LIMIT ?",
                    (query, limit)
                ).fetchall()
            except Exception:
                # Fallback to LIKE if FTS fails
                rows = db.execute(
                    "SELECT p.content, p.provision_ref, p.chapter, p.title, d.title as doc_title "
                    "FROM legal_provisions p JOIN legal_documents d ON p.document_id=d.id "
                    "WHERE p.content LIKE ? LIMIT ?",
                    (f"%{{query}}%", limit)
                ).fetchall()
            db.close()
            return [{{
                "title_en": r["doc_title"][:200] if r["doc_title"] else "",
                "provision": r["provision_ref"] or "",
                "content": r["content"][:500] if r["content"] else "",
                "chapter": r["chapter"] or "",
                "source": "uae_law_db"
            }} for r in rows]
        except Exception:
            return []
    return await asyncio.to_thread(_sync_search)
'''.format(db_path=DB_PATH)

fixed = 0
for fname in partial_tools:
    fpath = os.path.join(tools_dir, fname)
    if not os.path.exists(fpath):
        continue

    content = open(fpath).read()

    if "_search_uae_law_db" in content:
        print(f"  SKIP {fname} (already has local DB)")
        continue

    # Find the main async def research_ function
    match = re.search(r"(async def research_\w+\([^)]*\)[^:]*:)", content)
    if not match:
        print(f"  SKIP {fname} (no async research_ function found)")
        continue

    func_def = match.group(1)
    func_start = content.find(func_def)

    # Find the docstring end (after """)
    doc_end = content.find('"""', func_start + len(func_def))
    if doc_end > 0:
        doc_end = content.find('"""', doc_end + 3)
        if doc_end > 0:
            doc_end += 3
            insert_point = doc_end
        else:
            insert_point = func_start + len(func_def)
    else:
        insert_point = func_start + len(func_def)

    # Find the first line after docstring
    next_line = content.find("\n", insert_point) + 1

    # Get indent level
    next_content = content[next_line:]
    indent_match = re.match(r"(\s+)", next_content)
    indent = indent_match.group(1) if indent_match else "    "

    # Build the local DB query that runs FIRST
    # Extract the query parameter name from the function signature
    query_param = "query"
    if "law_number" in func_def:
        query_param = "law_number"
    elif "decree_number" in func_def:
        query_param = "decree_number"
    elif "entity_name" in func_def:
        query_param = "entity_name"

    db_first_code = f'''
{indent}# PRIMARY SOURCE: Local UAE Law DB (113K provisions, instant)
{indent}try:
{indent}    db_results = await _search_uae_law_db({query_param}, limit=10)
{indent}    if db_results:
{indent}        return {{
{indent}            "query": {query_param},
{indent}            "total_count": len(db_results),
{indent}            "results": db_results,
{indent}            "source": "uae_law_db",
{indent}            "cached": False,
{indent}            "elapsed_ms": 0,
{indent}        }}
{indent}except Exception:
{indent}    pass
{indent}# If DB returned nothing, continue to scraping/LLM fallback below
'''

    # Insert the local DB search function before the main function
    content = content[:func_start] + LOCAL_DB_SEARCH + "\n" + content[func_start:]

    # Recalculate position after insertion
    func_start = content.find(func_def)
    doc_end = content.find('"""', func_start + len(func_def))
    if doc_end > 0:
        doc_end = content.find('"""', doc_end + 3)
        if doc_end > 0:
            doc_end += 3
    next_line = content.find("\n", doc_end) + 1

    # Insert DB-first code after docstring
    content = content[:next_line] + db_first_code + content[next_line:]

    open(fpath, "w").write(content)
    fixed += 1
    print(f"  FIXED {fname} — local DB is now PRIMARY source")

print(f"\nTotal: {fixed}/16 tools now use local DB first")
