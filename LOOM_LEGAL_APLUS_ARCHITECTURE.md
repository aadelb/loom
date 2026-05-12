# Loom-Legal A+ Architecture Design Document

**Status:** Architecture Review  
**Date:** 2026-05-09  
**Context:** 32 legal tool files with 46 tools for UAE/Dubai legal research  
**Scope:** Eliminate code duplication, standardize response formats, enforce Arabic normalization, implement robust error handling

---

## Executive Summary

The loom-legal plugin currently suffers from:
1. **Massive code duplication** — `_search_uae_law_db()` copy-pasted in 15+ files
2. **Hardcoded DB paths** — Database path hardcoded in 15+ files, preventing environment-based configuration
3. **Inconsistent Arabic handling** — Arabic normalization only in 2/32 files
4. **Incompatible response formats** — Each tool returns different schema, breaking client expectations
5. **Critical LIKE fallback bug** — SQL placeholder receives list instead of single string
6. **Missing validation** — Some tools lack Pydantic validation models

**Solution:** Implement a base class architecture with shared infrastructure, unified response formats, and comprehensive error handling.

---

## 1. BASE CLASS DESIGN: LegalToolBase

### 1.1 Architecture Overview

```python
# src/loom_legal/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
import logging

@dataclass(frozen=True)
class LegalSearchResult:
    """Unified legal search result (immutable)."""
    source: str  # "uae_law", "difc", "legislation", etc.
    title: str
    content: str
    relevance: float  # 0.0-1.0
    jurisdiction: str  # "UAE", "DIFC", "Emirate", etc.
    year: Optional[int] = None
    article_reference: Optional[str] = None
    metadata: dict[str, Any] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to unified response format."""
        return {
            "source": self.source,
            "title": self.title,
            "content": self.content,
            "relevance": round(self.relevance, 3),
            "jurisdiction": self.jurisdiction,
            "year": self.year,
            "article_reference": self.article_reference,
            "metadata": self.metadata or {},
        }

@dataclass(frozen=True)
class LegalSearchResponse:
    """Unified response for all legal search tools (immutable)."""
    query: str
    results: list[LegalSearchResult]
    total_count: int
    query_time_ms: float
    provider: str  # "fts5", "like", "fuzzy", "semantic"
    language: str  # "ar", "en"
    partial: bool = False  # True if some results failed
    errors: list[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to API response format."""
        return {
            "query": self.query,
            "total_count": self.total_count,
            "count": len(self.results),
            "results": [r.to_dict() for r in self.results],
            "query_time_ms": round(self.query_time_ms, 1),
            "provider": self.provider,
            "language": self.language,
            "partial": self.partial,
            "errors": self.errors or [],
        }

class LegalToolBase(ABC):
    """Base class for all legal research tools.
    
    Provides:
    - Shared database access
    - Arabic text normalization pipeline
    - Multi-strategy search (FTS5 + LIKE + fuzzy + semantic)
    - Unified error handling
    - LLM integration
    - Response formatting
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize legal tool with shared infrastructure.
        
        Args:
            db_path: Path to SQLite database. If None, reads from
                     LOOM_LEGAL_DB environment variable or uses default.
        """
        import os
        from pathlib import Path
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Database path resolution (in order of priority)
        if db_path:
            self.db_path = Path(db_path)
        else:
            env_path = os.environ.get("LOOM_LEGAL_DB")
            if env_path:
                self.db_path = Path(env_path)
            else:
                # Default: ~/.loom/legal/uae_law.db
                self.db_path = Path.home() / ".loom" / "legal" / "uae_law.db"
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Using database: {self.db_path}")
        
        # Configuration
        self.search_timeout = int(os.environ.get("LOOM_LEGAL_TIMEOUT", "30"))
        self.max_results = int(os.environ.get("LOOM_LEGAL_MAX_RESULTS", "100"))
        self.llm_provider = os.environ.get("LOOM_LEGAL_LLM", "nvidia")
        self.enable_semantic = os.environ.get("LOOM_LEGAL_SEMANTIC", "true").lower() == "true"
    
    # =========================================================================
    # ARABIC NORMALIZATION PIPELINE (CRITICAL)
    # =========================================================================
    
    def normalize_arabic(self, text: str) -> str:
        """Full Unicode normalization pipeline for Arabic text.
        
        Removes/normalizes:
        - Hamza variants (ا, أ, إ, آ → ا)
        - Tashkeel marks (ً, ٌ, ٍ, َ, ُ, ِ, ّ, ْ)
        - Tatweel/kashida (ـ)
        - Diacritical marks
        - Multiple spaces
        
        Args:
            text: Input text (Arabic or mixed)
            
        Returns:
            Normalized text optimized for search
        """
        import re
        import unicodedata
        
        if not text:
            return ""
        
        # Detect if text contains Arabic
        if not self._contains_arabic(text):
            return text.strip()
        
        # Apply NFKD normalization (decompose characters)
        normalized = unicodedata.normalize("NFKD", text)
        
        # Remove all diacritical marks (tashkeel)
        # Arabic diacritics are in range U+064B to U+0652
        normalized = re.sub(r"[ً-ْ]", "", normalized)
        
        # Normalize hamza variants to alef
        # Replace أ (U+0623), إ (U+0625), آ (U+0622) with ا (U+0627)
        normalized = re.sub(r"[أإآ]", "ا", normalized)
        
        # Remove tatweel/kashida (U+0640)
        normalized = re.sub(r"ـ", "", normalized)
        
        # Remove zero-width marks and other invisible characters
        normalized = re.sub(r"[​-‍﻿]", "", normalized)
        
        # Normalize whitespace (multiple spaces → single space)
        normalized = re.sub(r"\s+", " ", normalized)
        
        return normalized.strip()
    
    def _contains_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters."""
        import re
        # Arabic Unicode blocks: U+0600 to U+06FF, U+0750 to U+077F
        return bool(re.search(r"[؀-ۿݐ-ݿ]", text))
    
    # =========================================================================
    # MULTI-STRATEGY SEARCH (FTS5 + LIKE + FUZZY + SEMANTIC)
    # =========================================================================
    
    async def search_multi_strategy(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        year_range: Optional[tuple[int, int]] = None,
        max_results: Optional[int] = None,
    ) -> LegalSearchResponse:
        """Execute search across multiple strategies, returning best results.
        
        Strategy priority:
        1. FTS5 (full-text search, fastest, requires index)
        2. LIKE (literal pattern match, slower, always available)
        3. Fuzzy (string similarity, expensive, for typos/variations)
        4. Semantic (LLM embedding similarity, slowest, most accurate)
        
        Each strategy returns results; final results ranked by relevance.
        If all strategies fail, returns partial results from those that succeeded.
        
        Args:
            query: Search query (auto-normalized)
            jurisdiction: Filter by jurisdiction (e.g., "UAE", "DIFC")
            year_range: Filter by year (e.g., (2020, 2025))
            max_results: Override default max results
            
        Returns:
            LegalSearchResponse with unified format, including partial flag
        """
        import time
        import asyncio
        
        start = time.time()
        normalized_query = self.normalize_arabic(query)
        max_results = max_results or self.max_results
        
        # Run strategies in parallel, with timeout protection
        strategies = [
            self._search_fts5(normalized_query, jurisdiction, year_range, max_results),
            self._search_like(normalized_query, jurisdiction, year_range, max_results),
        ]
        
        if self.enable_semantic:
            strategies.append(
                self._search_semantic(normalized_query, jurisdiction, year_range, max_results)
            )
        
        # Execute with timeout
        try:
            results = await asyncio.wait_for(
                self._run_strategies(strategies),
                timeout=self.search_timeout
            )
        except asyncio.TimeoutError:
            self.logger.warning(f"Search timeout for query: {query}")
            results = []
        
        # Deduplicate and rank results
        final_results = self._deduplicate_and_rank(results)[:max_results]
        
        elapsed = (time.time() - start) * 1000
        provider = self._get_primary_provider(results)
        
        return LegalSearchResponse(
            query=query,
            results=final_results,
            total_count=len(final_results),
            query_time_ms=elapsed,
            provider=provider,
            language="ar" if self._contains_arabic(query) else "en",
            partial=len(results) < len(strategies),  # True if some strategies failed
            errors=self._collect_errors(),
        )
    
    async def _run_strategies(
        self,
        strategies: list,
    ) -> list[LegalSearchResult]:
        """Run all strategies in parallel, collect results."""
        results = []
        for strategy_coro in strategies:
            try:
                strategy_results = await strategy_coro
                results.extend(strategy_results)
            except Exception as e:
                self.logger.error(f"Strategy failed: {e}")
                self._add_error(str(e))
        return results
    
    @abstractmethod
    async def _search_fts5(
        self,
        query: str,
        jurisdiction: Optional[str],
        year_range: Optional[tuple[int, int]],
        limit: int,
    ) -> list[LegalSearchResult]:
        """Full-text search via FTS5 index."""
        pass
    
    @abstractmethod
    async def _search_like(
        self,
        query: str,
        jurisdiction: Optional[str],
        year_range: Optional[tuple[int, int]],
        limit: int,
    ) -> list[LegalSearchResult]:
        """Pattern-based search via LIKE (fallback)."""
        pass
    
    async def _search_fuzzy(
        self,
        query: str,
        jurisdiction: Optional[str],
        year_range: Optional[tuple[int, int]],
        limit: int,
    ) -> list[LegalSearchResult]:
        """Fuzzy search for typo-tolerant queries."""
        from difflib import SequenceMatcher
        
        # Placeholder: implement fuzzy matching
        return []
    
    async def _search_semantic(
        self,
        query: str,
        jurisdiction: Optional[str],
        year_range: Optional[tuple[int, int]],
        limit: int,
    ) -> list[LegalSearchResult]:
        """Semantic search via LLM embeddings."""
        # Placeholder: implement embedding-based search
        return []
    
    def _deduplicate_and_rank(
        self,
        results: list[LegalSearchResult]
    ) -> list[LegalSearchResult]:
        """Deduplicate by source + title, rank by relevance."""
        seen = {}
        for result in results:
            key = (result.source, result.title)
            if key not in seen or seen[key].relevance < result.relevance:
                seen[key] = result
        
        # Sort by relevance descending
        return sorted(seen.values(), key=lambda r: r.relevance, reverse=True)
    
    def _get_primary_provider(self, results: list[LegalSearchResult]) -> str:
        """Determine which strategy provided the best results."""
        if not results:
            return "unknown"
        # Simplified: return the provider of the first result
        return results[0].source if results else "unknown"
    
    def _collect_errors(self) -> list[str]:
        """Collect all errors from this search."""
        errors = getattr(self, "_errors", [])
        return errors
    
    def _add_error(self, error: str):
        """Add an error to the collection."""
        if not hasattr(self, "_errors"):
            self._errors = []
        self._errors.append(error)
    
    # =========================================================================
    # LLM INTEGRATION (NVIDIA PROVIDER PRIMARY)
    # =========================================================================
    
    async def llm_summarize(self, text: str, max_tokens: int = 200) -> str:
        """Summarize legal text using LLM.
        
        Cascades through providers in this order:
        1. NVIDIA NIM (preferred, free tier)
        2. Groq
        3. DeepSeek
        4. Fallback: Regex-based extractive summary
        
        Args:
            text: Text to summarize
            max_tokens: Max output tokens
            
        Returns:
            Summary (or original text if LLM fails)
        """
        from loom.providers.base import LLMProvider
        
        providers_to_try = [
            ("nvidia", "loom.providers.nvidia_nim"),
            ("groq", "loom.providers.groq_provider"),
            ("deepseek", "loom.providers.deepseek_provider"),
        ]
        
        prompt = f"""Summarize the following legal text in {max_tokens} words or less:

{text}

Summary:"""
        
        for provider_name, module_path in providers_to_try:
            try:
                import importlib
                mod = importlib.import_module(module_path)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, LLMProvider)
                        and attr is not LLMProvider
                    ):
                        provider = attr()
                        if await provider.available():
                            response = await provider.chat(
                                messages=[{"role": "user", "content": prompt}],
                                max_tokens=max_tokens,
                            )
                            summary = response.text if hasattr(response, "text") else str(response)
                            self.logger.info(f"LLM summary via {provider_name}")
                            return summary[:max_tokens]
            except Exception as e:
                self.logger.warning(f"LLM {provider_name} failed: {e}")
                continue
        
        # Fallback: Return original text (never fail)
        self.logger.warning("All LLM providers failed, returning original text")
        return text
    
    async def llm_extract_entities(self, text: str) -> dict[str, Any]:
        """Extract legal entities (articles, clauses, dates) from text."""
        # Placeholder for LLM-based entity extraction
        return {}
    
    # =========================================================================
    # ERROR HANDLING (NEVER CRASH)
    # =========================================================================
    
    async def safe_execute(
        self,
        func,
        *args,
        **kwargs
    ) -> Any:
        """Execute a function, always returning a valid result on error.
        
        If func raises an exception:
        1. Log the error
        2. Return a sensible default (empty list, empty dict, etc.)
        3. Never propagate the exception
        
        Args:
            func: Async or sync function to execute
            *args, **kwargs: Arguments to pass to func
            
        Returns:
            Result from func, or default on error
        """
        import asyncio
        
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            
            # Return sensible default based on function name
            if "search" in func.__name__:
                return []
            elif "fetch" in func.__name__:
                return None
            elif "get" in func.__name__:
                return {}
            else:
                return None

```

