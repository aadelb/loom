# TODO: Data Extraction & Document Processing Integrations

Based on RESEARCH_DATA_EXTRACTION_GAPS.md, these are the 24 actionable integration tasks.

## Phase 1: Core Extraction (HIGH PRIORITY)

- [ ] INTEGRATE-026: Unstructured — Multi-format document API
  - Tool: `research_extract_document(url, format, element_type)`
  - File: `src/loom/tools/document_extract_unified.py`
  - Test: `tests/test_tools/test_document_extract_unified.py`
  - Params: `params.DocumentExtractParams` with (url, output_format, element_types, chunk_size)
  - Deps: `pip install unstructured pillow pdf2image`
  - GitHub: https://github.com/Unstructured-IO/unstructured
  - Est: 8-12 hours

- [ ] INTEGRATE-027: LayoutParser — Document structure detection
  - Tool: `research_detect_layout(url, element_types)`
  - File: `src/loom/tools/layout_analysis.py`
  - Test: `tests/test_tools/test_layout_analysis.py`
  - Params: `params.LayoutAnalysisParams` with (url, element_types, confidence_threshold)
  - Deps: `pip install layoutparser torch pdf2image`
  - GitHub: https://github.com/Layout-Parser/layout-parser
  - Est: 6-8 hours

- [ ] INTEGRATE-028: Gitleaks — Git history secret scanning
  - Tool: `research_scan_git_secrets(repo_url, scan_type, output_format)`
  - File: `src/loom/tools/git_secrets.py`
  - Test: `tests/test_tools/test_git_secrets.py`
  - Params: `params.GitSecretsParams` with (repo_url, scan_type, max_depth, format)
  - Deps: `gitleaks` (Go binary), subprocess wrapper only
  - GitHub: https://github.com/gitleaks/gitleaks
  - Est: 3-4 hours

- [ ] INTEGRATE-029: Instructor — Structured LLM outputs with validation
  - Tool: Enhance `research_llm_extract()` with `instructor` validation
  - File: Modify `src/loom/tools/llm.py`
  - Test: `tests/test_tools/test_llm_structured.py`
  - Params: Extend existing `research_llm_extract` with (schema, model, temperature)
  - Deps: `pip install instructor`
  - GitHub: https://github.com/jxnl/instructor
  - Est: 4-6 hours

- [ ] INTEGRATE-030: Great-Expectations — Data quality validation
  - Tool: `research_profile_data(data_url, data_format, assert_schema)`
  - File: `src/loom/tools/data_profiler.py`
  - Test: `tests/test_tools/test_data_profiler.py`
  - Params: `params.DataProfilerParams` with (csv_url, json_data, json_schema, expect_rules)
  - Deps: `pip install great-expectations pandas`
  - GitHub: https://github.com/great-expectations/great_expectations
  - Est: 6-8 hours

## Phase 2: Layout & Validation (MEDIUM PRIORITY)

- [ ] INTEGRATE-031: Camelot — PDF table extraction
  - Tool: `research_extract_pdf_tables(url, table_mode)`
  - File: `src/loom/tools/pdf_tables.py`
  - Test: `tests/test_tools/test_pdf_tables.py`
  - Params: `params.PDFTablesParams` with (url, mode='stream'|'lattice', output_format)
  - Deps: `pip install camelot-py pandas`
  - GitHub: https://github.com/camelot-dev/camelot
  - Est: 4-6 hours

- [ ] INTEGRATE-032: PaddleOCR — Lightweight OCR (faster alternative to EasyOCR)
  - Tool: Add `research_ocr_paddle()` as alternative to transcribe
  - File: `src/loom/tools/ocr_paddle.py`
  - Test: `tests/test_tools/test_ocr_paddle.py`
  - Params: `params.PaddleOCRParams` with (image_url, languages, model_size)
  - Deps: `pip install paddleocr`
  - GitHub: https://github.com/PaddlePaddle/PaddleOCR
  - Est: 3-5 hours

