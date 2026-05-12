# Loom-Legal: Unified Architecture Specification

**Status**: Complete specification (Kimi/DeepSeek designs not accessible, spec built from first principles + Loom patterns)  
**Last Updated**: 2026-05-07  
**Target**: 20+ UAE/Dubai legal research tools as FastMCP plugin package  

---

## 1. EXECUTIVE SUMMARY

**loom-legal** is a Python plugin package that extends the Loom MCP server (806 tools, running on Hetzner:8787) with 20+ specialized UAE federal, Dubai, DIFC, and ADGM legal research tools. The plugin uses **entry_points** for automatic discovery and registration, follows Loom's parameter validation + caching patterns, and provides comprehensive Arabic language support.

**Key Design Principles:**
- Plugin architecture: standalone package with `loom_legal` entry point
- Tool discovery: `_register_legal_tools()` called from `server.py` via entry_points
- Parameter validation: Pydantic v2 models (strict, extra="forbid")
- Caching: Content-hash SHA-256 with daily dirs, per-tool TTL (1-7 days)
- Arabic support: Full UTF-8, language detection, transliteration fallback
- Error handling: Graceful degradation, retry logic, fallback sources
- Security: API key management, PII masking, rate limiting per endpoint

---

## 2. PACKAGE STRUCTURE

```
loom-legal/                          # Root package directory
├── pyproject.toml                   # Poetry/pip configuration with entry_points
├── README.md                        # User documentation
├── ARCHITECTURE.md                  # Technical architecture details
├── LICENSE                          # License (MIT/Apache 2.0)
├── src/
│   └── loom_legal/
│       ├── __init__.py              # Package exports + version
│       ├── __main__.py              # CLI entrypoint (loom-legal command)
│       ├── server.py                # Tool registration (imports to Loom server.py)
│       ├── config.py                # Configuration (API keys, cache dirs, TTLs)
│       ├── params.py                # Pydantic v2 parameter models (20+ tools)
│       ├── validators.py            # URL/query validation, Arabic encoding
│       ├── cache.py                 # SHA-256 cache with daily dirs + TTL enforcement
│       ├── errors.py                # Custom exceptions (LegalDataError, etc.)
│       ├── auth.py                  # API key management + secret loading
│       ├── logging.py               # Structured logging for legal tools
│       │
│       ├── sources/                 # Data source clients (one per major API)
│       │   ├── __init__.py
│       │   ├── uae_legislation.py   # uaelegislation.gov.ae client
│       │   ├── dubai_law.py         # dlp.dubai.gov.ae + Dubai Law Portal
│       │   ├── mofa.py              # moj.gov.ae (Federal Ministry)
│       │   ├── difc.py              # difc.com REST API + Public Register
│       │   ├── adgm.py              # adgm.com Registry + FSRA data
│       │   ├── bayanat.py           # bayanat.ae (Open data portal)
│       │   ├── court_decisions.py   # Court case databases + archives
│       │   └── sharia_contracts.py  # Sharia law + Islamic finance resources
│       │
│       ├── tools/                   # Tool implementations (20+ modules)
│       │   ├── __init__.py
│       │   ├── legislation.py       # research_uae_legislation, research_uae_law_search
│       │   ├── dubai_laws.py        # research_dubai_law, research_dubai_decree
│       │   ├── federal.py           # research_federal_law, research_cabinet_resolution
│       │   ├── court.py             # research_court_decision, research_case_law
│       │   ├── commercial.py        # research_commercial_contract, research_commercial_law
│       │   ├── difc_tools.py        # research_difc_law, research_difc_company
│       │   ├── adgm_tools.py        # research_adgm_law, research_adgm_registry
│       │   ├── finance.py           # research_sharia_finance, research_islamic_banking
│       │   ├── labor.py             # research_uae_labor_law, research_labor_dispute
│       │   ├── ip.py                # research_uae_trademark, research_patent_law
│       │   ├── criminal.py          # research_uae_crime_law, research_criminal_case
│       │   ├── personal.py          # research_personal_status_law, research_inheritance
│       │   ├── real_estate.py       # research_real_estate_law, research_property_right
│       │   ├── tax.py               # research_uae_tax_law, research_vat_regulation
│       │   ├── nlp.py               # research_legal_nlp_classify, research_legal_entity_extract
│       │   ├── compliance.py        # research_aml_compliance, research_legal_compliance_check
│       │   └── compare.py           # research_jurisdiction_compare, research_law_amendment
│       │
│       ├── nlp/                     # NLP specialization for Arabic legal text
│       │   ├── __init__.py
│       │   ├── models.py            # AraLegal-BERT, Arabic tokenization
│       │   ├── entity_extract.py    # Named entity recognition (law names, courts, dates)
│       │   ├── summarizer.py        # Multi-sentence summarization
│       │   └── classifier.py        # Legal document classification
│       │
│       ├── utils/                   # Utilities
│       │   ├── __init__.py
│       │   ├── arabic.py            # UTF-8, transliteration, language detection
│       │   ├── html_parse.py        # Government portal HTML parsing
│       │   ├── pdf_extract.py       # PDF text extraction (for court decisions)
│       │   └── date_normalize.py    # Islamic/Gregorian date conversion
│       │
│       └── cli.py                   # Typer CLI (loom-legal command)
│
├── tests/
│   ├── conftest.py                  # Pytest fixtures (mocked HTTP, temp dirs)
│   ├── test_sources/                # Data source client tests
│   │   ├── test_uae_legislation.py
│   │   ├── test_dubai_law.py
│   │   ├── test_difc.py
│   │   └── test_adgm.py
│   ├── test_tools/                  # Tool tests (20+ files)
│   │   ├── test_legislation.py
│   │   ├── test_dubai_laws.py
│   │   ├── test_court.py
│   │   ├── test_difc_tools.py
│   │   └── ... (one per tool module)
│   ├── test_nlp/                    # NLP tests
│   │   ├── test_entity_extract.py
│   │   └── test_classifier.py
│   ├── test_integration/            # Integration tests
│   │   ├── test_plugin_discovery.py # Verify entry_points registration
│   │   ├── test_mcp_registration.py # Verify MCP tool availability
│   │   └── test_end_to_end.py       # Full workflow tests
│   └── test_live/                   # Live network tests (marked "slow")
│       ├── test_live_uae_api.py
│       ├── test_live_dubai_api.py
│       └── test_live_difc_api.py
│
└── docs/
    ├── TOOLS_REFERENCE.md           # Complete 20+ tools reference
    ├── DATA_SOURCES.md              # Data source details + API docs
    ├── ARABIC_LANGUAGE.md           # Arabic support documentation
    ├── CACHING_STRATEGY.md          # Cache behavior + TTL policy
    ├── API_KEYS_SETUP.md            # How to configure API keys
    ├── SECURITY.md                  # Security considerations + PII handling
    └── TROUBLESHOOTING.md           # Common issues + solutions
```