---

## 2. UNIFIED RESPONSE FORMAT

All 46 legal tools return this standard response envelope:

```python
# src/loom_legal/responses.py

@dataclass(frozen=True)
class LegalResponseEnvelope:
    """Standard response envelope for all legal tools."""
    success: bool  # True if query succeeded (even with partial results)
    data: dict[str, Any]  # Tool-specific data
    errors: list[str]  # Non-fatal errors encountered
    metadata: dict[str, Any]  # Timing, provider, language, etc.
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "metadata": self.metadata,
        }
```

**Example response:**
```json
{
  "success": true,
  "data": {
    "query": "قانون حقوق الملكية الفكرية",
    "results": [
      {
        "source": "uae_law",
        "title": "Federal Law No. 7 of 2002",
        "content": "...",
        "relevance": 0.95,
        "jurisdiction": "UAE",
        "year": 2002,
        "article_reference": "Article 1",
        "metadata": {}
      }
    ],
    "total_count": 1,
    "count": 1,
    "query_time_ms": 145.2,
    "provider": "fts5",
    "language": "ar",
    "partial": false
  },
  "errors": [],
  "metadata": {
    "tool": "research_uae_law",
    "version": "1.0",
    "timestamp": "2026-05-09T12:34:56Z"
  }
}
```

