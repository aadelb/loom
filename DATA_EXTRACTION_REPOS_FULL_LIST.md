# Complete List: Data Extraction & Document Processing Repos for Loom

**Research Date:** 2026-05-01  
**Total Repos Identified:** 30  
**Currently Integrated:** 6  
**Integration Gaps:** 24  

---

## 1. DOCUMENT PROCESSING & EXTRACTION

| Repo | Stars | Status | Description | URL |
|------|-------|--------|-------------|-----|
| **unstructured** | 8.9k | 🔴 NOT IN LOOM | Multi-format document API (PDF, DOCX, images) | https://github.com/Unstructured-IO/unstructured |
| **layoutparser** | 4.2k | 🔴 NOT IN LOOM | Document layout detection (headers, tables, regions) | https://github.com/Layout-Parser/layout-parser |
| **pdfminer** | 5.6k | ✓ IN LOOM | PDF text extraction (used by pdf_extract tool) | https://github.com/euske/pdfminer |
| **pdf2image** | 1.9k | 🔴 NOT IN LOOM | PDF to image conversion (Poppler) | https://github.com/Belval/pdf2image |
| **pandoc** | N/A | ✓ IN LOOM | Document format conversion (used by document tool) | https://github.com/jgm/pandoc |
| **document.py** | N/A | ✓ IN LOOM | Loom wrapper for Pandoc | (internal) |

---

## 2. TABLE EXTRACTION

| Repo | Stars | Status | Description | URL |
|------|-------|--------|-------------|-----|
| **camelot** | 4.8k | 🔴 NOT IN LOOM | PDF table extraction (stream/lattice modes) | https://github.com/camelot-dev/camelot |
| **tabula-py** | 2.6k | 🔴 NOT IN LOOM | PDF table extraction (Java-based) | https://github.com/chezou/tabula-py |

---

## 3. OCR & TEXT EXTRACTION

| Repo | Stars | Status | Description | URL |
|------|-------|--------|-------------|-----|
| **whisper** | 76k | ✓ IN LOOM | Audio/video transcription (99 languages) | https://github.com/openai/whisper |
| **EasyOCR** | 23k | ✓ IN LOOM (via ai_safety_extended) | Optical character recognition (80+ languages) | https://github.com/JaidedAI/EasyOCR |
| **PaddleOCR** | 41k | 🔴 NOT IN LOOM | Lightweight OCR by Baidu (40+ languages, edge-optimized) | https://github.com/PaddlePaddle/PaddleOCR |
| **pytesseract** | 5.7k | 🔴 NOT IN LOOM | Tesseract OCR wrapper | https://github.com/madmaze/pytesseract |

---

## 4. METADATA EXTRACTION

| Repo | Stars | Status | Description | URL |
|------|-------|--------|-------------|-----|
| **metadata_forensics.py** | N/A | ✓ IN LOOM | Web metadata extraction (OpenGraph, JSON-LD, Twitter Cards) | (internal) |
| **exifread** | 2.7k | 🔴 NOT IN LOOM | EXIF metadata reader (GPS, timestamps, camera) | https://github.com/ianare/exifread |
| **piexif** | 1.2k | 🔴 NOT IN LOOM | EXIF metadata parser/writer | https://github.com/hMatoba/piexif |

---

## 5. MEDIA EXTRACTION

| Repo | Stars | Status | Description | URL |
|------|-------|--------|-------------|-----|
| **yt-dlp** | 92k | ✓ IN LOOM | Video/audio download, metadata, subtitles | https://github.com/yt-dlp/yt-dlp |
| **subtitle-download** | 7.4k | 🔴 NOT IN LOOM | Video subtitle extraction (1000+ providers) | https://github.com/gyroflow/gyroflow |

---

## 6. EMAIL & MESSAGE PARSING

| Repo | Stars | Status | Description | URL |
|------|-------|--------|-------------|-----|
| **mail-parser** | 210 | 🔴 NOT IN LOOM | Email parsing (MIME, headers, attachments) | https://github.com/SpamScope/mail-parser |
| **email-parser** | 450 | 🔴 NOT IN LOOM | Email header extraction | https://github.com/joediamonds/email-parser |

---

## 7. DATA VALIDATION & PROFILING

| Repo | Stars | Status | Description | URL |
|------|-------|--------|-------------|-----|
| **pydantic** | 21k | ✓ IN LOOM | Data validation (used by all Loom param models) | https://github.com/pydantic/pydantic |
| **great-expectations** | 9.8k | 🔴 NOT IN LOOM | Data profiling & quality validation | https://github.com/great-expectations/great_expectations |
| **pandas-profiling** | 12.4k | 🔴 NOT IN LOOM | Auto-generate data profiles (alternative to great-expectations) | https://github.com/ydataai/pandas-profiling |

---

## 8. LLM-POWERED EXTRACTION

| Repo | Stars | Status | Description | URL |
|------|-------|--------|-------------|-----|
| **instructor** | 8.5k | 🔴 NOT IN LOOM | Structured LLM outputs with Pydantic validation | https://github.com/jxnl/instructor |
| **guardrails-ai** | 4.1k | 🔴 NOT IN LOOM | LLM output validation & safety gates | https://github.com/guardrails-ai/guardrails |

---

## 9. SECURITY & CODE ANALYSIS