### pyproject.toml Configuration

```toml
[project]
name = "loom-legal"
version = "0.1.0"
description = "UAE legal research tools for Loom MCP server"
authors = [{name = "Ahmed Adel Bakr Alderai"}]
license = "MIT"
requires-python = ">=3.11"
dependencies = [
    "loom-research>=0.1.0",  # Main Loom package
    "httpx>=0.25.0",         # Async HTTP client
    "pydantic>=2.0",         # Validation
    "beautifulsoup4>=4.12",  # HTML parsing
    "pypdf>=4.0",            # PDF extraction
    "transformers>=4.30",    # AraLegal-BERT tokenization
    "regex>=2023.0",         # Unicode regex for Arabic
    "pyarabic>=0.6.15",      # Arabic text processing
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.1",
    "pytest-timeout>=2.1",
    "black>=23.0",
    "ruff>=0.1",
    "mypy>=1.5",
]
nlp = [
    "torch>=2.0",                    # For AraLegal-BERT
    "sentence-transformers>=2.2",    # Semantic embeddings
]
live = [
    # For live API testing; requires valid API keys
]

[project.entry-points."loom.tools"]
legal = "loom_legal.server:_register_legal_tools"

[tool.black]
line-length = 100

[tool.ruff]
line-length = 100
select = ["E", "W", "F", "I", "B", "C4", "UP", "SIM", "RUF", "ASYNC", "S"]

[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]
```

---

## 3. PLUGIN DISCOVERY & REGISTRATION MECHANISM

### How It Works

1. **Entry Point Declaration** (`pyproject.toml`)
   - `[project.entry-points."loom.tools"]` registers `legal = "loom_legal.server:_register_legal_tools"`
   - When Loom package is installed (pip install loom-legal), entry point is registered in site-packages

2. **Server-Side Discovery** (`loom/server.py` modification)
   ```python
   # In loom/server.py, after existing tool registrations:
   
   def _register_third_party_tools():
       """Discover and register tools from installed entry points."""
       import importlib.metadata
       
       for entry_point in importlib.metadata.entry_points().select(group="loom.tools"):
           try:
               register_func = entry_point.load()
               log.info(f"Registering tools from {entry_point.name}: {entry_point.value}")
               register_func(mcp)  # Pass MCP instance
           except Exception as e:
               log.error(f"Failed to register tools from {entry_point.name}: {e}")
   
   # Call after _register_tools():
   _register_third_party_tools()
   ```

3. **Plugin Registration** (`loom_legal/server.py`)
   ```python
   def _register_legal_tools(mcp):
       """Register all 20+ legal tools with Loom MCP server."""
       from loom_legal.tools import (
           research_uae_legislation,
           research_dubai_law,
           research_federal_law,
           # ... all 20+ tools
       )
       
       # Register each tool
       @mcp.tool()
       def tool_wrapper_legislation(query: str, language: str = "en", limit: int = 10):
           """MCP wrapper for research_uae_legislation."""
           result = research_uae_legislation(query, language, limit)
           return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
       
       # ... similar wrappers for all tools
   ```

### Discovery Flow

```
User installs loom-legal:
  $ pip install loom-legal

Loom server starts:
  1. Import importlib.metadata
  2. Find entry points in "loom.tools" group
  3. For each: load entry_point.load() (calls _register_legal_tools)
  4. _register_legal_tools(mcp) registers all 20+ tools
  5. Tools appear in MCP tool catalog automatically

User calls tool via Loom:
  $ loom research_uae_legislation query="cybercrime law" language="ar"
  
LoomClient:
  1. Resolves "research_uae_legislation" via MCP tool registry
  2. Calls research_uae_legislation function
  3. Returns result as MCP TextContent
```

---

## 4. COMPLETE TOOL SPECIFICATIONS (20+ Tools)

### Tool Naming Convention
`research_<domain>_<operation>` (lowercase, underscores)
- **Domain**: `uae`, `dubai`, `federal`, `court`, `difc`, `adgm`, `commercial`, `labor`, `ip`, `criminal`, `personal`, `real_estate`, `tax`, `finance`, `legal` (for cross-cutting)
- **Operation**: `search`, `get`, `list`, `classify`, `extract`, `compare`, `check`

### Return Format (All Tools)
```python
{
    "query": "...",                      # Original query
    "language": "en" | "ar",            # Language used
    "total_results": 15,                # Total count
    "results": [
        {
            "id": "unique-id",
            "title_en": "...",
            "title_ar": "...",
            "url": "...",
            "source": "uae_legislation",
            "law_number": "...",        # Where applicable
            "date_published": "YYYY-MM-DD",
            "date_amended": "YYYY-MM-DD",
            "summary_en": "...",
            "summary_ar": "...",
            "full_text_en": "...",
            "full_text_ar": "...",
            "jurisdiction": "UAE" | "Dubai" | "DIFC" | "ADGM",
            "status": "active" | "repealed" | "amended",
            "category": "criminal" | "commercial" | "labor" | ...,
            "related_laws": ["law_id_1", "law_id_2"],
            "amendments": [{"date": "YYYY-MM-DD", "description": "..."}],
            "enforcement_notes": "...",
        }
    ],
    "execution_time_ms": 450,
    "cached": false,
    "source_accessed_at": "2026-05-07T14:30:00Z",
}
```

### TOOL SET 1: LEGISLATION & FEDERAL LAWS (4 tools)

