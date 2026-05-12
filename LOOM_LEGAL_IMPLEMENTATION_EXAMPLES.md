# Loom-Legal: Implementation Examples & Code Stubs

This document provides concrete code examples to guide Kimi/DeepSeek implementation.

---

## 1. PYPROJECT.TOML EXAMPLE

```toml
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[project]
name = "loom-legal"
version = "0.1.0"
description = "UAE legal research tools for Loom MCP server"
readme = "README.md"
license = "MIT"
authors = [{name = "Ahmed Adel Bakr Alderai", email = "ahmedalderai22@gmail.com"}]
requires-python = ">=3.11"

dependencies = [
    "loom-research>=0.1.0",
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
    "beautifulsoup4>=4.12.0",
    "pypdf>=4.0.0",
    "regex>=2023.0.0",
    "pyarabic>=0.6.15",
    "langdetect>=1.0.9",
    "hijri-converter>=2.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-timeout>=2.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
]
nlp = [
    "torch>=2.0.0",
    "sentence-transformers>=2.2.0",
    "transformers>=4.30.0",
]

[project.entry-points."loom.tools"]
legal = "loom_legal.server:_register_legal_tools"

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "W", "F", "I", "B", "C4", "UP", "SIM", "RUF", "ASYNC", "S"]
ignore = ["E501"]  # Line length handled by black

[tool.mypy]
strict = true
python_version = "3.11"
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = "beautifulsoup4.*,pypdf.*,langdetect.*"
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "unit: unit tests",
    "integration: integration tests",
    "e2e: end-to-end tests",
    "live: tests against live APIs (requires credentials)",
    "slow: slow tests",
]
```

---

## 2. ENTRY POINT REGISTRATION

### loom_legal/server.py

```python
"""Plugin registration for Loom MCP server.

This module provides the entry point that Loom's server.py calls
to register all legal tools.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import FastMCP
from mcp.types import TextContent

logger = logging.getLogger("loom_legal.server")


def _register_legal_tools(mcp: FastMCP) -> None:
    """Register all loom-legal tools with Loom MCP server.
    
    Called via entry_point from loom/server.py:
        for entry_point in importlib.metadata.entry_points().select(group="loom.tools"):
            register_func = entry_point.load()
            register_func(mcp)
    
    Args:
        mcp: FastMCP instance to register tools with
    """
    from loom_legal.tools.legislation import research_uae_legislation
    from loom_legal.tools.dubai_laws import research_dubai_law
    from loom_legal.tools.court import research_court_decision
    from loom_legal.tools.difc_tools import research_difc_law, research_difc_company
    # ... import all 26 tools
    
    logger.info("Registering 26 legal tools with Loom MCP server")
    
    # Register each tool with MCP wrapper
    @mcp.tool()
    async def tool_research_uae_legislation(
        query: str,
        language: str = "en",
        limit: int = 10,
        law_number: str | None = None,
        year: int | None = None,
        status: str = "active",
    ) -> list[TextContent]:
        """Search UAE federal legislation.
        
        Args:
            query: Search term (law name, keyword, number)
            language: "en" or "ar"
            limit: Max results (1-100)
            law_number: Optional filter (e.g., "2021-35")
            year: Optional filter (e.g., 2021)
            status: "active" | "repealed" | "amended" | "all"
        
        Returns:
            List of TextContent with JSON results
        """
        try:
            result = await research_uae_legislation(
                query=query,
                language=language,
                limit=limit,
                law_number=law_number,
                year=year,
                status=status,
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        except Exception as e:
            logger.exception("research_uae_legislation failed")
            return [TextContent(type="text", text=json.dumps({
                "error": str(e),
                "query": query,
            }, indent=2))]
    
    # ... repeat for all 26 tools
    
    logger.info("Successfully registered 26 legal tools")
```

### loom/server.py (Modified)

```python
# In existing server.py, add to _register_tools() or create new _register_third_party_tools():

def _register_third_party_tools(mcp: FastMCP) -> None:
    """Discover and register tools from installed entry points.
    
    This enables plugin architecture: separate packages can register
    tools without modifying Loom core.
    """
    import importlib.metadata
    
    logger.info("Loading third-party tool plugins from entry_points")
    
    for entry_point in importlib.metadata.entry_points().select(group="loom.tools"):
        try:
            logger.info(f"Loading plugin: {entry_point.name} from {entry_point.value}")
            register_func = entry_point.load()
            register_func(mcp)  # Call plugin's registration function
            logger.info(f"Successfully loaded {entry_point.name}")
        except Exception as e:
            logger.error(f"Failed to load {entry_point.name}: {e}", exc_info=True)
            # Don't fail startup, just warn

# In _create_app() or on server startup:
_register_third_party_tools(mcp)
```

