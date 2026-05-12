# Loom Tool Guidelines Generation - Summary Report

**Date:** 2026-05-06  
**Status:** COMPLETE  
**Tools Analyzed:** 835 / 835

---

## Overview

Successfully generated comprehensive output guidelines for all 835 Loom tools. This document serves as the ground truth for testing, validation, and regression detection across the entire tool suite.

---

## Generated Files

### 1. tool_guidelines.json (520 KB)
**Location:** `/Users/aadel/projects/loom/tool_guidelines.json`

Master reference file containing quality metadata for all 835 tools.

**Structure per tool:**
```json
{
  "research_fetch": {
    "module": "fetch",                          // Source file: src/loom/tools/fetch.py
    "category": "research",                     // Domain category
    "required_params": ["url"],                 // Required function parameters
    "optional_params": ["headers", "timeout"],  // Optional parameters
    "is_async": true,                           // True if async function
    "expected_return_type": "dict",             // dict, list, or any
    "min_output_chars": 200,                    // Minimum content length
    "quality_criteria": {
      "must_not_be_empty": true,                // Cannot be null/empty
      "must_be_dict_or_list": true,             // Type constraint
      "min_chars": 200                          // Content length minimum
    },
    "has_docstring": true,                      // All 835 tools have docstrings
    "docstring_preview": "Fetch and parse..."   // First 200 characters
  }
}
```

**Usage:**
```python
import json

with open("tool_guidelines.json") as f:
    guidelines = json.load(f)

# Get guideline for a tool
guideline = guidelines["research_fetch"]
print(f"Min output: {guideline['min_output_chars']} chars")
print(f"Type: {guideline['expected_return_type']}")
```

### 2. TOOL_TESTING_FRAMEWORK.md (4.1 KB)
**Location:** `/Users/aadel/projects/loom/TOOL_TESTING_FRAMEWORK.md`

Comprehensive testing strategy and category-specific expectations.

**Sections:**
- Test plan (5 phases)
- Output quality validation rules
- Category-specific expectations (research, LLM, scoring, infrastructure)
- Example good/bad outputs
- Regression detection workflow
- CI/CD integration approach

### 3. scripts/validate_guidelines.py (2.8 KB)
**Location:** `/Users/aadel/projects/loom/scripts/validate_guidelines.py`

CLI tool to validate individual tools or generate summary reports.

**Usage:**
```bash
# Summary report
python scripts/validate_guidelines.py --guidelines tool_guidelines.json

# Check specific tool
python scripts/validate_guidelines.py --guidelines tool_guidelines.json --tool research_fetch
```

### 4. GUIDELINES_INDEX.json (958 B)
**Location:** `/Users/aadel/projects/loom/GUIDELINES_INDEX.json`

Quick reference index with metrics and file locations.

---

## Key Statistics

### Coverage
- **Total Tools:** 835
- **Tools Analyzed:** 835 (100%)
- **Tools with Docstrings:** 835 (100%)
- **Tools with Guidelines:** 835 (100%)

### Execution Model
- **Async Tools:** 678 (81.2%) - I/O-bound (API calls, network requests)
- **Sync Tools:** 157 (18.8%) - Local computation, config operations

### Return Types
- **Dict:** 677 (81.0%) - Standard structured outputs
- **List:** 12 (1.4%) - Result arrays, collections
- **Any:** 146 (17.5%) - Flexible/polymorphic returns

### Category Distribution

| Category | Count | Min Output | Examples |
|----------|-------|-----------|----------|
| **research** | 810 | 200 chars | fetch, spider, search, markdown, deep |
| **other** | 15 | 50 chars | miscellaneous utilities |
| **infrastructure** | 5 | 50 chars | config, sessions, cache, health |
| **darkweb** | 3 | 50 chars | tor, onion discovery |
| **scoring** | 1 | 50 chars | attack scorer |
| **analysis** | 1 | 100 chars | report generation |

---

## Quality Criteria by Category

### Research Tools (810 tools)
**Expectation:** Most comprehensive outputs with data, metadata, timing