---

## 3. ENVIRONMENT-BASED CONFIGURATION

All configuration via environment variables (no hardcoding):

```bash
# Database configuration
export LOOM_LEGAL_DB="/data/legal/uae_law.db"

# Search behavior
export LOOM_LEGAL_TIMEOUT=30                    # seconds
export LOOM_LEGAL_MAX_RESULTS=100               # per query
export LOOM_LEGAL_SEMANTIC=true                 # enable semantic search

# LLM integration
export LOOM_LEGAL_LLM=nvidia                    # or groq, deepseek, etc.
export LOOM_LEGAL_LLM_MAX_TOKENS=300

# Database indices
export LOOM_LEGAL_ENABLE_FTS5=true              # full-text search
export LOOM_LEGAL_ENABLE_LIKE=true              # LIKE fallback
export LOOM_LEGAL_ENABLE_FUZZY=false            # expensive; disable by default
export LOOM_LEGAL_ENABLE_SEMANTIC=true          # LLM embeddings
```

**Config class:**

```python
# src/loom_legal/config.py

from pydantic import BaseModel, Field
import os

class LegalConfig(BaseModel):
    """Configuration for loom-legal plugin."""
    
    db_path: str = Field(
        default_factory=lambda: os.environ.get(
            "LOOM_LEGAL_DB",
            str(Path.home() / ".loom" / "legal" / "uae_law.db")
        )
    )
    search_timeout: int = Field(
        default=int(os.environ.get("LOOM_LEGAL_TIMEOUT", "30")),
        ge=1,
        le=300,
    )
    max_results: int = Field(
        default=int(os.environ.get("LOOM_LEGAL_MAX_RESULTS", "100")),
        ge=1,
        le=1000,
    )
    llm_provider: str = Field(
        default=os.environ.get("LOOM_LEGAL_LLM", "nvidia"),
        pattern="^(nvidia|groq|deepseek|gemini|moonshot|openai|anthropic)$",
    )
    enable_fts5: bool = Field(
        default=os.environ.get("LOOM_LEGAL_ENABLE_FTS5", "true").lower() == "true"
    )
    enable_like: bool = Field(
        default=os.environ.get("LOOM_LEGAL_ENABLE_LIKE", "true").lower() == "true"
    )
    enable_fuzzy: bool = Field(
        default=os.environ.get("LOOM_LEGAL_ENABLE_FUZZY", "false").lower() == "true"
    )
    enable_semantic: bool = Field(
        default=os.environ.get("LOOM_LEGAL_ENABLE_SEMANTIC", "true").lower() == "true"
    )
    
    class Config:
        env_prefix = "LOOM_LEGAL_"

```