---

## 3. PARAMETER VALIDATION MODELS

### loom_legal/params.py (Stub)

```python
"""Parameter models for all loom-legal tools.

All models use Pydantic v2 with:
- extra="forbid" (no unknown fields)
- strict=True (type coercion minimal)
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, ConfigDict


class LegalToolParams(BaseModel):
    """Base class for all legal tool parameters."""
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=True,
    )


class UAELegislationParams(LegalToolParams):
    """Parameters for research_uae_legislation."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query (law name, number, or keyword)",
    )
    language: Literal["en", "ar"] = Field(
        "en",
        description="Result language",
    )
    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of results",
    )
    law_number: str | None = Field(
        None,
        pattern=r"^\d{4}-\d{1,3}$",
        description="Filter by law number (e.g., '2021-35')",
    )
    year: int | None = Field(
        None,
        ge=1900,
        le=2100,
        description="Filter by year enacted",
    )
    status: Literal["active", "repealed", "amended", "all"] = Field(
        "active",
        description="Law status filter",
    )
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Prevent SQL injection and disallowed characters."""
        if re.search(r"[;'\"]|--|\\/|exec|select", v, re.IGNORECASE):
            raise ValueError("Query contains disallowed characters")
        return v.strip()


class CourtDecisionParams(LegalToolParams):
    """Parameters for research_court_decision."""
    
    query: str = Field(..., min_length=1, max_length=500)
    case_number: str | None = Field(
        None,
        pattern=r"^\d+/\d+$",
        description="Case number (e.g., '12345/2023')",
    )
    court: Literal["cassation", "court_of_appeal", "first_instance", "all"] = Field(
        "all",
    )
    year: int | None = Field(None, ge=1950, le=2100)
    language: Literal["en", "ar"] = Field("en")
    limit: int = Field(10, ge=1, le=100)


class LegalNLPClassifyParams(LegalToolParams):
    """Parameters for research_legal_nlp_classify."""
    
    text: str = Field(..., min_length=10, max_length=5000)
    category_type: Literal["auto", "law_type", "document_type", "risk_level"] = "auto"
    language: Literal["en", "ar", "auto"] = "auto"
```

---

## 4. SOURCE CLIENT PATTERN

### loom_legal/sources/base.py (Infrastructure)

```python
"""Base classes for data source clients."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from loom_legal.cache import get_cache, CacheStore
from loom_legal.errors import LegalRateLimitError, LegalSourceUnavailable

logger = logging.getLogger("loom_legal.sources.base")

T = TypeVar("T")


@dataclass
class RateLimiter:
    """Simple token bucket rate limiter."""
    
    requests_per_hour: int
    
    def __post_init__(self):
        self.tokens = self.requests_per_hour
        self.last_refill = asyncio.get_event_loop().time()
    
    async def acquire(self) -> None:
        """Wait until token available."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_refill
        
        # Refill tokens
        refill_amount = (elapsed / 3600) * self.requests_per_hour
        self.tokens = min(self.requests_per_hour, self.tokens + refill_amount)
        self.last_refill = now
        
        if self.tokens < 1:
            sleep_time = (1 - self.tokens) * 3600 / self.requests_per_hour
            logger.info(f"Rate limit reached, sleeping {sleep_time:.1f}s")
            await asyncio.sleep(sleep_time)
            self.tokens = 1
        
        self.tokens -= 1


class SourceClient:
    """Base class for data source clients."""
    
    def __init__(self, cache: CacheStore | None = None, rate_limit: int = 100):
        self.cache = cache or get_cache()
        self.rate_limiter = RateLimiter(requests_per_hour=rate_limit)
    
    def _cache_key(self, endpoint: str, params: dict[str, Any]) -> str:
        """Generate cache key from endpoint + params."""
        key_str = f"{endpoint}|{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    async def _fetch_cached(
        self,
        endpoint: str,
        params: dict[str, Any],
        fetch_fn,
        ttl_seconds: int = 604800,  # 7 days
    ) -> dict[str, Any]:
        """Fetch with caching."""
        cache_key = self._cache_key(endpoint, params)
        
        # Try cache first
        cached = self.cache.get(cache_key)
        if cached and not self._is_expired(cached):
            return {...cached, "cached": True}
        
        # Rate limit before fetching
        await self.rate_limiter.acquire()
        
        # Fetch fresh data
        try:
            result = await fetch_fn()
            result["cached"] = False
            self.cache.set(cache_key, result, ttl=ttl_seconds)
            return result
        except asyncio.TimeoutError:
            if cached:
                logger.warning(f"Fetch timeout for {endpoint}, returning stale cache")
                return {...cached, "cached_stale": True}
            raise LegalSourceUnavailable(f"{endpoint} unavailable")
    
    def _is_expired(self, entry: dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        from datetime import datetime, timezone
        
        expires_at = entry.get("expires_at")
        if not expires_at:
            return True
        
        return datetime.fromisoformat(expires_at) < datetime.now(timezone.utc)
```