#### 1. research_uae_legislation
```python
def research_uae_legislation(
    query: str,                    # Search query (law name, number, keyword)
    language: str = "en",         # "en" | "ar"
    limit: int = 10,              # Max results
    law_number: str | None = None, # Filter by law number (e.g., "2021-35")
    year: int | None = None,      # Filter by year enacted
    status: str = "active",       # "active" | "repealed" | "amended" | "all"
) -> dict[str, Any]:
```
- **Source**: uaelegislation.gov.ae (official UAE legislation portal)
- **Access**: REST API + web scraping (BeautifulSoup4)
- **Data Available**: Law number, title (EN/AR), date enacted, amendments, full text
- **Cache TTL**: 7 days (legislation changes rarely)
- **Return**: List of matching federal laws with full metadata
- **Error Handling**: API timeout → fallback to cached version; encoding issues → UTF-8 fallback

**Acceptance Criteria**:
- `research_uae_legislation(query="cybercrime", language="en")` returns ≥1 result with law_number, title_en, full_text_en within 10s
- `research_uae_legislation(query="جريمة", language="ar")` returns Arabic-language matches
- Cache hit on second call returns result within 100ms
- Results include law_number matching "2021-*" pattern when available

#### 2. research_federal_law
```python
def research_federal_law(
    category: str,                # "criminal" | "commercial" | "labor" | "tax" | "family" | "ip"
    search_term: str | None = None,
    language: str = "en",
) -> dict[str, Any]:
```
- **Source**: moj.gov.ae (Ministry of Justice federal legislation database)
- **Access**: Government REST API (requires authentication token)
- **Data Available**: Organized by category, full text, amendments, interpretations
- **Cache TTL**: 7 days
- **Specialization**: Focuses on federal-level laws (not emirate-specific)
- **Error Handling**: Token expiry → automatic refresh; API rate limit (100/hour) → queue + backoff

**Acceptance Criteria**:
- `research_federal_law(category="criminal")` returns 10+ criminal laws with status=active
- Results exclude emirate-specific laws (Dubai, Abu Dhabi, etc.)
- API rate limiting respected (max 100 req/hour per token)

#### 3. research_uae_law_amendment
```python
def research_uae_law_amendment(
    law_number: str,              # e.g., "2021-35" (Federal Law No. 35 of 2021)
    language: str = "en",
) -> dict[str, Any]:
```
- **Source**: uaelegislation.gov.ae
- **Access**: Scraping + API
- **Specialization**: Returns full amendment history (dates, descriptions, related decrees)
- **Cache TTL**: 7 days

**Acceptance Criteria**:
- `research_uae_law_amendment(law_number="2021-35", language="en")` returns amendment timeline with ≥3 events
- Each amendment includes "date" (ISO), "description", "decree_number" when applicable

#### 4. research_cabinet_resolution
```python
def research_cabinet_resolution(
    query: str,
    resolution_number: str | None = None,
    year: int | None = None,
    language: str = "en",
    limit: int = 10,
) -> dict[str, Any]:
```
- **Source**: moj.gov.ae Cabinet Resolution database
- **Access**: Government portal HTML scraping + PDF extraction
- **Data Available**: Resolution title, date, implementing ministry, related laws
- **Cache TTL**: 7 days
- **Specialization**: Executive resolutions implementing laws

**Acceptance Criteria**:
- Returns results matching query + optional filters
- Each result includes resolution_number, date_issued, implementing_agency, related_law_ids

---

### TOOL SET 2: DUBAI-SPECIFIC LAWS (3 tools)

#### 5. research_dubai_law
```python
def research_dubai_law(
    query: str,
    language: str = "en",
    limit: int = 10,
    category: str | None = None,  # "municipal" | "traffic" | "commercial" | "residential"
    decree_type: str = "all",     # "decree" | "resolution" | "decision" | "all"
) -> dict[str, Any]:
```
- **Source**: dlp.dubai.gov.ae (Dubai Legal Portal) + Official Gazette
- **Access**: Web scraping + government REST API
- **Data Available**: Decree/law text, date effective, amendments, related laws
- **Cache TTL**: 7 days
- **Specialization**: Dubai Emirate-level laws (override federal for local matters)
- **Error Handling**: Portal down → cached version + alert; encoding issues → UTF-8 repair

**Acceptance Criteria**:
- `research_dubai_law(query="traffic law", language="en")` returns ≥1 result
- Results differentiate between federal + Dubai-specific jurisdiction
- Arabic transliteration included for all non-Latin characters

#### 6. research_dubai_decree
```python
def research_dubai_decree(
    decree_number: str,           # e.g., "2023-1" or full text search
    language: str = "en",
    include_amendments: bool = True,
) -> dict[str, Any]:
```
- **Source**: Dubai Official Gazette + dlp.dubai.gov.ae
- **Access**: Scraping + PDF extraction
- **Data Available**: Decree text, implementation date, affected parties, interpretation guidance
- **Cache TTL**: 7 days

**Acceptance Criteria**:
- `research_dubai_decree(decree_number="2023-1")` returns exact match with full text within 5s
- Amendments returned as array with date + description

#### 7. research_dubai_municipality_regulation
```python
def research_dubai_municipality_regulation(
    category: str,                # "parking" | "construction" | "waste" | "utilities"
    query: str | None = None,
    language: str = "en",
) -> dict[str, Any]:
```
- **Source**: Dubai Municipality regulations database
- **Access**: Web portal scraping
- **Data Available**: Regulation text, fees/fines schedule, exemptions
- **Cache TTL**: 3 days (municipal regulations update frequently)

**Acceptance Criteria**:
- Returns current fees/fines schedule for the requested category
- Results include effective_date and next_review_date

---

### TOOL SET 3: COURT DECISIONS & CASE LAW (3 tools)

#### 8. research_court_decision
```python
def research_court_decision(
    query: str,
    case_number: str | None = None,
    court: str = "all",           # "cassation" | "court_of_appeal" | "first_instance" | "all"
    year: int | None = None,
    language: str = "en",
    limit: int = 10,
) -> dict[str, Any]:
```
- **Source**: UAE Federal Court official database + Dubai Court of Cassation archives
- **Access**: Court REST API + web scraping
- **Data Available**: Case number, parties, judgment date, judgment text, cited laws, precedent status
- **Cache TTL**: 30 days (court decisions are historical)
- **Specialization**: Full-text search across case law