- [ ] INTEGRATE-033: Semgrep — SAST code security analysis
  - Tool: `research_analyze_code_security(repo_url, rules, format)`
  - File: `src/loom/tools/code_security.py`
  - Test: `tests/test_tools/test_code_security.py`
  - Params: `params.CodeSecurityParams` with (repo_url, rules, ignore_patterns)
  - Deps: `semgrep` (CLI), subprocess wrapper
  - GitHub: https://github.com/returntocorp/semgrep
  - Est: 4-5 hours

- [ ] INTEGRATE-034: Exifread — Image EXIF metadata extraction
  - Tool: Enhance `research_metadata_forensics()` with EXIF parsing
  - File: Modify `src/loom/tools/metadata_forensics.py`
  - Test: `tests/test_tools/test_metadata_forensics_exif.py`
  - Params: Extend existing metadata tool with image_urls list
  - Deps: `pip install exifread`
  - GitHub: https://github.com/ianare/exifread
  - Est: 2-3 hours

- [ ] INTEGRATE-035: Resume Parser — HR document extraction
  - Tool: `research_parse_resume(resume_url, output_schema)`
  - File: `src/loom/tools/resume_parser.py`
  - Test: `tests/test_tools/test_resume_parser.py`
  - Params: `params.ResumeParserParams` with (url, format, extract_fields)
  - Deps: `pip install resume-parser spacy`
  - GitHub: https://github.com/OmkarPathak/resume-parser
  - Est: 5-7 hours

## Phase 3: Specialized & Lower Priority

- [ ] INTEGRATE-036: Guardrails-AI — LLM output safety gates
  - Tool: `research_apply_guardrails(llm_output, policy)`
  - File: `src/loom/tools/llm_guardrails.py`
  - Test: `tests/test_tools/test_llm_guardrails.py`
  - Deps: `pip install guardrails-ai`
  - GitHub: https://github.com/guardrails-ai/guardrails
  - Est: 4-6 hours

- [ ] INTEGRATE-037: Pandas-Profiling — Alternative data profiler
  - Tool: Optional alternative to great-expectations
  - File: `src/loom/tools/data_profiler_pandas.py`
  - Deps: `pip install pandas-profiling ydata-profiling`
  - GitHub: https://github.com/ydataai/pandas-profiling
  - Est: 2-3 hours

- [ ] INTEGRATE-038: TruffleHog — Alternative secret scanning
  - Tool: `research_scan_secrets_truffleHog()` as gitleaks alternative
  - File: `src/loom/tools/secrets_truffleHog.py`
  - Deps: `pip install truffleHog` or CLI
  - GitHub: https://github.com/trufflesecurity/truffleHog
  - Est: 3-4 hours

- [ ] INTEGRATE-039: Bandit — Python security scanning
  - Tool: `research_scan_python_security(repo_url)`
  - File: `src/loom/tools/bandit_scanner.py`
  - Deps: `pip install bandit`
  - GitHub: https://github.com/PyCQA/bandit
  - Est: 3-4 hours

- [ ] INTEGRATE-040: Pytesseract — Tesseract OCR wrapper
  - Tool: Optional OCR alternative (lower priority than PaddleOCR)
  - File: `src/loom/tools/ocr_tesseract.py`
  - Deps: `pip install pytesseract` + system Tesseract
  - GitHub: https://github.com/madmaze/pytesseract
  - Est: 2-3 hours

- [ ] INTEGRATE-041: Mail-Parser — Email message parsing
  - Tool: `research_parse_email(email_raw, extract_fields)`
  - File: `src/loom/tools/email_parser_mime.py`
  - Deps: `pip install mail-parser`
  - GitHub: https://github.com/SpamScope/mail-parser
  - Est: 3-4 hours

- [ ] INTEGRATE-042: TabuLA-PY — PDF table extraction (Java-based alternative)
  - Tool: Optional alternative to Camelot
  - File: `src/loom/tools/pdf_tables_tabula.py`
  - Deps: `pip install tabula-py` + Java
  - GitHub: https://github.com/chezou/tabula-py
  - Est: 2-3 hours

- [ ] INTEGRATE-043: PDF2Image — PDF to image conversion utility
  - Tool: Internal utility for OCR pipelines
  - File: `src/loom/tools/pdf_to_images.py`
  - Deps: `pip install pdf2image` + Poppler
  - GitHub: https://github.com/Belval/pdf2image
  - Est: 2 hours

