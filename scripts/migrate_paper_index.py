"""Migrate paper index: merge duplicate entries (same PDF) into one canonical entry."""
import hashlib
import json
import re
import shutil
from pathlib import Path

PAPERS_DIR = Path("/home/aadel/.loom/papers")
INDEX = PAPERS_DIR / "index.json"
PARSED = PAPERS_DIR / "parsed"


def norm_arxiv(a):
    if not a:
        return ""
    return re.sub(r"v\d+$", "", str(a).strip().lower())


def canonical_id(arxiv_id=None, file_path=None, title=None):
    na = norm_arxiv(arxiv_id)
    if na:
        return "arx_" + hashlib.sha256(na.encode()).hexdigest()[:9]
    if file_path:
        rp = str(Path(file_path).expanduser().resolve())
        return "f_" + hashlib.sha256(rp.encode()).hexdigest()[:10]
    return hashlib.sha256((title or "untitled").lower().strip().encode()).hexdigest()[:12]


def resolved_file(p):
    f = p.get("file")
    return str(Path(f).expanduser().resolve()) if f else None


index = json.loads(INDEX.read_text())
papers = index["papers"]
print(f"BEFORE: {len(papers)} entries")

# Group entries by resolved file path (fallback: by old id if no file)
groups = {}  # group_key -> list of (old_id, entry)
for oid, entry in papers.items():
    rf = resolved_file(entry)
    key = rf or f"noid::{oid}"
    groups.setdefault(key, []).append((oid, entry))

# Build merged entries
new_papers = {}
id_remap = {}  # old_id -> new_id

def pick_title(entries):
    # Prefer a title that isn't an arxiv-header or bare arxiv-id stub
    cands = [e.get("title", "") for _, e in entries]
    good = [
        t for t in cands
        if t and not t.lower().startswith("arxiv:")
        and not re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", t.strip())
    ]
    if good:
        return max(good, key=len)
    return max(cands, key=len) if cands else ""

for key, entries in groups.items():
    # Determine canonical id from best available signals
    arxiv_id = next((e.get("arxiv_id") for _, e in entries if e.get("arxiv_id")), None)
    file_path = next((e.get("file") for _, e in entries if e.get("file")), None)
    title = pick_title(entries)
    new_id = canonical_id(arxiv_id=arxiv_id, file_path=file_path, title=title)

    # Merge all fields
    merged = {}
    tags = set()
    for _, e in entries:
        for k, v in e.items():
            if k == "tags":
                tags.update(v or [])
            elif k in ("id",):
                continue
            elif v not in (None, "", [], {}):
                # later non-empty values win, but don't overwrite good title with stub
                if k == "title":
                    continue
                merged[k] = v
    merged["id"] = new_id
    merged["title"] = title
    merged["tags"] = sorted(tags)
    if arxiv_id:
        merged["arxiv_id"] = arxiv_id
    if file_path:
        merged["file"] = file_path

    new_papers[new_id] = merged
    for oid, _ in entries:
        id_remap[oid] = new_id

    # Relocate parsed JSON: prefer one with markdown/abstract content
    best_parsed = None
    for oid, _ in entries:
        pf = PARSED / f"{oid}.json"
        if pf.exists():
            try:
                data = json.loads(pf.read_text())
                score = len(data.get("markdown", "")) + len(data.get("abstract", "")) + len(data.get("references", []))
                if best_parsed is None or score > best_parsed[1]:
                    best_parsed = (pf, score)
            except Exception:
                pass
    if best_parsed:
        target = PARSED / f"{new_id}.json"
        if best_parsed[0] != target:
            shutil.copy(best_parsed[0], target)

# Rebuild tag index
new_tags = {}
for nid, p in new_papers.items():
    for t in p.get("tags", []):
        new_tags.setdefault(t, [])
        if nid not in new_tags[t]:
            new_tags[t].append(nid)

# Rebuild collections with remapped ids
new_collections = {}
for coll, pids in index.get("collections", {}).items():
    remapped = []
    for pid in pids:
        nid = id_remap.get(pid, pid)
        if nid not in remapped:
            remapped.append(nid)
    new_collections[coll] = remapped

index["papers"] = new_papers
index["tags"] = new_tags
index["collections"] = new_collections
INDEX.write_text(json.dumps(index, indent=2, default=str))

print(f"AFTER: {len(new_papers)} entries")
print("Remap:")
for o, n in id_remap.items():
    print(f"  {o} -> {n}")
print("\nMerged papers:")
for nid, p in new_papers.items():
    print(f"  {nid} | tags={p.get('tags')} | {p.get('title','')[:50]}")