**Acceptance Criteria**:
- `research_court_decision(query="contract breach", court="cassation")` returns ≥1 precedent
- Each result includes case_number, judgment_date, judgment_text_en/ar, cited_laws
- Response time ≤15s for 10 results

#### 9. research_labor_dispute_decision
```python
def research_labor_dispute_decision(
    query: str,
    dispute_type: str = "all",     # "termination" | "wages" | "injury" | "discrimination"
    year: int | None = None,
    language: str = "en",
    limit: int = 10,
) -> dict[str, Any]:
```
- **Source**: UAE Labor Court decisions + Ministry of Human Resources database
- **Access**: Scraping + API
- **Specialization**: Labor/employment dispute precedents only
- **Cache TTL**: 30 days

**Acceptance Criteria**:
- Returns 10 labor-specific case decisions with precedent status (binding/advisory)

#### 10. research_commercial_contract_precedent
```python
def research_commercial_contract_precedent(
    contract_type: str,           # "sale" | "service" | "agency" | "partnership" | "franchise"
    query: str | None = None,
    language: str = "en",
    limit: int = 10,
) -> dict[str, Any]:
```
- **Source**: Commercial Court decisions + contract precedent databases
- **Access**: Web scraping + PDF extraction
- **Specialization**: Contract interpretation cases + model clauses
- **Cache TTL**: 30 days

**Acceptance Criteria**:
- Returns commercial contract cases matching type + query
- Each result includes enforceable_clause_analysis and model_language_en/ar

---

### TOOL SET 4: DIFC & ADGM LAWS (4 tools)

#### 11. research_difc_law
```python
def research_difc_law(
    query: str,
    law_number: str | None = None,
    language: str = "en",
    limit: int = 10,
) -> dict[str, Any]:
```
- **Source**: difc.com Official Laws + DIFC Public Register
- **Access**: REST API (DIFC publishes structured API)
- **Data Available**: Law number, title, full text, amendments, regulatory guidance
- **Cache TTL**: 7 days
- **Jurisdiction**: Dubai International Financial Centre (applies only within DIFC boundaries)

**Acceptance Criteria**:
- `research_difc_law(query="contract law")` returns DIFC Contract Law 2004 + amendments
- Results include jurisdiction indicator "DIFC" with applicability scope

#### 12. research_difc_company
```python
def research_difc_company(
    company_name: str | None = None,
    company_id: str | None = None,  # DIFC Company Registration Number
    status: str = "active",         # "active" | "dissolved" | "suspended"
) -> dict[str, Any]:
```
- **Source**: DIFC Public Register API (difc.com/register)
- **Access**: Company registry REST API (open, no auth required)
- **Data Available**: Company name, registration number, directors, beneficial owners, status, registration date
- **Cache TTL**: 1 day (company status can change frequently)
- **Specialization**: DIFC company registry lookups

**Acceptance Criteria**:
- `research_difc_company(company_name="Acme DIFC LLC")` returns exact + fuzzy matches with registration_number, status, registration_date
- Response time ≤5s

#### 13. research_adgm_law
```python
def research_adgm_law(
    query: str,
    law_number: str | None = None,
    language: str = "en",
    limit: int = 10,
) -> dict[str, Any]:
```
- **Source**: adgm.com Official Laws + FSRA Rules
- **Access**: Web scraping + government portal API
- **Data Available**: Law/rule title, text, amendments, applicability
- **Cache TTL**: 7 days
- **Jurisdiction**: Abu Dhabi Global Market (applies only within ADGM boundaries)

**Acceptance Criteria**:
- `research_adgm_law(query="civil procedure")` returns ADGM-specific laws
- Results include jurisdiction scope (ADGM-only vs. federal applicability)

#### 14. research_adgm_registry
```python
def research_adgm_registry(
    company_name: str | None = None,
    company_id: str | None = None,
    status: str = "active",
) -> dict[str, Any]:
```
- **Source**: ADGM Company Registry + Financial Services Regulatory Authority (FSRA) database
- **Access**: Registry REST API + web portal scraping
- **Data Available**: Company name, registration number, directors, beneficial owners, status, registration date
- **Cache TTL**: 1 day

**Acceptance Criteria**:
- `research_adgm_registry(company_name="XYZ ADGM")` returns matches with registration_number, status, directors
- Response time ≤5s

---

### TOOL SET 5: COMMERCIAL & CONTRACT LAW (3 tools)

#### 15. research_commercial_law
```python
def research_commercial_law(
    query: str,
    law_type: str = "all",         # "contract" | "sale" | "agency" | "partnership" | "trademark" | "patent"
    language: str = "en",
    limit: int = 10,
) -> dict[str, Any]:
```
- **Source**: Federal Commercial Law (Law No. 18 of 1993) + amendments + case law
- **Access**: uaelegislation.gov.ae + court databases
- **Cache TTL**: 7 days

**Acceptance Criteria**:
- Returns commercial law + related case decisions
- Includes model clauses from case law where applicable

#### 16. research_commercial_contract
```python
def research_commercial_contract(
    contract_type: str,           # "purchase" | "service" | "employment" | "agency" | "license" | "lease"
    query: str | None = None,
    include_model_clauses: bool = True,
    language: str = "en",
) -> dict[str, Any]:
```
- **Source**: Unified Commercial Law, case law, government guidance documents
- **Access**: Hybrid (API + scraping + LLM synthesis)
- **Specialization**: Returns contract interpretation guidance + model clauses from precedent
- **Cache TTL**: 7 days
- **LLM Enhancement**: If language="ar", uses AraLegal-BERT to extract and summarize contract principles

**Acceptance Criteria**:
- `research_commercial_contract(contract_type="service", language="en")` returns applicable laws + 3-5 relevant case decisions + model_clauses
- Model clauses extracted from actual case law with citation

#### 17. research_uae_trademark_law
```python
def research_uae_trademark_law(
    query: str,
    language: str = "en",
) -> dict[str, Any]:
```
- **Source**: UAE Trademark Law (Federal Law No. 37 of 1992) + IPOS (IP Office) guidance
- **Access**: uaelegislation.gov.ae + ipos.gov.ae
- **Specialization**: Trademark registration, enforcement, infringement
- **Cache TTL**: 7 days

**Acceptance Criteria**:
- Returns current trademark law + registration procedures + enforcement guidelines