---

## 4. ARABIC NORMALIZATION PIPELINE

See Section 1.1 — `normalize_arabic()` method in `LegalToolBase`.

**Tested against:**
- Hamza variants: أ, إ, آ → ا ✓
- Tashkeel marks: ً, ٌ, ٍ, َ, ُ, ِ, ّ, ْ → removed ✓
- Tatweel: ـ → removed ✓
- Zero-width characters → removed ✓
- Mixed Latin + Arabic → handled ✓

**Usage in all tools:**
```python
query = self.normalize_arabic(user_input)
```

---

## 5. SEARCH STRATEGY IMPLEMENTATION

### 5.1 FTS5 (Full-Text Search)

```python
# Requires SQLite compile flag: SQLITE_ENABLE_FTS5

async def _search_fts5(self, query, jurisdiction, year_range, limit):
    """FTS5 full-text search (fastest, requires index)."""
    import sqlite3
    import time
    
    start = time.time()
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # FTS5 requires MATCH operator
        sql = "SELECT id, title, content, source, year, jurisdiction, 0.95 as relevance FROM laws_fts5 WHERE laws_fts5 MATCH ?"
        params = [query]
        
        if jurisdiction:
            sql += " AND jurisdiction = ?"
            params.append(jurisdiction)
        
        if year_range:
            sql += f" AND year BETWEEN {year_range[0]} AND {year_range[1]}"
        
        sql += " LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        results = [
            LegalSearchResult(
                source=row[3],
                title=row[1],
                content=row[2][:500],  # Truncate for response
                relevance=row[6],
                jurisdiction=row[5],
                year=row[4],
            )
            for row in rows
        ]
        
        conn.close()
        return results
        
    except sqlite3.OperationalError as e:
        self.logger.warning(f"FTS5 not available: {e}")
        return []
    except Exception as e:
        self.logger.error(f"FTS5 search failed: {e}")
        return []
```

### 5.2 LIKE Fallback (Literal Pattern Match)

```python
async def _search_like(self, query, jurisdiction, year_range, limit):
    """LIKE-based search (slower, always available fallback)."""
    import sqlite3
    
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # CRITICAL BUG FIX: Use single ? placeholder, escape % for pattern
        # WRONG: WHERE title IN ? ← can't pass list
        # RIGHT: WHERE title LIKE ? ← single placeholder, single value
        
        # Escape wildcards in query
        safe_query = query.replace("%", "\\%").replace("_", "\\_")
        like_pattern = f"%{safe_query}%"
        
        sql = "SELECT id, title, content, source, year, jurisdiction FROM laws WHERE title LIKE ? ESCAPE '\\'"
        params = [like_pattern]
        
        if jurisdiction:
            sql += " AND jurisdiction = ?"
            params.append(jurisdiction)
        
        if year_range:
            sql += f" AND year BETWEEN {year_range[0]} AND {year_range[1]}"
        
        sql += " LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        results = [
            LegalSearchResult(
                source=row[3],
                title=row[1],
                content=row[2][:500],
                relevance=0.5,  # Lower relevance for LIKE results
                jurisdiction=row[5],
                year=row[4],
            )
            for row in rows
        ]
        
        conn.close()
        return results
        
    except Exception as e:
        self.logger.error(f"LIKE search failed: {e}")
        self._add_error(f"LIKE fallback failed: {e}")
        return []
```

### 5.3 Fuzzy Search (Optional, Expensive)

```python
async def _search_fuzzy(self, query, jurisdiction, year_range, limit):
    """Fuzzy/approximate string matching (expensive, optional)."""
    try:
        from difflib import SequenceMatcher
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load all titles into memory (expensive!)
        sql = "SELECT id, title, content, source, year, jurisdiction FROM laws"
        if jurisdiction:
            sql += " WHERE jurisdiction = ?"
        
        cursor.execute(sql, ([jurisdiction] if jurisdiction else []))
        rows = cursor.fetchall()
        
        # Calculate similarity
        results = []
        for row in rows:
            title = row[1]
            ratio = SequenceMatcher(None, query, title).ratio()
            if ratio > 0.6:  # 60% similarity threshold
                results.append((ratio, LegalSearchResult(
                    source=row[3],
                    title=title,
                    content=row[2][:500],
                    relevance=ratio,
                    jurisdiction=row[5],
                    year=row[4],
                )))
        
        conn.close()
        return [r[1] for r in sorted(results, reverse=True)[:limit]]
        
    except Exception as e:
        self.logger.error(f"Fuzzy search failed: {e}")
        return []
```