| Repo | Stars | Status | Description | URL |
|------|-------|--------|-------------|-----|
| **gitleaks** | 17.5k | 🔴 NOT IN LOOM | Secret scanning in git history | https://github.com/gitleaks/gitleaks |
| **truffleHog** | 15.8k | 🔴 NOT IN LOOM | Secrets detection with verification | https://github.com/trufflesecurity/truffleHog |
| **detect-secrets** | 3.8k | 🔴 NOT IN LOOM | Pre-commit secret detection (lightweight) | https://github.com/Yelp/detect-secrets |
| **semgrep** | 13k | 🔴 NOT IN LOOM | SAST for code patterns & security (20+ languages) | https://github.com/returntocorp/semgrep |
| **bandit** | 4.2k | 🔴 NOT IN LOOM | Python security scanner | https://github.com/PyCQA/bandit |

---

## 10. SPECIALIZED PARSING

| Repo | Stars | Status | Description | URL |
|------|-------|--------|-------------|-----|
| **resume-parser** | 1.1k | 🔴 NOT IN LOOM | Resume/CV extraction (skills, experience, education) | https://github.com/OmkarPathak/resume-parser |
| **docparser** | 180 | 🔴 NOT IN LOOM | Document parsing (invoices, resumes, forms) | https://github.com/docparser/docparser-python |

---

## 11. BROWSER AUTOMATION (For Dynamic Extraction)

| Repo | Stars | Status | Description | URL |
|------|-------|--------|-------------|-----|
| **playwright** | 65k | ✓ IN LOOM | Cross-browser automation (used by Camoufox tool) | https://github.com/microsoft/playwright |
| **selenium** | 30k | 🔴 NOT IN LOOM | Web browser automation (alternative to Playwright) | https://github.com/SeleniumHQ/selenium |

---

## Integration Status Summary

### Already in Loom (6 tools)
1. Whisper (transcribe)
2. EasyOCR (via ai_safety_extended)
3. Pydantic (core dependency)
4. yt-dlp (ytdlp_backend)
5. Playwright (stealth/camoufox)
6. Pandoc (document converter)

### High Priority Gaps (5 tools) — Phase 1
1. **unstructured** — Unified document API
2. **layoutparser** — Document layout detection
3. **gitleaks** — Git secret scanning
4. **instructor** — Structured LLM extraction
5. **great-expectations** — Data profiling

### Medium Priority Gaps (5 tools) — Phase 2
6. **camelot** — PDF tables
7. **PaddleOCR** — Fast OCR
8. **semgrep** — Code security
9. **exifread** — Image metadata
10. **resume-parser** — Resume extraction

### Lower Priority Gaps (14 tools) — Phase 3
11. guardrails-ai
12. pandas-profiling
13. pytesseract
14. truffleHog
15. detect-secrets
16. bandit
17. mail-parser
18. email-parser
19. docparser
20. tabula-py
21. piexif
22. pdf2image
23. selenium
24. subtitle-download

---

## Key Recommendations

### Must Integrate (Q2 2026)
- **unstructured** → Enterprise document processing
- **gitleaks** → Compliance (EU AI Act Article 15)
- **instructor** → Reliable structured extraction
- **great-expectations** → Data quality gates

### Should Integrate (Q3 2026)
- **layoutparser** → Advanced document understanding
- **camelot** → Specialized PDF tables
- **PaddleOCR** → Lightweight alternative to EasyOCR
- **semgrep** → Code artifact analysis

### Nice to Have (Q4 2026+)
- Email parsing tools (mail-parser, email-parser)
- OCR alternatives (pytesseract, detect-secrets)
- Resume parser for HR workflows
- Data profiling alternatives (pandas-profiling)

---

## Dependencies

### System-Level (Non-Python)
- **Poppler** (for pdf2image) — Usually pre-installed on Linux/Mac
- **Tesseract** (optional, for pytesseract)
- **Java** (for tabula-py)
- **gitleaks binary** (standalone Go binary, not pip)
- **semgrep binary** (standalone Go binary, not pip)

### Python Packages
```
# Phase 1 Critical
pip install unstructured layoutparser instructor great-expectations

# Phase 2 Important
pip install camelot-py paddleocr semgrep exifread resume-parser

# Phase 3 Optional
pip install guardrails-ai pandas-profiling pytesseract truffleHog detect-secrets bandit mail-parser
```

---

## Cost Estimation

| Phase | Tools | Est. Hours | Risk | Impact |
|-------|-------|-----------|------|--------|
| Phase 1 | 5 | 25-40 | Low-Medium | 90% gap solved |
| Phase 2 | 5 | 18-26 | Low-Medium | Enterprise ready |
| Phase 3 | 14 | 30-40 | Low | Specialized coverage |
| **TOTAL** | 24 | **73-106** | Low-Medium | World-class pipeline |

---

## File Locations in Loom

| Component | Path |
|-----------|------|
| TODO tracking | `/Users/aadel/projects/loom/TODO_DATA_EXTRACTION_INTEGRATIONS.md` |
| Research report | `/Users/aadel/projects/loom/RESEARCH_DATA_EXTRACTION_GAPS.md` |
| Repos list | `/Users/aadel/projects/loom/DATA_EXTRACTION_REPOS_FULL_LIST.md` (this file) |
| Tools directory | `src/loom/tools/` |
| Params models | `src/loom/params.py` |
| Tool registration | `src/loom/server.py:_register_tools()` |
| Tests | `tests/test_tools/` |
| Documentation | `docs/tools-reference.md`, `docs/help.md` |

---

## Next Steps

1. **Review** this list with team
2. **Prioritize** Phase 1 integrations (unstructured, layoutparser, gitleaks, instructor, great-expectations)
3. **Create** INTEGRATE-026 through INTEGRATE-035 tasks in issue tracker
4. **Assign** to implementation sprints (Q2 2026)
5. **Monitor** dependency updates (especially PyTorch/vision models)