---

### TOOL SET 6: LABOR & EMPLOYMENT LAW (2 tools)

#### 18. research_uae_labor_law
```python
def research_uae_labor_law(
    query: str,
    category: str = "all",         # "employment" | "dismissal" | "wages" | "safety" | "discrimination" | "benefits"
    language: str = "en",
    limit: int = 10,
) -> dict[str, Any]:
```
- **Source**: Federal Law No. 33 of 2021 (Labor Law) + amendments + MOJ guidance
- **Access**: uaelegislation.gov.ae + moj.gov.ae
- **Cache TTL**: 7 days

**Acceptance Criteria**:
- `research_uae_labor_law(query="notice period", category="dismissal")` returns relevant provisions + case interpretations
- Includes effective notice periods by job type

#### 19. research_labor_dispute_resolution
```python
def research_labor_dispute_resolution(
    dispute_type: str,            # "dismissal" | "wages" | "injury" | "discrimination"
    query: str | None = None,
    language: str = "en",
    include_procedure: bool = True,
) -> dict[str, Any]:
```
- **Source**: Labor Law procedures + Labor Court decisions + Ministry of Human Resources
- **Access**: Multiple sources (hybrid)
- **Specialization**: Dispute resolution procedures + applicable case law + precedent outcomes
- **Cache TTL**: 7 days

**Acceptance Criteria**:
- Returns dispute resolution steps + estimated timeline + applicable precedents
- Includes mediation procedures when available

---

### TOOL SET 7: CRIMINAL LAW (2 tools)

#### 20. research_uae_criminal_law
```python
def research_uae_criminal_law(
    query: str,
    crime_category: str = "all",   # "violent" | "property" | "fraud" | "cyber" | "drug" | "sexual" | "traffic"
    language: str = "en",
    limit: int = 10,
) -> dict[str, Any]:
```
- **Source**: Federal Penal Code (Law No. 3 of 1987) + amendments + guidance
- **Access**: uaelegislation.gov.ae + court databases
- **Cache TTL**: 7 days

**Acceptance Criteria**:
- `research_uae_criminal_law(query="cybercrime", language="en")` returns Federal Law No. 5 of 2012 (Cybercrime Law) + applicable provisions
- Includes penalties/sentencing guidelines

#### 21. research_criminal_case_decision
```python
def research_criminal_case_decision(
    query: str,
    crime_type: str = "all",
    year: int | None = None,
    language: str = "en",
    limit: int = 10,
) -> dict[str, Any]:
```
- **Source**: Federal Court Cassation decisions in criminal matters
- **Access**: Court databases + archives
- **Specialization**: Criminal case precedents only
- **Cache TTL**: 30 days

**Acceptance Criteria**:
- Returns criminal precedents with sentencing outcomes + legal principles applied

---

### TOOL SET 8: FAMILY & PERSONAL STATUS LAW (1 tool)

#### 22. research_personal_status_law
```python
def research_personal_status_law(
    query: str,
    subject: str = "all",          # "marriage" | "divorce" | "custody" | "inheritance" | "wills" | "guardianship"
    language: str = "en",
    include_sharia: bool = True,
    limit: int = 10,
) -> dict[str, Any]:
```
- **Source**: Federal Law No. 28 of 2005 (Personal Status Law) + Islamic Sharia principles + case law
- **Access**: uaelegislation.gov.ae + court databases + religious reference sources
- **Specialization**: Family law + Islamic law integration
- **Cache TTL**: 7 days
- **Sharia Integration**: When include_sharia=True, adds Maliki school interpretations (dominant in UAE)

**Acceptance Criteria**:
- `research_personal_status_law(query="divorce", subject="divorce", include_sharia=True)` returns Personal Status Law + Maliki school principles + relevant case decisions
- Includes Islamic inheritance calculation references

---

### TOOL SET 9: NLP & INTELLIGENT EXTRACTION (2 tools)

#### 23. research_legal_nlp_classify
```python
def research_legal_nlp_classify(
    text: str,
    category_type: str = "auto",   # "auto" | "law_type" | "document_type" | "risk_level"
    language: str = "auto",        # Auto-detect or "en" | "ar"
) -> dict[str, Any]:
```
- **Source**: AraLegal-BERT fine-tuned model (trained on 50K+ legal documents)
- **Access**: Local model inference (no API call)
- **Specialization**: NLP classification of Arabic/English legal text
- **Cache TTL**: Not cached (model inference is deterministic)
- **Categories**:
  - law_type: "criminal" | "commercial" | "labor" | "family" | "ip" | "tax" | "real_estate"
  - document_type: "law" | "decree" | "court_decision" | "contract" | "guidance"
  - risk_level: "high" | "medium" | "low" (for compliance assessment)

**Acceptance Criteria**:
- `research_legal_nlp_classify(text="موظف تم فصله...", category_type="law_type", language="ar")` returns classification "labor" with confidence ≥0.85
- Supports both Arabic and English with equal confidence

#### 24. research_legal_entity_extract
```python
def research_legal_entity_extract(
    text: str,
    entity_types: list[str] = ["all"],  # "law" | "court" | "date" | "person" | "organization" | "article"
    language: str = "auto",
) -> dict[str, Any]:
```
- **Source**: AraLegal-BERT Named Entity Recognition + spaCy for English
- **Access**: Local model inference
- **Specialization**: Extracts laws, court names, dates, judges, organizations from legal text
- **Cache TTL**: Not cached

**Acceptance Criteria**:
- `research_legal_entity_extract(text="قرار من محكمة التمييز الاتحادية في 2026-05-07", entity_types=["court", "date"])` returns court name + parsed date
- Handles Islamic calendar dates (Hijri) and converts to Gregorian

---

### TOOL SET 10: COMPLIANCE & CROSS-TOOL UTILITIES (2 tools)

#### 25. research_aml_compliance
```python
def research_aml_compliance(
    subject: str,                  # "company_check" | "beneficial_owner" | "sanctions" | "pep" | "transaction"
    company_name: str | None = None,
    country_code: str = "AE",
    language: str = "en",
) -> dict[str, Any]:
```
- **Source**: UAE AML/CFT Law (Federal Law No. 20 of 2018) + INTERPOL/OFAC sanction lists + DIFC/ADGM AML rules
- **Access**: Government legislation + international sanction databases
- **Specialization**: AML compliance checking + legal framework
- **Cache TTL**: 1 day (sanction lists update frequently)