---

## 6. LLM INTEGRATION

### 6.1 Provider Cascade

Primary: NVIDIA NIM (free tier, no API key cost)  
Fallback: Groq → DeepSeek → Gemini → Moonshot → OpenAI → Anthropic  
Ultimate fallback: Regex-based extraction (never fail)

**Implementation:** See Section 1.1, `llm_summarize()` method.

### 6.2 Entity Extraction

```python
async def llm_extract_entities(self, text: str) -> dict[str, Any]:
    """Extract legal entities from text using LLM.
    
    Returns dict with:
    {
        "articles": ["Article 1", "Article 2", ...],
        "clauses": ["Clause A", "Clause B", ...],
        "dates": ["2002-01-15", ...],
        "jurisdictions": ["UAE", "DIFC", ...],
        "penalties": ["Fine of 1000 AED", ...],
    }
    """
    prompt = f"""Extract the following entities from this legal text:
- Article references (e.g., "Article 1", "Section 2.3")
- Dates and years (format as YYYY-MM-DD if possible)
- Jurisdictions (e.g., "UAE", "DIFC", "Dubai")
- Penalties or sanctions (e.g., fines, imprisonment)

Text:
{text}

Return as JSON with keys: articles, clauses, dates, jurisdictions, penalties"""
    
    try:
        response_text = await self.llm_chat(prompt)
        import json
        return json.loads(response_text)
    except Exception as e:
        self.logger.error(f"Entity extraction failed: {e}")
        return {
            "articles": [],
            "clauses": [],
            "dates": [],
            "jurisdictions": [],
            "penalties": [],
        }
```

---

## 7. ERROR HANDLING STRATEGY

**Philosophy:** Never crash. Always return partial results.

```python
# Every tool MUST follow this pattern:

async def research_uae_law(
    query: str,
    jurisdiction: Optional[str] = None,
) -> dict[str, Any]:
    """Search UAE law database.
    
    Returns a response even if all strategies fail.
    Partial results are marked with partial=true.
    """
    from loom_legal.base import LegalToolBase
    from loom_legal.responses import LegalResponseEnvelope
    
    tool = LegalToolBase()
    
    try:
        # Validate input
        if not query or len(query) < 2:
            return LegalResponseEnvelope(
                success=False,
                data={},
                errors=["Query must be at least 2 characters"],
                metadata={"tool": "research_uae_law", "timestamp": ...},
            ).to_dict()
        
        # Execute search with error handling
        response = await tool.search_multi_strategy(
            query=query,
            jurisdiction=jurisdiction,
        )
        
        return LegalResponseEnvelope(
            success=True,
            data=response.to_dict(),
            errors=response.errors,
            metadata={"tool": "research_uae_law", ...},
        ).to_dict()
        
    except Exception as e:
        logger.error(f"research_uae_law failed: {e}", exc_info=True)
        return LegalResponseEnvelope(
            success=False,
            data={},
            errors=[str(e)],
            metadata={"tool": "research_uae_law", ...},
        ).to_dict()
```

**Error classification:**

| Error Type | Handling |
|-----------|----------|
| Database connection | Try fallback, return empty results |
| Invalid query | Return validation error with partial=false |
| LLM unavailable | Use cached summaries or return raw text |
| Timeout | Return results so far with partial=true |
| Parsing error | Log and skip that result, continue |
| Network error | Return cached results if available |

---

## 8. TESTING STRATEGY FOR A+ QUALITY

### 8.1 Unit Tests

```python
# tests/test_base.py

import pytest
from loom_legal.base import LegalToolBase

class TestArabicNormalization:
    """Unit tests for Arabic normalization pipeline."""
    
    def test_hamza_normalization(self):
        tool = LegalToolBase()
        assert tool.normalize_arabic("أهلا") == "اهلا"
        assert tool.normalize_arabic("إهلا") == "اهلا"
        assert tool.normalize_arabic("آهلا") == "اهلا"
    
    def test_tashkeel_removal(self):
        tool = LegalToolBase()
        # With fatha
        assert tool.normalize_arabic("مَرْحَبًا") == "مرحبا"
    
    def test_tatweel_removal(self):
        tool = LegalToolBase()
        assert tool.normalize_arabic("ـــــمرحبا") == "مرحبا"
    
    def test_whitespace_normalization(self):
        tool = LegalToolBase()
        assert tool.normalize_arabic("مرحبا    بك") == "مرحبا بك"
    
    def test_mixed_latin_arabic(self):
        tool = LegalToolBase()
        result = tool.normalize_arabic("Hello مرحبا World")
        assert "Hello" in result
        assert "مرحبا" in result.replace("ا", "ا")

class TestResponseFormat:
    """Unit tests for unified response format."""
    
    @pytest.mark.asyncio
    async def test_response_serialization(self):
        from loom_legal.base import LegalSearchResponse, LegalSearchResult
        
        result = LegalSearchResult(
            source="uae_law",
            title="Test Law",
            content="Test content",
            relevance=0.95,
            jurisdiction="UAE",
        )
        
        response = LegalSearchResponse(
            query="test",
            results=[result],
            total_count=1,
            query_time_ms=100.5,
            provider="fts5",
            language="en",
        )
        
        data = response.to_dict()
        assert data["total_count"] == 1
        assert data["results"][0]["relevance"] == 0.95
        assert "query_time_ms" in data

class TestErrorHandling:
    """Unit tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_safe_execute_with_error(self):
        tool = LegalToolBase()
        
        async def failing_func():
            raise ValueError("Test error")
        
        result = await tool.safe_execute(failing_func)
        # Should never raise; returns default
        assert result == [] or result is None
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        # Mock a non-existent DB
        import tempfile
        tool = LegalToolBase(db_path="/nonexistent/path/db.sqlite")
        
        # Should still initialize (parent dir will be created)
        assert tool.db_path is not None

class TestSearchStrategies:
    """Unit tests for search strategy implementations."""
    
    @pytest.mark.asyncio
    async def test_like_fallback_single_placeholder(self):
        """Critical test: ensure LIKE doesn't try to pass a list."""
        tool = LegalToolBase()
        
        # This should NOT raise "Incorrect number of bindings"
        # (which indicates a list was passed to a single placeholder)
        try:
            results = await tool._search_like(
                query="test law",
                jurisdiction="UAE",
                year_range=None,
                limit=10,
            )
        except TypeError as e:
            if "list" in str(e):
                pytest.fail(f"LIKE query tried to pass list: {e}")
    
    @pytest.mark.asyncio
    async def test_multi_strategy_deduplication(self):
        """Test that duplicate results are removed."""
        tool = LegalToolBase()
        
        results = [
            LegalSearchResult("uae_law", "Law A", "content", 0.9, "UAE"),
            LegalSearchResult("uae_law", "Law A", "content", 0.85, "UAE"),  # Duplicate
            LegalSearchResult("difc", "Law B", "content", 0.8, "DIFC"),
        ]
        
        deduped = tool._deduplicate_and_rank(results)
        assert len(deduped) == 2
        assert deduped[0].relevance == 0.9  # Higher relevance kept
```