### loom_legal/sources/uae_legislation.py (Example)

```python
"""Client for uaelegislation.gov.ae portal."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from loom_legal.sources.base import SourceClient

logger = logging.getLogger("loom_legal.sources.uae_legislation")


class UAELegislationClient(SourceClient):
    """Client for UAE federal legislation portal."""
    
    BASE_URL = "https://www.uaelegislation.gov.ae/en/legislation/search"
    
    async def search(
        self,
        query: str,
        language: str = "en",
        limit: int = 10,
        law_number: str | None = None,
        year: int | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        """Search UAE legislation.
        
        Returns cached result if available + not expired.
        Otherwise fetches fresh data + caches.
        """
        params = {
            "q": query,
            "lang": language,
            "limit": limit,
            "law_number": law_number,
            "year": year,
            "status": status,
        }
        
        async def _fetch():
            """Actual fetch logic."""
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    self.BASE_URL,
                    params=params,
                )
                resp.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                
                for item in soup.find_all("div", class_="legislation-item")[:limit]:
                    law_title = item.find("h3")
                    law_number = item.find("span", class_="law-number")
                    law_date = item.find("span", class_="date")
                    
                    if law_title:
                        results.append({
                            "title_en": law_title.text.strip(),
                            "law_number": law_number.text if law_number else None,
                            "date_enacted": law_date.text if law_date else None,
                            "url": item.find("a")["href"] if item.find("a") else None,
                        })
                
                return {
                    "query": query,
                    "language": language,
                    "total_results": len(results),
                    "results": results,
                }
        
        return await self._fetch_cached("uae_legislation:search", params, _fetch, ttl_seconds=604800)
```

---

## 5. TOOL IMPLEMENTATION PATTERN

### loom_legal/tools/legislation.py (Example)

```python
"""Federal legislation research tools."""

from __future__ import annotations

import logging
from typing import Any

from loom_legal.params import UAELegislationParams
from loom_legal.sources.uae_legislation import UAELegislationClient

logger = logging.getLogger("loom_legal.tools.legislation")


async def research_uae_legislation(
    query: str,
    language: str = "en",
    limit: int = 10,
    law_number: str | None = None,
    year: int | None = None,
    status: str = "active",
) -> dict[str, Any]:
    """Search UAE federal legislation.
    
    Args:
        query: Search query (law name, keyword, number)
        language: "en" or "ar"
        limit: Max results (1-100)
        law_number: Optional filter (e.g., "2021-35")
        year: Optional year filter
        status: "active" | "repealed" | "amended" | "all"
    
    Returns:
        Dict with results list and metadata.
    """
    # Validate parameters
    params = UAELegislationParams(
        query=query,
        language=language,
        limit=limit,
        law_number=law_number,
        year=year,
        status=status,
    )
    
    # Create client and search
    client = UAELegislationClient(rate_limit=200)  # 200 req/hr per source
    
    try:
        result = await client.search(
            query=params.query,
            language=params.language,
            limit=params.limit,
            law_number=params.law_number,
            year=params.year,
            status=params.status,
        )
        
        # Enhance results (add summary, relationships, etc.)
        result["results"] = await _enhance_results(result["results"], language)
        result["execution_time_ms"] = 0  # Track in wrapper
        result["source_accessed_at"] = datetime.now(timezone.utc).isoformat()
        
        return result
    
    except Exception as e:
        logger.exception("research_uae_legislation failed")
        return {
            "query": query,
            "language": language,
            "error": str(e),
            "results": [],
        }


async def _enhance_results(
    results: list[dict[str, Any]],
    language: str,
) -> list[dict[str, Any]]:
    """Enhance results with summaries, relationships, etc."""
    # Placeholder: could call LLM for summarization
    return results
```

---

## 6. TEST EXAMPLES

### tests/test_tools/test_legislation.py