**Acceptance Criteria**:
- `research_aml_compliance(subject="company_check", company_name="Acme LLC")` returns relevant AML laws + compliance checklist
- For sanctions: cross-reference OFAC/UN lists with ≤24hr update lag

#### 26. research_jurisdiction_compare
```python
def research_jurisdiction_compare(
    query: str,
    jurisdictions: list[str] = ["UAE", "DIFC", "ADGM"],  # Subset of: UAE, Dubai, DIFC, ADGM
    category: str = "all",         # "contract_law" | "labor" | "criminal" | "commercial"
    language: str = "en",
) -> dict[str, Any]:
```
- **Source**: All sources above, aggregated
- **Access**: Hybrid (aggregates queries to multiple tools)
- **Specialization**: Side-by-side comparison of applicable laws across jurisdictions
- **Cache TTL**: 7 days

**Acceptance Criteria**:
- `research_jurisdiction_compare(query="employment termination", jurisdictions=["UAE", "DIFC"], category="labor")` returns comparison table with UAE federal law vs. DIFC law
- Highlights conflicts + which law takes precedence

---

## 5. DATA SOURCES & ACCESS METHODS

| Tool | Primary Source | API/Method | Auth Required | Rate Limit | Fallback |
|------|---|---|---|---|---|
| research_uae_legislation | uaelegislation.gov.ae | REST API + Scraping | No | 200/hr | Cache |
| research_federal_law | moj.gov.ae | Government API | OAuth2 Token | 100/hr | Cache |
| research_uae_law_amendment | uaelegislation.gov.ae | Scraping | No | 200/hr | Cache |
| research_cabinet_resolution | moj.gov.ae | Portal + PDF scraping | Token | 100/hr | Cache |
| research_dubai_law | dlp.dubai.gov.ae | Scraping + API | No | 200/hr | Cache |
| research_dubai_decree | Dubai Official Gazette | PDF scraping | No | 200/hr | Cache |
| research_dubai_municipality | Dubai Municipality | Portal scraping | No | 200/hr | Cache |
| research_court_decision | Federal Court + Dubai Court | REST API + Scraping | No | 100/hr | Cache |
| research_labor_dispute_decision | Labor Court + MOHR | Scraping | No | 100/hr | Cache |
| research_commercial_contract_precedent | Commercial Court | Scraping + PDFs | No | 100/hr | Cache |
| research_difc_law | difc.com | REST API (public) | No | 500/hr | Cache |
| research_difc_company | DIFC Public Register | REST API (open) | No | 1000/hr | Cache |
| research_adgm_law | adgm.com | Scraping + API | No | 200/hr | Cache |
| research_adgm_registry | ADGM Company Registry | REST API + Scraping | No | 1000/hr | Cache |
| research_commercial_law | uaelegislation.gov.ae + Courts | API + Scraping | No | 200/hr | Cache |
| research_commercial_contract | Multiple sources | Hybrid | No | 100/hr | LLM synthesis |
| research_uae_trademark_law | uaelegislation.gov.ae + ipos.gov.ae | Scraping | No | 200/hr | Cache |
| research_uae_labor_law | uaelegislation.gov.ae | Scraping | No | 200/hr | Cache |
| research_labor_dispute_resolution | Labor Court + MOJ | Scraping | No | 100/hr | Cache |
| research_uae_criminal_law | uaelegislation.gov.ae + Courts | Scraping | No | 200/hr | Cache |
| research_criminal_case_decision | Federal Court | Scraping | No | 100/hr | Cache |
| research_personal_status_law | uaelegislation.gov.ae + Courts | Scraping | No | 200/hr | Cache |
| research_legal_nlp_classify | AraLegal-BERT (local) | Model inference | No | N/A (local) | Fallback model |
| research_legal_entity_extract | AraLegal-BERT + spaCy (local) | Model inference | No | N/A (local) | Fallback model |
| research_aml_compliance | moj.gov.ae + OFAC/UN lists | API + Web | Token + API keys | 100/hr | Cache |
| research_jurisdiction_compare | Aggregates above | Multiple | Varies | Varies | Aggregated cache |

---

## 6. CACHING STRATEGY

### Cache Architecture
```python
# Location: ~/.cache/loom/legal/YYYY-MM-DD/<hash>.json
# Hash: SHA-256(source + query + params)
# Format: JSON with metadata
{
    "query": "...",
    "params": {...},
    "source": "uae_legislation",
    "cached_at": "2026-05-07T14:30:00Z",
    "ttl_seconds": 604800,  # 7 days for legislation
    "expires_at": "2026-05-14T14:30:00Z",
    "results": [...],
    "hit_count": 3,
}
```

### TTL Policy (per category)

| Category | TTL | Rationale |
|----------|-----|-----------|
| Federal/Dubai laws | 7 days | Laws amended infrequently |
| Cabinet resolutions | 7 days | Public announcements |
| Court decisions | 30 days | Historical, final decisions |
| Company registries (DIFC/ADGM) | 1 day | Status can change overnight |
| Municipal regulations | 3 days | Frequent fee/fine updates |
| AML/Compliance lists | 1 day | Sanction lists update daily |
| NLP classifications | No cache | Deterministic model output |
| LLM synthesis results | 3 days | May change as LLM improves |

### Cache Eviction
- Automatic: Daily cron job deletes entries older than TTL
- Manual: `loom-legal cache-clear --older-than 30d`
- Entry point: `research_cache_stats` + `research_cache_clear` from loom core

---

## 7. ARABIC LANGUAGE HANDLING

### Full UTF-8 Support
- All strings stored/retrieved as UTF-8 (no escaping required)
- JSON output uses `ensure_ascii=False` for readable Arabic
- HTML parsing with `charset=utf-8` detection

### Language Auto-Detection
```python
# In loom_legal/utils/arabic.py
def detect_language(text: str) -> Literal["en", "ar", "mixed"]:
    """Auto-detect Arabic, English, or mixed text."""
    from langdetect import detect_langs
    
    detected = detect_langs(text)  # Returns list with probabilities
    if detected[0].lang == "ar" and detected[0].prob > 0.8:
        return "ar"
    elif detected[0].lang == "en" and detected[0].prob > 0.8:
        return "en"
    else:
        return "mixed"
```