- [ ] INTEGRATE-044: Piexif — EXIF metadata write (complementary to read)
  - Tool: Enhance metadata tools with EXIF writing
  - File: Modify `src/loom/tools/metadata_forensics.py`
  - Deps: `pip install piexif`
  - GitHub: https://github.com/hMatoba/piexif
  - Est: 2-3 hours

- [ ] INTEGRATE-045: Detect-Secrets — Pre-commit secret detection
  - Tool: Lightweight alternative to gitleaks
  - File: `src/loom/tools/secrets_detect.py`
  - Deps: `pip install detect-secrets`
  - GitHub: https://github.com/Yelp/detect-secrets
  - Est: 2-3 hours

- [ ] INTEGRATE-046: Subtitle-Download — Video subtitle extraction
  - Tool: Enhancement to existing yt-dlp integration
  - File: Modify `src/loom/tools/ytdlp_backend.py`
  - Deps: Already covered by yt-dlp
  - GitHub: https://github.com/gyroflow/gyroflow
  - Est: 1-2 hours

- [ ] INTEGRATE-047: Email-Parser — Email header parsing (smaller alternative)
  - Tool: Optional lightweight email parser
  - File: `src/loom/tools/email_parser_lite.py`
  - Deps: `pip install email-parser` (if available)
  - GitHub: https://github.com/joediamonds/email-parser
  - Est: 2-3 hours

- [ ] INTEGRATE-048: Enhance Pydantic Integration
  - Task: Review all extraction tools for Pydantic v2 compliance
  - File: Audit `src/loom/params.py`
  - Check: All tools use `extra="forbid"`, `strict=True`
  - Est: 4-6 hours

- [ ] INTEGRATE-049: Knowledge-Graph Enhancement
  - Task: Verify existing knowledge_graph.py and expand entity linking
  - File: Review/enhance `src/loom/tools/knowledge_graph.py`
  - Check: Entity resolution, RDF output, multi-language support
  - Est: 3-5 hours

---

## Testing & Documentation Requirements

For EACH integration tool:

1. **Unit tests** (80%+ coverage):
   - Test with valid inputs (happy path)
   - Test with edge cases (empty files, corrupted documents, timeouts)
   - Test with invalid inputs (bad URLs, unsupported formats)
   - Mock external services where appropriate

2. **Integration tests**:
   - Test with real documents (via research_fetch)
   - Test with various file formats (PDF, DOCX, HTML, images)
   - Test error handling and fallbacks

3. **Documentation**:
   - Entry in `docs/tools-reference.md` with examples
   - Entry in `docs/help.md` with troubleshooting
   - Inline docstrings following Loom conventions
   - Cost estimation (if applicable)

4. **Pre-commit validation**:
   - Run `ruff check --fix` (linting)
   - Run `ruff format` (formatting)
   - Run `mypy src/loom/tools/<tool>.py` (type checking)
   - Verify no hardcoded secrets or API keys

---

## Success Criteria

Each integration is "done" when:

- [ ] Tool function exists in `src/loom/tools/<name>.py`
- [ ] Params model exists in `src/loom/params.py` with `extra="forbid"`, `strict=True`
- [ ] Tool is registered in `src/loom/server.py:_register_tools()`
- [ ] Tests in `tests/test_tools/` with 80%+ coverage
- [ ] Documentation in `docs/tools-reference.md` + `docs/help.md`
- [ ] All ruff/mypy checks pass locally
- [ ] Journey test scenario added (if applicable)
- [ ] Git commit with `feat(tools): integrate <tool-name>`

---

## Priority Guide

**CRITICAL (Do First):**
- INTEGRATE-026, 027, 028, 029, 030 (Phase 1 — 25-40 hours)

**HIGH (Next Sprint):**
- INTEGRATE-031, 032, 033, 034, 035 (Phase 2 — 18-26 hours)

**MEDIUM (Backlog):**
- INTEGRATE-036 through INTEGRATE-049 (Phase 3 — 30-40 hours)

**Total Effort:** ~95 hours across 24 tools

**Recommended Timeline:** Q2 2026 (2-3 months with part-time work)
