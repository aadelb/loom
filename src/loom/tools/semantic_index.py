"""Semantic Tool Index — TF-IDF vectors for intelligent tool discovery."""
from __future__ import annotations
import ast, asyncio, logging, math, re
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.semantic_index")
_INDEX: dict[str, list[float]] = {}
_IDF: dict[str, float] = {}
_VOCAB: list[str] = []
_VOCAB_IDX: dict[str, int] = {}
_INDEX_LOCK = asyncio.Lock()
_STOPWORDS = {"the", "a", "is", "to", "for", "and", "of", "in", "with", "on", "by", "from", "or", "an", "as", "be", "at", "this", "that", "it", "which", "was", "are", "been", "have", "has", "do", "does", "did"}

def _extract_tools() -> dict[str, str]:
    tools = {}
    for file_path in Path(__file__).parent.glob("*.py"):
        if file_path.name.startswith("_"):
            continue
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name.startswith("research_"):
                    tools[node.name] = ast.get_docstring(node) or ""
        except Exception as e:
            logger.warning(f"Parse error {file_path.name}: {e}")
    return tools

def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]+", text.lower()) if t not in _STOPWORDS and len(t) > 1]

def _build_index() -> tuple[dict[str, list[float]], dict[str, float], list[str]]:
    tools = _extract_tools()
    if not tools:
        return {}, {}, []
    all_tokens = [_tokenize(doc) for doc in tools.values()]
    vocab = sorted(set(w for tokens in all_tokens for w in tokens))
    vocab_idx = {w: i for i, w in enumerate(vocab)}
    n_docs = len(tools)
    idf = {w: math.log((n_docs + 1) / (sum(1 for t in all_tokens if w in t) + 1)) + 1 for w in vocab}
    tfidf_idx = {}
    for tool, tokens in zip(tools.keys(), all_tokens):
        tf = [0.0] * len(vocab)
        for token in tokens:
            tf[vocab_idx[token]] += 1
        norm = math.sqrt(sum(x**2 for x in tf)) or 1.0
        tf = [x / norm for x in tf]
        tfidf = [tf[i] * idf[vocab[i]] for i in range(len(vocab))]
        norm = math.sqrt(sum(x**2 for x in tfidf)) or 1.0
        tfidf_idx[tool] = [x / norm for x in tfidf]
    return tfidf_idx, idf, vocab

def _cosine(v1: list[float], v2: list[float]) -> float:
    if len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(x**2 for x in v1)) or 1.0
    n2 = math.sqrt(sum(x**2 for x in v2)) or 1.0
    return dot / (n1 * n2) if n1 * n2 > 0 else 0.0

async def research_semantic_search(query: str, top_k: int = 10) -> dict[str, Any]:
    """Search tools by semantic similarity using TF-IDF vectors.

    Tokenizes query, computes TF-IDF, finds top-K tools by cosine similarity.
    Index is cached after first call.

    Args:
        query: Search query string
        top_k: Number of results (1-50, default 10)

    Returns:
        Dict with query, results list, total_indexed count.
    """
    global _INDEX, _IDF, _VOCAB, _VOCAB_IDX
    if not _INDEX:
        async with _INDEX_LOCK:
            if not _INDEX:
                _INDEX, _IDF, _VOCAB = _build_index()
                _VOCAB_IDX = {w: i for i, w in enumerate(_VOCAB)}
    top_k = max(1, min(top_k, 50))
    tools = _extract_tools()
    q_tokens = _tokenize(query)
    q_tf = [0.0] * len(_VOCAB)
    for token in q_tokens:
        if token in _VOCAB_IDX:
            q_tf[_VOCAB_IDX[token]] += 1
    norm = math.sqrt(sum(x**2 for x in q_tf)) or 1.0
    q_tf = [x / norm for x in q_tf]
    q_tfidf = [q_tf[i] * _IDF.get(_VOCAB[i], 0) for i in range(len(_VOCAB))]
    norm = math.sqrt(sum(x**2 for x in q_tfidf)) or 1.0
    if norm > 0:
        q_tfidf = [x / norm for x in q_tfidf]
    scores = [(name, _cosine(q_tfidf, _INDEX.get(name, [0]*len(_VOCAB)))) for name in tools.keys()]
    scores.sort(key=lambda x: x[1], reverse=True)
    results = []
    for tool_name, sim in scores[:top_k]:
        doc = tools.get(tool_name, "")
        preview = (doc[:200].replace("\n", " ").strip() if doc else "")
        results.append({"tool_name": tool_name, "similarity_score": round(sim, 4), "docstring_preview": preview, "module": "semantic_index"})
    return {"query": query, "results": results, "total_indexed": len(tools)}

async def research_semantic_rebuild() -> dict[str, Any]:
    """Force rebuild the semantic index. Call after adding new tools.

    Returns:
        Dict with rebuild status, tools_indexed, vocabulary_size.
    """
    global _INDEX, _IDF, _VOCAB, _VOCAB_IDX
    async with _INDEX_LOCK:
        _INDEX.clear()
        _IDF.clear()
        _VOCAB.clear()
        _INDEX, _IDF, _VOCAB = _build_index()
        _VOCAB_IDX = {w: i for i, w in enumerate(_VOCAB)}
    idx_kb = round(sum(len(v) * 8 for v in _INDEX.values()) / 1024, 2)
    return {"rebuilt": True, "tools_indexed": len(_INDEX), "vocabulary_size": len(_VOCAB), "index_size_kb": idx_kb}