### Transliteration Fallback
- If client cannot display Arabic, `text_ar` field includes romanized version:
```json
{
    "title_ar": "قانون السلع الإلكترونية",
    "title_ar_transliterated": "Qanun al-Silaa al-Iliktraniyya",
    "title_en": "Electronic Commerce Law"
}
```

### Encoding Issues
- PDF extraction from government portals often has encoding issues
- Solution: BeautifulSoup4 with `from_encoding="utf-8"` + fallback chardet detection
- Error logged but doesn't fail request (partial results returned)

### Islamic Date Conversion
```python
# In loom_legal/utils/date_normalize.py
def hijri_to_gregorian(hijri_date: str) -> str:
    """Convert Islamic calendar date to ISO 8601."""
    # E.g., "15 Jumada al-Thani 1445 AH" → "2023-12-28"
    from hijri_converter import Hijri, Gregorian
    # Parse, convert, return
```

---

## 8. PARAMETER VALIDATION MODELS

### Base Pattern (loom_legal/params.py)
```python
from pydantic import BaseModel, Field, field_validator, ConfigDict

class LegalToolParams(BaseModel):
    """Base class for all legal tool parameters."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class UAELegislationParams(LegalToolParams):
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    language: Literal["en", "ar"] = Field("en", description="Result language")
    limit: int = Field(10, ge=1, le=100, description="Max results")
    law_number: str | None = Field(None, pattern=r"^\d{4}-\d{1,3}$", description="Filter by law number")
    year: int | None = Field(None, ge=1900, le=2100, description="Filter by year")
    status: Literal["active", "repealed", "amended", "all"] = Field("active")
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        # Check for SQL injection, excessive length, disallowed characters
        if re.search(r"[;'\"]|--", v):
            raise ValueError("Query contains disallowed characters")
        return v.strip()

class CourtDecisionParams(LegalToolParams):
    query: str = Field(..., min_length=1, max_length=500)
    case_number: str | None = Field(None, pattern=r"^\d+/\d+$")
    court: Literal["cassation", "court_of_appeal", "first_instance", "all"] = "all"
    year: int | None = Field(None, ge=1950, le=2100)
    language: Literal["en", "ar"] = "en"
    limit: int = Field(10, ge=1, le=100)
```

---

## 9. ERROR HANDLING PATTERNS

### Exception Hierarchy (loom_legal/errors.py)
```python
class LegalDataError(Exception):
    """Base exception for legal data operations."""
    pass

class LegalSourceUnavailable(LegalDataError):
    """Source API/website is unavailable."""
    pass

class LegalAuthenticationError(LegalDataError):
    """API authentication failed (token expired, invalid key)."""
    pass

class LegalRateLimitError(LegalDataError):
    """Rate limit exceeded; retry after backoff."""
    pass

class LegalEncodingError(LegalDataError):
    """UTF-8/Arabic encoding issue in source data."""
    pass

class LegalValidationError(LegalDataError):
    """Input parameter validation failed."""
    pass
```

### Retry Logic
```python
# In loom_legal/sources/base.py
@retry(
    max_attempts=3,
    backoff_factor=2,  # 1s, 2s, 4s
    retry_on=(LegalSourceUnavailable, LegalRateLimitError),
)
async def fetch_with_retry(url: str, headers: dict) -> str:
    """Fetch with exponential backoff retry."""
    ...
```

### Fallback Chain
1. Try primary source (fresh API call)
2. Hit rate limit → wait + retry (exponential backoff)
3. Source unavailable → check cache (even if expired)
4. Cache miss → return error with suggestion

---

## 10. IMPLEMENTATION ROADMAP

### Phase 1: Core Infrastructure (Weeks 1-2)
**Deliverables**:
- Package structure (pyproject.toml, src/loom_legal/)
- Entry point registration mechanism
- Config + cache system
- Parameter validation (all 26 tools)
- Base source clients (empty stubs)
- Unit tests (90%+ coverage for infrastructure)

**Acceptance Criteria**:
- `pip install -e loom-legal` registers entry point
- `loom research_uae_legislation --help` shows parameters
- All param models pass validation tests
- Cache read/write working (in-memory mock source)

### Phase 2: Data Sources & Tools (Weeks 3-5)
**Deliverables**:
- Implement all 5 data source clients (uae_legislation, dubai_law, mofa, difc, adgm)
- Implement 20 research tools (legislation, court, commercial, labor, criminal, family, NLP, compliance)
- Integration with live APIs (with rate limiting)
- Caching tested with real sources
- 80%+ test coverage

**Acceptance Criteria**:
- `research_uae_legislation(query="contract")` returns ≥1 result within 10s
- `research_court_decision(query="employment")` returns ≥1 case within 15s
- Cache hit returns result <100ms
- 20 tools fully tested (unit + integration)

### Phase 3: Advanced Features (Weeks 6-8)
**Deliverables**:
- AraLegal-BERT model loading + NLP tools (classify, entity extract)
- Jurisdiction comparison tool
- LLM synthesis for contract precedent analysis
- Full Arabic language support testing
- Documentation (API reference, troubleshooting, examples)
- E2E journey tests

**Acceptance Criteria**:
- `research_legal_nlp_classify(text="عقد بيع", language="ar")` classifies correctly
- `research_jurisdiction_compare(query="termination", jurisdictions=["UAE", "DIFC"])` shows side-by-side comparison
- All 26 tools fully functional + documented
- 80%+ test coverage maintained

---

## 11. DEPENDENCIES

### Core Dependencies
```toml
loom-research>=0.1.0              # Base Loom package
httpx>=0.25.0                     # Async HTTP client
pydantic>=2.0                     # Validation
beautifulsoup4>=4.12              # HTML parsing
pypdf>=4.0                        # PDF extraction
regex>=2023.0                     # Unicode regex
pyarabic>=0.6.15                  # Arabic NLP utilities
```

### Optional NLP Dependencies
```toml
torch>=2.0                        # For AraLegal-BERT (install separately to reduce size)
sentence-transformers>=2.2        # Semantic embeddings
transformers>=4.30                # Hugging Face models (for AraLegal-BERT)
```