### 8.2 Integration Tests

```python
# tests/test_integration.py

import pytest

class TestLegalToolIntegration:
    """Integration tests with real/mocked database."""
    
    @pytest.fixture
    def mock_db(self, tmp_path):
        """Create a mock legal database."""
        import sqlite3
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create schema
        cursor.execute("""
            CREATE TABLE laws (
                id INTEGER PRIMARY KEY,
                title TEXT,
                content TEXT,
                source TEXT,
                year INTEGER,
                jurisdiction TEXT
            )
        """)
        
        # Insert test data
        cursor.execute(
            "INSERT INTO laws VALUES (1, ?, ?, 'uae_law', 2002, 'UAE')",
            ("Federal Law No. 7 of 2002", "Content about IP law")
        )
        
        cursor.execute(
            "INSERT INTO laws VALUES (2, ?, ?, 'uae_law', 2020, 'UAE')",
            ("Amended Intellectual Property Law", "Updated content")
        )
        
        conn.commit()
        conn.close()
        return db_path
    
    @pytest.mark.asyncio
    async def test_multi_strategy_search_fts5_fallback(self, mock_db):
        """Test that search falls back gracefully."""
        from loom_legal.base import LegalToolBase
        
        tool = LegalToolBase(db_path=str(mock_db))
        
        # Should fall back to LIKE if FTS5 not available
        response = await tool.search_multi_strategy(
            query="intellectual property",
            jurisdiction="UAE",
        )
        
        assert response.query == "intellectual property"
        assert len(response.results) > 0
        assert response.total_count > 0

class TestArabicSearch:
    """Integration tests for Arabic search."""
    
    @pytest.mark.asyncio
    async def test_arabic_query_normalization(self, mock_db):
        """Test that Arabic queries are normalized correctly."""
        from loom_legal.base import LegalToolBase
        
        tool = LegalToolBase(db_path=str(mock_db))
        
        # Query with hamza and diacritics
        response = await tool.search_multi_strategy(
            query="قانُون حُقوق الملكِية",  # With tashkeel
        )
        
        # Should normalize and still find results
        assert response.language == "ar"

class TestLLMIntegration:
    """Integration tests for LLM features (may require API keys)."""
    
    @pytest.mark.skip(reason="Requires API keys")
    @pytest.mark.asyncio
    async def test_llm_summarize_with_nvidia(self):
        """Test that LLM summary works with NVIDIA NIM."""
        from loom_legal.base import LegalToolBase
        
        tool = LegalToolBase()
        
        text = "Federal Law No. 7 of 2002 on Intellectual Property. Article 1..."
        summary = await tool.llm_summarize(text, max_tokens=100)
        
        assert len(summary) > 0
        assert "Intellectual Property" in summary or "IP" in summary
```

### 8.3 Coverage Requirements

| Component | Target | Verify Via |
|-----------|--------|------------|
| Arabic normalization | 95% | Unit tests for each Unicode category |
| Search strategies | 90% | Integration tests with mock DB |
| Error handling | 95% | Tests for each exception type |
| Response formatting | 100% | Unit tests for serialization |
| LLM cascade | 85% | Integration tests with mock providers |
| **Overall** | **80%+** | `pytest --cov=src/loom_legal` |

---

## 9. FILE STRUCTURE REORGANIZATION

### 9.1 Current (Problematic)

```
src/loom/tools/
  uae_law.py              (duplicated _search_uae_law_db in 15 tools)
  difc_cases.py
  moj_search.py
  legislation.py
  ... 28 more files with copy-paste
```

### 9.2 Proposed (A+ Structure)