```json
GOOD OUTPUT:
{
  "results": [
    {"title": "...", "url": "...", "score": 0.92},
    {"title": "...", "url": "...", "score": 0.88}
  ],
  "total": 42,
  "query": "original search query",
  "execution_time_ms": 245,
  "source": "exa"
}

BAD OUTPUT:
{
  "error": "Something went wrong"
}
```

**Validation Rules:**
- Must not be empty/null
- Must include results array or data field
- Must have metadata (total, source, timing)
- Must exceed 200 characters

### LLM Tools (Summarize, Translate, Answer, Classify)
**Expectation:** Short but complete AI-generated responses

```json
GOOD OUTPUT:
{
  "text": "The research demonstrates that...",
  "model": "groq-mixtral-8x7b",
  "tokens": 256,
  "input_length": 2847
}

BAD OUTPUT:
{
  "text": "..."  // Truncated or placeholder
}
```

**Validation Rules:**
- Must not be empty
- Must have actual LLM response (not hardcoded)
- Minimum 30 characters (short summaries OK)
- No truncation artifacts ("...", "[incomplete]")

### Scoring Tools (Attack scorer, harm assessor, etc.)
**Expectation:** Structured numeric scores with reasoning

```json
GOOD OUTPUT:
{
  "score": 78,
  "confidence": 0.92,
  "reasoning": "Attack demonstrates clear understanding...",
  "category": "high",
  "components": {
    "harm": 85,
    "stealth": 72,
    "executability": 75
  }
}

BAD OUTPUT:
{
  "score": 78  // Missing confidence, reasoning
}
```

**Validation Rules:**
- Must not be empty
- Must include numeric score (0-100 range)
- Must include confidence (0-1 range)
- Must include reasoning/explanation
- Minimum 50 characters

### Infrastructure Tools (Config, Sessions, Health)
**Expectation:** Status/state information with operational data

```json
GOOD OUTPUT:
{
  "status": "ok",
  "sessions_active": 3,
  "cache_size_mb": 245.7,
  "uptime_seconds": 145800
}

BAD OUTPUT:
{
  "ok": true  // Too minimal
}
```

**Validation Rules:**
- Must include explicit "status" field
- Must not be empty
- Status values: "ok", "error", "warning", "initializing"
- Minimum 50 characters

---

## Testing Phases

### Phase 1: Static Analysis (COMPLETE)
- Generated guidelines for all 835 tools
- Extracted docstrings, parameters, return types
- Categorized by domain
- Defined quality criteria per category

**Deliverables:**
- tool_guidelines.json (835 tools)
- TOOL_TESTING_FRAMEWORK.md
- This summary document

### Phase 2: Unit Test Generation (TO DO)
Generate parametrized pytest tests for each tool:

```python
@pytest.mark.parametrize("tool_name", GUIDELINES.keys())
async def test_tool_output_format(tool_name, guidelines):
    """Validate that each tool returns expected format."""
    tool_fn = get_tool_function(tool_name)
    params = build_test_params(tool_name, guidelines)
    output = await tool_fn(**params)
    validate_tool_output(tool_name, output, guidelines)
```

**Estimated effort:** 2-3 days
**Expected coverage:** 835 unit tests

### Phase 3: Content Validation Tests (TO DO)
Per-category validation:

```python
async def test_research_tool_has_results(tool_name):
    """Research tools must have non-empty results."""
    output = await call_tool(tool_name)
    assert "results" in output
    assert len(output["results"]) > 0
```

**Estimated effort:** 1-2 days
**Expected coverage:** 50+ integration tests

### Phase 4: Regression Detection (TO DO)
Baseline outputs for all tools:

```bash
pytest tests/test_tools/test_guidelines_baseline.py \
  --baseline-generate \
  --output tests/data/tool_outputs_baseline.json
```

**Deliverable:** `tests/data/tool_outputs_baseline.json`
**Update frequency:** Monthly or after major changes

### Phase 5: CI/CD Integration (TO DO)
Add to pre-commit hooks and GitHub Actions:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: validate-tool-outputs
      name: Validate tool output formats
      entry: python scripts/validate_guidelines.py
      language: python
      types: [python]
```

**Expected runtime:** 2-5 minutes per commit

---

## How to Use These Guidelines

### For Tool Testing
```python
from tool_guidelines import load_guidelines