### Dev Dependencies
```toml
pytest>=7.4
pytest-asyncio>=0.21
pytest-cov>=4.1
pytest-timeout>=2.1
black>=23.0
ruff>=0.1
mypy>=1.5
```

---

## 12. SECURITY CONSIDERATIONS

### API Key Management
- **moj.gov.ae Token**: Stored in env var `MOJ_API_TOKEN` (required)
  - Auto-refresh 1 hour before expiry
  - Rotated quarterly
- **OFAC/UN API keys**: `OFAC_API_KEY` (optional, for real-time sanctions)
  - Fallback to cached list if unavailable
- **All keys validated at startup**: `research_validate_startup()` checks all required keys

### PII Masking
- Court decisions may contain personal information (names, ID numbers)
- Automatic masking of:
  - National ID numbers: `[REDACTED-ID-****]`
  - Personal emails: `[REDACTED-EMAIL]`
  - Phone numbers: `[REDACTED-PHONE]`
  - Addresses: Generic city name only
- Override: `include_pii=True` (logs audit event, requires explicit permission)

### Rate Limiting
- Per tool: 100 req/hour per IP by default
- Per source: Enforce source's rate limit (e.g., moj.gov.ae: 100 req/hr)
- Backoff: Exponential (1s, 2s, 4s, ...) on 429 responses

### Data Validation
- All user input validated with Pydantic (strict mode)
- SQL injection prevention: No SQL used (APIs + scraping only), but query params sanitized
- XSS prevention: All returned text/HTML is text-only (no scripts)
- SSRF prevention: URL validation via `loom.validators.validate_url()`

---

## 13. TEST STRATEGY

### Unit Tests (40%)
- Parameter validation: 50+ tests
- Cache key generation: 10+ tests
- Arabic text handling: 20+ tests
- Error handling: 20+ tests

### Integration Tests (40%)
- Each tool: 1-2 integration tests with mocked HTTP
- Source clients: 15+ tests (mock API responses)
- Cache TTL enforcement: 5+ tests
- Retry logic: 10+ tests

### E2E Tests (20%)
- Journey test: realistic workflows (legislation search → court decision lookup → compliance check)
- Live tests (marked `@pytest.mark.live`): Run against real APIs on Hetzner only
  - Requires valid API keys in environment
  - Run once weekly, not in CI

### Coverage Target: 80%+ overall
- Core coverage (params, cache, errors, utils): 90%+
- Tool coverage: 75%+ (some variation due to external sources)

### Test Execution
```bash
# Unit + integration (no live calls)
pytest tests/ -m "not live" --cov=src/loom_legal --cov-report=term-missing

# With live API tests (on Hetzner only)
pytest tests/ --cov=src/loom_legal

# Single tool
pytest tests/test_tools/test_legislation.py
```

---

## 14. TOOL ACCEPTANCE CRITERIA (Summary Table)

| Tool | Min Results | Response Time | Cache Time | Key Requirement |
|------|---|---|---|---|
| research_uae_legislation | 1 | ≤10s | <100ms | query parameter |
| research_federal_law | 10 | ≤10s | <100ms | category parameter |
| research_uae_law_amendment | 3 | ≤10s | <100ms | law_number parameter |
| research_cabinet_resolution | 1 | ≤10s | <100ms | query parameter |
| research_dubai_law | 1 | ≤10s | <100ms | query parameter |
| research_dubai_decree | 1 exact match | ≤5s | <100ms | decree_number match |
| research_dubai_municipality | 1 | ≤10s | <100ms | category parameter |
| research_court_decision | 1 | ≤15s | <100ms | query parameter |
| research_labor_dispute_decision | 10 | ≤15s | <100ms | dispute_type match |
| research_commercial_contract_precedent | 5 | ≤15s | <100ms | contract_type match |
| research_difc_law | 1 | ≤10s | <100ms | query parameter |
| research_difc_company | 1 | ≤5s | <100ms | company_name/id |
| research_adgm_law | 1 | ≤10s | <100ms | query parameter |
| research_adgm_registry | 1 | ≤5s | <100ms | company_name/id |
| research_commercial_law | 5 | ≤10s | <100ms | query parameter |
| research_commercial_contract | 3 + model clauses | ≤15s | <100ms | contract_type |
| research_uae_trademark_law | 1 | ≤10s | <100ms | query parameter |
| research_uae_labor_law | 5 | ≤10s | <100ms | query parameter |
| research_labor_dispute_resolution | 1 procedure | ≤10s | <100ms | dispute_type |
| research_uae_criminal_law | 5 | ≤10s | <100ms | query parameter |
| research_criminal_case_decision | 5 | ≤15s | <100ms | crime_type match |
| research_personal_status_law | 5 + Sharia | ≤10s | <100ms | subject parameter |
| research_legal_nlp_classify | 1 classification | ≤2s | N/A | text parameter |
| research_legal_entity_extract | 1+ entities | ≤2s | N/A | text parameter |
| research_aml_compliance | 1 checklist | ≤10s | <100ms | subject parameter |
| research_jurisdiction_compare | Comparison table | ≤15s | <100ms | jurisdictions param |

---

## 15. NEXT STEPS FOR IMPLEMENTERS

1. **Review Against Kimi/DeepSeek Designs**:
   - Compare tool signatures (are they aligned?)
   - Check data sources (any missing or different APIs?)
   - Validate implementation phases (are timeline expectations reasonable?)
   - Flag architectural conflicts for resolution

2. **Finalize Configuration**:
   - Confirm API endpoints for moj.gov.ae, dlp.dubai.gov.ae, court databases
   - Obtain OAuth tokens + test API access
   - Decide on OFAC/UN sanction list provider (real-time vs. cached)

3. **Begin Phase 1 Implementation**:
   - Use this spec as implementation blueprint
   - Kimi: Can implement package structure + param validation + base infrastructure
   - DeepSeek: Can implement data source clients (high parallelization)
   - Claude (code review): Audit phase 1 against this spec before moving to phase 2

4. **Documentation**:
   - Create example Jupyter notebooks (search → analyze → export)
   - Write troubleshooting guide (common API issues)
   - Record demo video (basic usage workflow)

