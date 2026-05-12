# Loom-Legal: Design Comparison Framework

**Purpose**: Template for comparing Kimi + DeepSeek designs against the unified spec once they become accessible.

---

## COMPARISON MATRIX

### 1. PLUGIN ARCHITECTURE

| Aspect | Unified Spec | Kimi Design | DeepSeek Design | ✓ Aligned |
|--------|------|------|------|---|
| **Package Type** | Standalone plugin via entry_points | ? | ? | ? |
| **Entry Point Group** | `loom.tools` | ? | ? | ? |
| **Tool Registration** | `_register_legal_tools(mcp)` function | ? | ? | ? |
| **Package Dependencies** | loom-research >= 0.1.0 | ? | ? | ? |
| **Installation** | `pip install loom-legal` | ? | ? | ? |
| **Source Repo** | New: https://github.com/aadel/loom-legal | ? | ? | ? |

### 2. PACKAGE STRUCTURE

| Path | Unified Spec | Kimi | DeepSeek | Notes |
|------|---|---|---|---|
| `src/loom_legal/__init__.py` | ✓ | ? | ? | Version + exports |
| `src/loom_legal/server.py` | ✓ | ? | ? | Entry point function |
| `src/loom_legal/params.py` | ✓ | ? | ? | All 26 parameter models |
| `src/loom_legal/validators.py` | ✓ | ? | ? | Query/URL validation |
| `src/loom_legal/cache.py` | ✓ | ? | ? | SHA-256 cache + TTL |
| `src/loom_legal/sources/` | ✓ (8 modules) | ? | ? | Data source clients |
| `src/loom_legal/tools/` | ✓ (15+ modules) | ? | ? | 26 tool implementations |
| `src/loom_legal/nlp/` | ✓ (4 modules) | ? | ? | AraLegal-BERT + NER |
| `src/loom_legal/utils/` | ✓ (4 modules) | ? | ? | Arabic, PDF, date parsing |
| `tests/` | ✓ (9 subdirs) | ? | ? | Unit + integration + E2E |
| `docs/` | ✓ (7 docs) | ? | ? | Tools reference, troubleshooting |

### 3. TOOL COUNT & NAMING

| Category | Unified Spec | Kimi | DeepSeek | Note |
|----------|---|---|---|---|
| **Total Tools** | 26 | ? | ? | **KEY METRIC**: Must match or justify delta |
| **Legislation** | 4 | ? | ? | research_uae_legislation, research_federal_law, etc. |
| **Dubai Laws** | 3 | ? | ? | research_dubai_law, research_dubai_decree, etc. |
| **Court/Cases** | 3 | ? | ? | research_court_decision, research_labor_dispute_decision, etc. |
| **DIFC/ADGM** | 4 | ? | ? | research_difc_law, research_difc_company, etc. |
| **Commercial** | 3 | ? | ? | research_commercial_law, research_commercial_contract, etc. |
| **Labor** | 2 | ? | ? | research_uae_labor_law, research_labor_dispute_resolution |
| **Criminal** | 2 | ? | ? | research_uae_criminal_law, research_criminal_case_decision |
| **Family/Personal** | 1 | ? | ? | research_personal_status_law |
| **NLP & Compliance** | 4 | ? | ? | research_legal_nlp_classify, research_legal_entity_extract, etc. |

### 4. DATA SOURCES

| Source | URL | Unified Spec | Kimi | DeepSeek | Notes |
|--------|-----|---|---|---|---|
| UAE Legislation Portal | uaelegislation.gov.ae | ✓ | ? | ? | Primary federal laws |
| MOJ Database | moj.gov.ae | ✓ | ? | ? | Requires OAuth2 token |
| Dubai Legal Portal | dlp.dubai.gov.ae | ✓ | ? | ? | Emirate-level laws |
| Federal Court | courts.gov.ae | ✓ | ? | ? | Case law database |
| DIFC Laws | difc.com | ✓ | ? | ? | DIFC jurisdiction |
| DIFC Registry | difc.com/register | ✓ | ? | ? | Company registry API |
| ADGM Laws | adgm.com | ✓ | ? | ? | ADGM jurisdiction |
| ADGM Registry | adgm.com/registry | ✓ | ? | ? | Company registry + FSRA |
| Bayanat Open Data | bayanat.ae | ✓ | ? | ? | Open government data |
| Dubai Municipality | dmca.gov.ae | ✓ | ? | ? | Municipal regulations |
| AraLegal-BERT | HuggingFace model | ✓ | ? | ? | Local NLP model |

**ACTION**: If Kimi/DeepSeek use different sources, justify why and document API endpoints.

### 5. CACHING STRATEGY

