"""Fix all remaining loom-legal issues."""
import sqlite3
import os
import re

TOOLS_DIR = "/data/opt/research-toolbox/loom-legal/src/loom_legal/tools"
DB_PATH = "/opt/research-toolbox/uae-law-mcp/data/database.db"

print("=== FIX 1: uae_law_db.py — make LIKE the primary search (not FTS) ===")
path = os.path.join(TOOLS_DIR, "uae_law_db.py")
content = open(path).read()

# The FTS search fails for multi-word English. Replace with LIKE as primary.
# Find the SQL query section
if "provisions_fts" in content:
    # Replace FTS with LIKE as primary
    content = content.replace(
        "WHERE p.id IN (SELECT rowid FROM provisions_fts WHERE provisions_fts MATCH ?)",
        "WHERE p.content LIKE ?"
    )
    # Fix the param — FTS uses bare query, LIKE uses %query%
    # Find where query param is set for DB
    content = content.replace(
        "db_params = [params.query]",
        'db_params = [f"%{params.query}%"]'
    )
    open(path, "w").write(content)
    print("  Fixed: LIKE is now primary search in uae_law_db")
else:
    # Check if it already uses LIKE
    if "LIKE ?" in content:
        print("  Already uses LIKE")
    else:
        print("  No FTS or LIKE found — checking structure")

print()
print("=== FIX 2: Compile-check ALL tool files ===")
import py_compile
errors = []
for fname in sorted(os.listdir(TOOLS_DIR)):
    if not fname.endswith(".py"):
        continue
    fpath = os.path.join(TOOLS_DIR, fname)
    try:
        py_compile.compile(fpath, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append((fname, str(e)[:100]))
        print(f"  SYNTAX ERROR: {fname}: {str(e)[:80]}")

if not errors:
    print("  All files compile OK")
else:
    print(f"  {len(errors)} files have syntax errors")

print()
print("=== FIX 3: Clean error field in scraping tools ===")
scraping_tools = [
    "legislation.py", "dubai_law.py", "elaws.py", "federal_law.py",
    "difc.py", "adgm.py", "criminal.py", "labor.py", "commercial.py",
    "personal_status.py", "court_decisions.py", "aml_compliance.py",
    "trademark.py", "dubai_decree.py", "municipality.py", "labor_dispute.py"
]

cleaned = 0
for fname in scraping_tools:
    fpath = os.path.join(TOOLS_DIR, fname)
    if not os.path.exists(fpath):
        continue
    content = open(fpath).read()

    # Check if there's already error_cleanup
    if "error_cleanup" in content:
        continue

    # Find the last return and add error cleanup
    lines = content.split("\n")
    for i in range(len(lines)-1, -1, -1):
        if lines[i].strip().startswith("return ") and ("result" in lines[i] or "_final" in lines[i] or "{" in lines[i]):
            indent = " " * (len(lines[i]) - len(lines[i].lstrip()))
            var = "result" if "result" in lines[i] else "_final_result" if "_final" in lines[i] else None
            if var and f"return {var}" == lines[i].strip():
                cleanup = [
                    f"{indent}# error_cleanup",
                    f"{indent}if isinstance({var}, dict) and {var}.get('results') and len({var}.get('results', [])) > 0:",
                    f"{indent}    {var}.pop('error', None)",
                ]
                for j, cl in enumerate(cleanup):
                    lines.insert(i+j, cl)
                open(fpath, "w").write("\n".join(lines))
                cleaned += 1
                break
            break

print(f"  Cleaned error field from {cleaned} tools")

print()
print("=== FIX 4: Verify DB has English content searchable ===")
db = sqlite3.connect(DB_PATH)
en = db.execute("SELECT COUNT(*) FROM legal_provisions WHERE language='en'").fetchone()[0]
total = db.execute("SELECT COUNT(*) FROM legal_provisions").fetchone()[0]
test_like = db.execute("SELECT COUNT(*) FROM legal_provisions WHERE content LIKE '%settlement%'").fetchone()[0]
test_454 = db.execute("SELECT COUNT(*) FROM legal_provisions WHERE content LIKE '%454%Penal%'").fetchone()[0]
db.close()
print(f"  Total: {total}, English: {en}")
print(f"  LIKE 'settlement': {test_like}")
print(f"  LIKE '454 Penal': {test_454}")

print()
print("=== DONE ===")