guidelines = load_guidelines("tool_guidelines.json")
guideline = guidelines["research_fetch"]

# Validate output
output = await research_fetch(url="https://example.com")
assert validate_output(output, guideline), "Output validation failed"
```

### For CI/CD Validation
```bash
# Run validation
python scripts/validate_guidelines.py --guidelines tool_guidelines.json

# Check specific tool
python scripts/validate_guidelines.py --guidelines tool_guidelines.json --tool research_fetch
```

### For Documentation
Each tool's guideline includes:
- Required and optional parameters
- Expected return type
- Minimum content length
- Category and quality bar
- Docstring preview

Use this for:
- Generating test stubs
- Writing integration tests
- Creating API documentation
- Detecting regressions

### For Regression Detection
```python
import json

baseline = json.load(open("tool_outputs_baseline.json"))
current = json.load(open("tool_outputs_current.json"))

for tool_name in baseline:
    baseline_len = len(json.dumps(baseline[tool_name]))
    current_len = len(json.dumps(current[tool_name]))
    
    # Flag if output shrunk > 50 chars
    if current_len < baseline_len - 50:
        print(f"REGRESSION: {tool_name}")
```

---

## Maintenance Schedule

| Task | Frequency | Owner | Effort |
|------|-----------|-------|--------|
| Regenerate guidelines | Monthly | CI/CD | Automated |
| Validate all outputs | Per commit | CI/CD | 2-5 min |
| Update quality criteria | Quarterly | Team | 4 hours |
| Audit undocumented tools | Quarterly | Team | 2 hours |
| Add new test categories | As needed | Team | 2-4 hours |
| Review regression reports | Weekly | Team | 1 hour |

---

## Next Steps

1. **Implement Phase 2** (Unit Test Generation)
   - Create parametrized test file
   - Generate test for each of 835 tools
   - Target: 80%+ pass rate

2. **Implement Phase 3** (Content Validation)
   - Create category-specific validators
   - Test research tools have results
   - Test LLM tools have complete text
   - Test scoring tools have reasoning

3. **Implement Phase 4** (Regression Detection)
   - Generate baseline outputs (mocked/cached)
   - Create regression test suite
   - Set up CI/CD reporting

4. **Implement Phase 5** (CI/CD Integration)
   - Add pre-commit hooks
   - Add GitHub Actions workflow
   - Set up artifact uploads for failures

5. **Documentation**
   - Update tools-reference.md with guidelines
   - Create troubleshooting guide
   - Document expected outputs for each tool

---

## Success Criteria

- [x] All 835 tools have guidelines defined
- [x] 100% of tools have docstrings
- [ ] All tools validated for output format (target: 830+/835)
- [ ] Regression detection in place
- [ ] Less than 5% false positives on validation

---

## Files Location

**Local (Mac):**
- `/Users/aadel/projects/loom/tool_guidelines.json`
- `/Users/aadel/projects/loom/TOOL_TESTING_FRAMEWORK.md`
- `/Users/aadel/projects/loom/GUIDELINES_INDEX.json`
- `/Users/aadel/projects/loom/scripts/validate_guidelines.py`

**Remote (Hetzner):**
- `/opt/research-toolbox/tool_guidelines.json`
- `/opt/research-toolbox/TOOL_TESTING_FRAMEWORK.md`
- `/opt/research-toolbox/GUIDELINES_INDEX.json`
- `/opt/research-toolbox/scripts/validate_guidelines.py`

---

## Support & Questions

To understand a specific tool's guidelines:

1. Open `tool_guidelines.json`
2. Find the tool name (e.g., "research_fetch")
3. Check:
   - `module` - which source file
   - `category` - domain category
   - `expected_return_type` - dict/list/any
   - `min_output_chars` - minimum content
   - `docstring_preview` - what the tool does
   - `required_params` - mandatory arguments

For testing help:
- See TOOL_TESTING_FRAMEWORK.md for test strategies
- Check category-specific examples above
- Use `validate_guidelines.py` to check individual tools

---

**Generated:** 2026-05-06  
**Analysis Tool:** Python 3.11 introspection + static analysis  
**Total Time:** ~5 minutes  
**Author:** Claude Backend Agent