```python
"""Tests for legislation tools."""

import pytest
from unittest.mock import patch, AsyncMock

from loom_legal.tools.legislation import research_uae_legislation
from loom_legal.params import UAELegislationParams


@pytest.mark.unit
def test_uae_legislation_params_validation():
    """Validate parameter model."""
    # Valid
    params = UAELegislationParams(query="contract")
    assert params.language == "en"
    
    # Invalid query
    with pytest.raises(ValueError):
        UAELegislationParams(query="'; DROP TABLE laws;--")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_uae_legislation_basic():
    """Test basic legislation search."""
    result = await research_uae_legislation(
        query="contract law",
        language="en",
        limit=5,
    )
    
    assert result["query"] == "contract law"
    assert result["language"] == "en"
    assert isinstance(result["results"], list)
    if result["results"]:
        assert "title_en" in result["results"][0]
        assert "law_number" in result["results"][0]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_uae_legislation_caching():
    """Test that second call hits cache."""
    # First call
    result1 = await research_uae_legislation(query="criminal")
    assert result1.get("cached") is False
    
    # Second call (should be cached)
    result2 = await research_uae_legislation(query="criminal")
    assert result2.get("cached") is True
    
    # Results should be identical
    assert result1["results"] == result2["results"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_uae_legislation_arabic():
    """Test Arabic language support."""
    result = await research_uae_legislation(
        query="جريمة",  # "crime" in Arabic
        language="ar",
    )
    
    assert result["language"] == "ar"
    if result["results"]:
        assert any("title_ar" in r for r in result["results"])


@pytest.mark.live
@pytest.mark.asyncio
async def test_research_uae_legislation_live():
    """Test against live uaelegislation.gov.ae API."""
    result = await research_uae_legislation(
        query="Federal Law No. 3 of 1987",
        language="en",
    )
    
    assert result["total_results"] >= 1
    assert result["results"][0]["law_number"] == "1987-3"
```

---

## 7. INTEGRATION WITH LOOM SERVER

### Modified loom/server.py Entry

```python
# In _create_app() function:

def _create_app() -> FastMCP:
    """Create and configure the Loom MCP server."""
    mcp = FastMCP(name="Loom", version=get_version_info()["version"])
    
    # Register core tools
    _register_tools(mcp)
    
    # Register third-party plugins (including loom-legal)
    _register_third_party_tools(mcp)
    
    # ... rest of configuration
    return mcp


def _register_third_party_tools(mcp: FastMCP) -> None:
    """Load and register tools from installed plugins."""
    import importlib.metadata
    
    for entry_point in importlib.metadata.entry_points().select(group="loom.tools"):
        try:
            log.info(f"Loading plugin: {entry_point.name}")
            register_func = entry_point.load()
            register_func(mcp)
            log.info(f"Loaded {entry_point.name}")
        except Exception as e:
            log.error(f"Failed to load {entry_point.name}: {e}")
```

---

## 8. TOOL ACCEPTANCE TEST TEMPLATE

```python
# tests/test_integration/test_acceptance.py

@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_uae_legislation_acceptance():
    """
    Acceptance: research_uae_legislation(query='cybercrime law', language='en')
    returns >= 1 result with law_number, title_en, full_text_en within 10s
    """
    import time
    
    start = time.time()
    result = await research_uae_legislation(
        query="cybercrime law",
        language="en",
    )
    elapsed = time.time() - start
    
    # Assertions
    assert elapsed <= 10, f"Took {elapsed}s, exceeds 10s limit"
    assert result["total_results"] >= 1, "No results returned"
    
    first_result = result["results"][0]
    assert "law_number" in first_result, "Missing law_number"
    assert "title_en" in first_result, "Missing title_en"
    # Optional: check if full_text_en exists
    
    # Cache check
    start = time.time()
    result2 = await research_uae_legislation(
        query="cybercrime law",
        language="en",
    )
    elapsed2 = time.time() - start
    
    assert elapsed2 < 0.1, f"Cache hit took {elapsed2}s, should be <100ms"
    assert result2.get("cached") is True, "Not marked as cached"
```

---

## SUMMARY FOR IMPLEMENTERS

Use these examples to:

1. **Package Setup**: Copy pyproject.toml structure, update dependencies
2. **Entry Point**: Implement `_register_legal_tools(mcp)` in `loom_legal/server.py`
3. **Modify Loom**: Add `_register_third_party_tools()` to `loom/server.py`
4. **Parameters**: Extend `loom_legal/params.py` with all 26 parameter models
5. **Sources**: Implement clients using `SourceClient` base class pattern
6. **Tools**: Implement 26 tools using async/await pattern, with caching + error handling
7. **Tests**: Follow acceptance test template, aim for 80%+ coverage

Each tool should:
- Validate parameters using Pydantic models
- Use source client for data access
- Cache results with appropriate TTL
- Handle errors gracefully (fallback to cache)
- Return dict in standard format

All code should:
- Use type hints (strict mypy)
- Be formatted with Black
- Lint with Ruff
- Have docstrings (Google style)
- Be fully tested (unit + integration)