| Aspect | Unified Spec | Kimi | DeepSeek | Decision |
|--------|---|---|---|---|
| **Cache Location** | `~/.cache/loom/legal/YYYY-MM-DD/` | ? | ? | Daily dirs, SHA-256 keys |
| **TTL: Federal Laws** | 7 days | ? | ? | Laws change slowly |
| **TTL: Court Decisions** | 30 days | ? | ? | Historical, final |
| **TTL: Company Registry** | 1 day | ? | ? | Status changes daily |
| **TTL: NLP Models** | No cache (deterministic) | ? | ? | Model inference repeatable |
| **L1 Cache (Source)** | Raw API response | ? | ? | Hybrid strategy |
| **L2 Cache (Tool)** | Processed results | ? | ? | Variable per tool |
| **Cache Key Format** | SHA-256(source + query + params) | ? | ? | Deterministic |
| **Eviction Policy** | Daily cron, older than TTL | ? | ? | Automatic + manual |

**ACTION**: If different TTL policy, justify based on data freshness requirements.

### 6. PARAMETER MODELS (Sample)

| Tool | Parameters | Unified Spec | Kimi | DeepSeek | Validation |
|------|---|---|---|---|---|
| **research_uae_legislation** | query, language, limit, law_number, year, status | ✓ Pydantic v2 | ? | ? | Strict mode, forbid extra |
| **research_federal_law** | category, search_term, language | ✓ | ? | ? | |
| **research_court_decision** | query, case_number, court, year, language, limit | ✓ | ? | ? | |
| **research_legal_nlp_classify** | text, category_type, language | ✓ | ? | ? | |

**ACTION**: Compare parameter names, types, and default values. Flag naming inconsistencies.

### 7. ERROR HANDLING

| Error Type | Unified Spec | Kimi | DeepSeek | Handling |
|-----------|---|---|---|---|
| **API Unavailable** | LegalSourceUnavailable | ? | ? | Cache fallback |
| **Auth Failure** | LegalAuthenticationError | ? | ? | Token refresh |
| **Rate Limit** | LegalRateLimitError | ? | ? | Exponential backoff |
| **Encoding Issue** | LegalEncodingError | ? | ? | UTF-8 repair |
| **Validation Fail** | LegalValidationError | ? | ? | Input rejection |

**ACTION**: Ensure exception names + handling match. Add missing error types if needed.

### 8. ARABIC LANGUAGE SUPPORT

| Feature | Unified Spec | Kimi | DeepSeek | Implementation |
|---------|---|---|---|---|
| **UTF-8 Support** | ✓ Full | ? | ? | No escaping, native Unicode |
| **Language Detection** | ✓ Auto-detect en/ar/mixed | ? | ? | langdetect library |
| **Transliteration Fallback** | ✓ DIN 31635 | ? | ? | pyarabic + custom |
| **Islamic Date Conversion** | ✓ Hijri↔Gregorian | ? | ? | hijri_converter library |
| **NLP: AraLegal-BERT** | ✓ Fine-tuned model | ? | ? | sentence-transformers |
| **All Tools Bilingual** | ✓ title_en + title_ar | ? | ? | Every result dual-language |

**ACTION**: Confirm Arabic support scope. Are all tools bilingual or only some?

### 9. IMPLEMENTATION PHASES & TIMELINE

| Phase | Unified Spec | Kimi | DeepSeek | Duration |
|-------|---|---|---|---|
| **Phase 1: Infrastructure** | Weeks 1-2 | ? | ? | Package, params, cache, validators |
| **Phase 2: Data Sources & Tools** | Weeks 3-5 | ? | ? | 8 sources, 20 tools, integration tests |
| **Phase 3: Advanced Features** | Weeks 6-8 | ? | ? | NLP, jurisdiction compare, docs |
| **Total Duration** | 8 weeks | ? | ? | **KEY METRIC**: Feasibility check |

**ACTION**: If timeline differs, document resource availability + parallel work breakdown.

### 10. DEPENDENCIES

| Package | Unified Spec | Kimi | DeepSeek | Version |
|---------|---|---|---|---|
| loom-research | >=0.1.0 | ? | ? | Core dependency |
| httpx | >=0.25.0 | ? | ? | Async HTTP |
| pydantic | >=2.0 | ? | ? | Validation |
| beautifulsoup4 | >=4.12 | ? | ? | HTML parsing |
| pypdf | >=4.0 | ? | ? | PDF extraction |
| pyarabic | >=0.6.15 | ? | ? | Arabic utilities |
| torch | Optional | ? | ? | For NLP (install separately) |
| sentence-transformers | Optional | ? | ? | For embeddings |

**ACTION**: If additional dependencies needed, justify + assess impact on install size.

### 11. TEST COVERAGE

| Test Type | Unified Spec | Kimi | DeepSeek | Target |
|-----------|---|---|---|---|
| **Unit Tests** | 40% | ? | ? | Params, cache, errors, utils |
| **Integration Tests** | 40% | ? | ? | Each tool, source clients, cache TTL |
| **E2E Tests** | 20% | ? | ? | Journey tests (realistic workflows) |
| **Live Tests** | Marked `@pytest.mark.live` | ? | ? | Run on Hetzner, require API keys |
| **Overall Coverage Target** | 80%+ | ? | ? | **GATE**: No merge without this |