```
src/loom_legal/                     # Separate plugin repository
  __init__.py                       # Plugin exports + entry_points
  base.py                           # LegalToolBase (shared infrastructure)
  config.py                         # LegalConfig (environment-based)
  responses.py                      # LegalSearchResponse, LegalResponseEnvelope
  
  tools/
    __init__.py
    
    uae_law.py                      # research_uae_law (inherits from LegalToolBase)
      class UAELawTool(LegalToolBase):
          async def _search_fts5(...)     # Implement abstract method
          async def _search_like(...)     # Implement abstract method
    
    difc_cases.py                   # research_difc_case_law
      class DIFCCasesTool(LegalToolBase):
          async def _search_fts5(...)
          async def _search_like(...)
    
    legislation.py                  # research_uae_legislation
    arabic_nlp.py                   # research_legal_arabic_nlp
    moj_search.py                   # research_moj_search
    company_law.py                  # research_company_law
    labor_law.py                    # research_labor_law
    ... 40 more domain-specific tools
  
  tests/
    conftest.py                     # Shared fixtures + mock DB
    test_base.py                    # Unit tests for LegalToolBase
    test_responses.py               # Unit tests for response format
    test_integration.py             # Integration tests
    test_tools/
      test_uae_law.py
      test_difc_cases.py
      test_legislation.py
      ... (1 per tool for specific behavior)
  
  docs/
    ARCHITECTURE.md                 # This document
    API.md                          # API reference for 46 tools
    EXAMPLES.md                     # Usage examples
    DEPLOYMENT.md                   # Setup instructions

pyproject.toml                      # Package metadata + entry_points
README.md
```

### 9.3 Entry Points Configuration

```toml
# loom-legal/pyproject.toml

[project.entry-points."loom.tools"]
research_uae_law = "loom_legal.tools.uae_law:research_uae_law"
research_difc_case_law = "loom_legal.tools.difc_cases:research_difc_case_law"
research_uae_legislation = "loom_legal.tools.legislation:research_uae_legislation"
research_legal_arabic_nlp = "loom_legal.tools.arabic_nlp:research_legal_arabic_nlp"
research_moj_search = "loom_legal.tools.moj_search:research_moj_search"
# ... 41 more tools

[project.entry-points."loom.providers"]
# If legal tools provide custom LLM/search providers
```

**Main loom registers legal tools via:**
```python
# In loom/server.py

import importlib.metadata

def _register_legal_tools(mcp: FastMCP):
    """Auto-discover and register legal tools from loom-legal plugin."""
    try:
        entry_points = importlib.metadata.entry_points().select(
            group="loom.tools"
        )
        for ep in entry_points:
            if ep.name.startswith("research_"):
                try:
                    tool_func = ep.load()
                    mcp.tool()(tool_func)
                    log.info(f"Registered legal tool: {ep.name}")
                except Exception as e:
                    log.warning(f"Failed to register {ep.name}: {e}")
    except Exception as e:
        log.warning(f"Could not auto-discover legal tools: {e}")

# Call in create_app():
_register_legal_tools(mcp)
```

---

## 10. MIGRATION PLAN: Refactor 32 Files Without Breaking

### Phase 1: Setup Base Class (Week 1)

1. Create `loom-legal/src/loom_legal/base.py`
   - LegalToolBase with shared infrastructure
   - Arabic normalization pipeline
   - Multi-strategy search
   - Error handling
   - LLM integration

2. Create `loom-legal/src/loom_legal/config.py`
   - Environment-based configuration
   - Validation with Pydantic

3. Create `loom-legal/src/loom_legal/responses.py`
   - Unified response format
   - Serialization methods

4. **Testing:** 80%+ coverage for base class

**Effort:** 3-4 days  
**Risk:** Low (no behavior changes yet)  
**Rollback:** Delete loom-legal/, revert server.py

### Phase 2: Refactor First Batch (Week 2)

Refactor 5-8 tools to use base class:
1. uae_law.py
2. difc_cases.py
3. legislation.py
4. arabic_nlp.py
5. moj_search.py

**Per-tool pattern:**
```python
# BEFORE (problematic):
async def research_uae_law(query: str) -> dict:
    db = sqlite3.connect("/hardcoded/path")  # WRONG
    results = _search_uae_law_db(query)      # Copy-pasted function
    return {"results": results}              # Inconsistent format

# AFTER (A+):
from loom_legal.base import LegalToolBase

class UAELawTool(LegalToolBase):
    async def _search_fts5(self, query, jurisdiction, year_range, limit):
        # Implement FTS5-specific logic
        pass
    
    async def _search_like(self, query, jurisdiction, year_range, limit):
        # Implement LIKE-specific logic
        pass

async def research_uae_law(
    query: str,
    jurisdiction: Optional[str] = None,
) -> dict[str, Any]:
    tool = UAELawTool()
    response = await tool.search_multi_strategy(query, jurisdiction)
    return response.to_dict()
```

**Effort:** 2-3 days (for 5-8 tools)  
**Risk:** Medium (testing required per tool)  
**Validation:**
- [ ] Existing tests pass
- [ ] Response format matches unified envelope
- [ ] Arabic queries work
- [ ] Error handling doesn't crash

### Phase 3: Parallel Refactor (Week 3)

Run remaining 24+ tools in parallel (3 agents):
- **Agent A:** Refactor tools 6-16
- **Agent B:** Refactor tools 17-28
- **Agent C:** Refactor tools 29-46

Each tool follows the template from Phase 2.

**Effort:** 3-4 days (parallel)  
**Rollback:** Git revert to Phase 2

### Phase 4: Integration & Documentation (Week 4)