**ACTION**: Ensure test structure matches. Flag coverage gaps.

### 12. SECURITY

| Aspect | Unified Spec | Kimi | DeepSeek | Implementation |
|--------|---|---|---|---|
| **API Key Storage** | Env vars only | ? | ? | No hardcoding |
| **PII Masking** | Default ON | ? | ? | NER-based + audit logging |
| **Rate Limiting** | Per-source limits | ? | ? | Backoff on 429 |
| **SSRF Prevention** | URL validation | ? | ? | loom.validators.validate_url |
| **SQL Injection** | Query sanitization | ? | ? | No SQL used, params validated |
| **Startup Validation** | Check all API keys | ? | ? | research_validate_startup() |

**ACTION**: Review security checklist. Add any missing controls.

### 13. DOCUMENTATION

| Doc | Unified Spec | Kimi | DeepSeek | Contents |
|-----|---|---|---|---|
| **TOOLS_REFERENCE.md** | ✓ | ? | ? | Parameters, examples, costs |
| **ARCHITECTURE.md** | ✓ | ? | ? | Design, patterns, data flow |
| **ARABIC_LANGUAGE.md** | ✓ | ? | ? | UTF-8, transliteration, NLP |
| **API_KEYS_SETUP.md** | ✓ | ? | ? | How to configure credentials |
| **TROUBLESHOOTING.md** | ✓ | ? | ? | Common issues, solutions |
| **SECURITY.md** | ✓ | ? | ? | PII handling, rate limits, key mgmt |
| **CACHING_STRATEGY.md** | ✓ | ? | ? | Cache behavior, TTL policy |

**ACTION**: Ensure docs exist + are complete. Flag missing documentation.

---

## RESOLUTION CHECKLIST

Once Kimi/DeepSeek designs are available, work through this checklist:

### High-Priority Conflicts
- [ ] **Tool Count**: Do both designs propose same 26 tools? If not, reconcile list.
- [ ] **Data Sources**: Are the same government APIs targeted? If different, validate availability.
- [ ] **Timeline**: Is 8-week estimate realistic? Adjust if necessary.
- [ ] **Package Structure**: Do both use entry_points for plugin discovery? If not, align on mechanism.

### Medium-Priority Differences
- [ ] **Parameter Names**: Are parameter names consistent across designs? (e.g., `law_number` vs. `law_id`)
- [ ] **Caching Strategy**: Do both use hybrid L1+L2? Or different approach?
- [ ] **Arabic Support**: Are all tools bilingual or subset? Align scope.
- [ ] **Error Handling**: Do exception names match? Add any missing types.

### Low-Priority Considerations
- [ ] **Documentation Structure**: Which doc organization is clearer? Adopt best approach.
- [ ] **NLP Model**: AraLegal-BERT vs. alternative? Benchmark if different.
- [ ] **Testing Framework**: pytest structure aligned? Use same fixtures + markers.
- [ ] **Code Style**: Black + ruff + mypy? Confirm configuration.

### Sign-Off Criteria
After reconciliation:
- [ ] Single master spec document (live source of truth)
- [ ] Kimi + DeepSeek + Claude all reference same spec
- [ ] No ambiguity in tool signatures or data flows
- [ ] Implementation can begin without further design meetings
- [ ] All questions marked with "?" above have been answered

---

## NOTES FOR REVIEWERS

### When Comparing Designs

**PASS if:**
- Tool count matches (26 tools)
- Data sources well-documented + validated
- Caching strategy sound (either approach acceptable if justified)
- Parameter validation via Pydantic v2 (strict mode)
- Error handling comprehensive
- Arabic support full (bilingual results)
- Timeline realistic + dependencies clear
- 80%+ test coverage target maintained

**FLAG as RISK if:**
- Tool count differs significantly (>3 tools delta)
- Uses unvalidated/unavailable data sources (esp. government APIs)
- Caching bypass (no TTL enforcement)
- Weak error handling (silent failures, no fallback)
- Partial Arabic support (only some tools bilingual)
- Unrealistic timeline (<4 weeks for phase 1-2) without resource scaling
- Test coverage target <70%

**ESCALATE if:**
- Fundamental architecture conflict (e.g., "monolith tool" vs. "plugin")
- Legal/compliance concern (PII handling, jurisdiction precedence)
- Security gap (hardcoded API keys, SSRF vulnerability)
- Unresolvable data access issue (API requires special permission, not available)

---

## NEXT STEPS (Timeline)

1. **Today**: Provide this comparison framework to Kimi + DeepSeek
2. **Tomorrow**: Kimi produces design document, DeepSeek produces design document
3. **Day 3**: Ahmed reviews both designs, populates comparison matrix
4. **Day 4**: Reconciliation meeting (if conflicts detected)
5. **Day 5**: Sign-off on final unified spec
6. **Week 2**: Phase 1 implementation begins (Kimi + DeepSeek parallel)
7. **Week 5**: Phase 2 merge + integration testing
8. **Week 8**: Phase 3 completion + release