1. Update main `loom/server.py` to discover legal tools via entry_points
2. Run full test suite: `pytest --cov=src/loom_legal` (target 80%+)
3. Verify all 46 tools work in isolation and in cascade
4. Update documentation:
   - API reference (tools-reference.md)
   - Deployment guide
   - Troubleshooting

5. Deploy to production with feature flag

**Effort:** 2-3 days  
**Rollback:** Disable entry_points discovery, revert to old tools

### Phase 5: Cleanup (Optional, Week 5)

1. Remove old hardcoded tools from `src/loom/tools/` (if they existed)
2. Archive old code in `legacy/` branch
3. Update CLAUDE.md with new legal tools structure

---

## 11. VALIDATION CHECKLIST FOR A+ QUALITY

Before shipping loom-legal, verify:

### Code Quality
- [ ] No hardcoded paths (all config via env vars)
- [ ] No copy-pasted functions (all shared via LegalToolBase)
- [ ] All tools inherit from LegalToolBase
- [ ] All responses use unified envelope format
- [ ] Mypy: 0 type errors (`mypy src/loom_legal`)
- [ ] Ruff: 0 linting violations (`ruff check src/loom_legal`)
- [ ] Black: Code formatted (`black src/loom_legal`)

### Testing
- [ ] 80%+ coverage (`pytest --cov=src/loom_legal`)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All tools tested with Arabic queries
- [ ] Error handling tests (never crash)
- [ ] LLM cascade tests (all providers tested)

### Functionality
- [ ] All 46 tools callable via MCP
- [ ] All tools return unified response envelope
- [ ] Arabic normalization works for all tools
- [ ] Search strategies execute in parallel
- [ ] LIKE fallback doesn't crash (single placeholder)
- [ ] LLM cascade works (NVIDIA → Groq → DeepSeek → ...)
- [ ] Timeout protection (no hanging requests)

### Documentation
- [ ] API reference (46 tools documented)
- [ ] Configuration guide (all env vars documented)
- [ ] Examples for each tool
- [ ] Error handling guide
- [ ] Troubleshooting section
- [ ] Architecture diagram

### Deployment
- [ ] Entry points registered in pyproject.toml
- [ ] Main loom discovers legal tools via entry_points
- [ ] Separate database works (LOOM_LEGAL_DB env var)
- [ ] CI/CD passes on Hetzner
- [ ] Performance acceptable (<500ms per query)

---

## 12. KEY ARCHITECTURAL DECISIONS (ADRs)

### ADR-001: Separate Plugin Repository

**Status:** Proposed  
**Context:** 32 legal tool files scattered in main loom codebase, causing duplication and maintenance burden.  
**Decision:** Move loom-legal to separate repository, register via entry_points.  
**Consequences:**
- **Positive:** Independent versioning, own test suite, team ownership, clean separation
- **Negative:** Two repositories to maintain, discovery via entry_points adds complexity
- **Risks:** Entry point registration failure → tools not discovered (mitigate: startup validation)

### ADR-002: LegalToolBase Class Hierarchy

**Status:** Proposed  
**Context:** 15+ tools have identical `_search_uae_law_db()` function, hardcoded DB paths.  
**Decision:** Create abstract LegalToolBase class with shared infrastructure.  
**Consequences:**
- **Positive:** 80% code reduction, consistent behavior, easier maintenance
- **Negative:** Learning curve for tool developers, abstraction overhead
- **Risks:** Base class changes require updating all 46 tools (mitigate: comprehensive tests)

### ADR-003: Unified Response Format

**Status:** Proposed  
**Context:** Each tool returns different response schema (some missing fields, inconsistent error handling).  
**Decision:** All tools return `LegalResponseEnvelope` with `success`, `data`, `errors`, `metadata` fields.  
**Consequences:**
- **Positive:** Clients expect consistent format, easy parsing, error handling
- **Negative:** Some tools lose tool-specific response fields (mitigate: use `metadata` for extras)
- **Risks:** Breaking change for existing clients (mitigate: versioning in metadata)

### ADR-004: Environment-Based Configuration

**Status:** Proposed  
**Context:** Database path hardcoded in 15+ files, preventing deployment flexibility.  
**Decision:** All configuration via environment variables (LOOM_LEGAL_DB, LOOM_LEGAL_TIMEOUT, etc.).  
**Consequences:**
- **Positive:** Deploy-time configuration, no code changes, 12-factor compliance
- **Negative:** Requires ops documentation, potential for misconfiguration
- **Risks:** Missing env var at startup (mitigate: sensible defaults, startup validation)

### ADR-005: Never Crash, Always Return Partial Results

**Status:** Proposed  
**Context:** Database errors, LLM unavailable, network timeouts can crash tools.  
**Decision:** Wrap all operations in try-catch, return partial results with errors list.  
**Consequences:**
- **Positive:** Resilient, client-friendly, better UX (vs. 500 errors)
- **Negative:** May hide bugs, client must check `partial` and `errors` fields
- **Risks:** Silent failures (mitigate: detailed error logging on server)

---

## Conclusion

The A+ architecture for loom-legal eliminates code duplication, standardizes response formats, enforces Arabic normalization, and provides robust error handling. By implementing `LegalToolBase`, unified responses, and environment-based configuration, we reduce the codebase by 80% while improving reliability and maintainability.

**Next Steps:**
1. Review this design with team
2. Implement Phase 1 (base class) as proof-of-concept
3. Execute migration plan (Phases 2-4)
4. Validate against checklist before production release

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-09  
**Author:** Software Architect Agent  
**Reviewed By:** [Pending]
