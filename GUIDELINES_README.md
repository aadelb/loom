# Loom Tool Guidelines - Complete Documentation Index

**Generated:** 2026-05-06  
**Status:** READY FOR IMPLEMENTATION  
**Total Tools:** 835

---

## Quick Start

### For Testing Your Tools
1. Read: `TOOL_TESTING_FRAMEWORK.md`
2. Reference: `tool_guidelines.json` (master data)
3. Validate: `python scripts/validate_guidelines.py`

### For Implementation
1. Follow: `TOOL_VALIDATION_IMPLEMENTATION.md` (5-8 day plan)
2. Review: `TOOL_GUIDELINES_SUMMARY.md` (comprehensive overview)
3. Analyze: `TOOL_GUIDELINES_ANALYSIS.txt` (category breakdown)

### For Quick Lookup
```bash
# Check a specific tool's guidelines
python scripts/validate_guidelines.py --guidelines tool_guidelines.json --tool research_fetch

# Get summary statistics
python scripts/validate_guidelines.py --guidelines tool_guidelines.json
```

---

## Files Generated (6 New Files)

### 1. tool_guidelines.json (520 KB) - MASTER REFERENCE
**Location:** `/Users/aadel/projects/loom/tool_guidelines.json`

Complete quality metadata for all 835 tools. Machine-readable JSON format.

**Contains per tool:**
- Source module
- Category (research, llm, scoring, etc.)
- Required and optional parameters
- Execution model (async/sync)
- Expected return type
- Minimum output character length
- Quality criteria (machine-checkable rules)
- Docstring preview

**Usage:**
```python
import json

with open("tool_guidelines.json") as f:
    guidelines = json.load(f)

# Get guideline for specific tool
guideline = guidelines["research_fetch"]
print(f"Min output: {guideline['min_output_chars']} chars")
```

---

### 2. TOOL_TESTING_FRAMEWORK.md (4.1 KB) - TESTING STRATEGY
**Location:** `/Users/aadel/projects/loom/TOOL_TESTING_FRAMEWORK.md`

Complete testing methodology and category-specific expectations.

**Sections:**
- Test plan (5 phases: analysis, unit tests, content validation, regression, CI/CD)
- Output quality validation rules
- Category-specific expectations with GOOD/BAD examples:
  - Research tools (810 tools) - must have results, metadata, timing
  - LLM tools - must have actual text, not hardcoded
  - Scoring tools - must have score, confidence, reasoning
  - Infrastructure tools - must have status field
- Regression detection workflow
- CI/CD integration approach

**Best for:** Understanding what good output looks like

---

### 3. TOOL_GUIDELINES_SUMMARY.md (12 KB) - COMPLETE OVERVIEW
**Location:** `/Users/aadel/projects/loom/TOOL_GUIDELINES_SUMMARY.md`

Comprehensive reference covering everything about the guidelines.

**Sections:**
- Executive summary
- Key statistics (835 tools, 100% docstrings, 81% async)
- Category breakdown with examples
- Quality criteria for each category (with JSON examples)
- Testing phases and timeline
- How to use the guidelines
- Maintenance schedule
- Success criteria

**Best for:** Orientation and comprehensive understanding

---

### 4. TOOL_GUIDELINES_ANALYSIS.txt (5 KB) - CATEGORY BREAKDOWN
**Location:** `/Users/aadel/projects/loom/TOOL_GUIDELINES_ANALYSIS.txt`

Detailed analysis with examples from each category.

**Contains:**
- Sample tools from each category (with all guideline fields)
- Category statistics
- Execution model breakdown
- Return type distribution
- Docstring coverage
- Minimum output chars per category

**Best for:** Quick reference and category-specific examples

---

### 5. TOOL_VALIDATION_IMPLEMENTATION.md (16 KB) - IMPLEMENTATION PLAN
**Location:** `/Users/aadel/projects/loom/TOOL_VALIDATION_IMPLEMENTATION.md`

Step-by-step guide to implement tool validation (5-8 days).

**Covers all 5 phases:**
1. **Phase 2: Unit Test Generation** (2-3 days)
   - Create test fixtures
   - Parametrized tests for all 835 tools
   - Format validation
   
2. **Phase 3: Content Validation** (1-2 days)
   - Category-specific validators
   - Research, LLM, scoring, infrastructure tests
   
3. **Phase 4: Regression Detection** (1-2 days)
   - Baseline generation
   - Regression test suite
   
4. **Phase 5: CI/CD Integration** (1 day)
   - Pre-commit hooks
   - GitHub Actions workflow
   
**Includes:**
- Code examples for each phase
- Step-by-step instructions
- Expected results
- Troubleshooting
- Timeline and checklist

**Best for:** Implementing the full validation pipeline

---

### 6. scripts/validate_guidelines.py (2.8 KB) - CLI TOOL
**Location:** `/Users/aadel/projects/loom/scripts/validate_guidelines.py`

Command-line tool to validate and inspect tool guidelines.

**Usage:**
```bash
# Get summary statistics
python scripts/validate_guidelines.py --guidelines tool_guidelines.json

# Check specific tool
python scripts/validate_guidelines.py --guidelines tool_guidelines.json --tool research_fetch

# Verbose output
python scripts/validate_guidelines.py --guidelines tool_guidelines.json -v
```

**Output:**
```
Tool Guidelines Summary
======================

Total tools: 835

By Category:
  research            : 810
  other               :  15
  infrastructure      :   5
  darkweb             :   3
  scoring             :   1
  analysis            :   1

Docstrings: 835/835 (100.0%)
Async: 678/835 (81.2%)
```

**Best for:** Quick checks and CI/CD integration

---

## Guidelines at a Glance

### Coverage
- **Total Tools:** 835
- **Categories:** 6 (research, other, infrastructure, darkweb, scoring, analysis)
- **With Docstrings:** 835 (100%)
- **Async Tools:** 678 (81.2%)
- **Sync Tools:** 157 (18.8%)

### Quality Tiers by Category

| Category | Tools | Min Output | Type | Priority |
|----------|-------|-----------|------|----------|
| **research** | 810 | 200 chars | dict/list | HIGH |
| **other** | 15 | 50 chars | any | MEDIUM |
| **infrastructure** | 5 | 50 chars | dict | MEDIUM |
| **darkweb** | 3 | 50 chars | any | LOW |
| **scoring** | 1 | 50 chars | dict | HIGH |
| **analysis** | 1 | 100 chars | dict | MEDIUM |

### Quality Criteria

All outputs MUST:
1. Not be empty (null/empty dict/empty list check)
2. Match expected type (dict, list, or flexible)
3. Meet minimum character length for category
4. Follow category-specific rules:
   - **Research:** Include results/data + metadata
   - **LLM:** Actual text (not hardcoded/truncated)
   - **Scoring:** Score + confidence + reasoning
   - **Infrastructure:** Status field present

---

## Reading Path by Role

### QA/Testing Team
1. Start: `TOOL_TESTING_FRAMEWORK.md` (test strategy)
2. Then: `TOOL_GUIDELINES_ANALYSIS.txt` (examples per category)
3. Reference: `tool_guidelines.json` (specific tool lookups)
4. Implement: `TOOL_VALIDATION_IMPLEMENTATION.md` (Phase 2-3)

### Backend Developers
1. Start: `TOOL_GUIDELINES_SUMMARY.md` (overview)
2. Then: `TOOL_GUIDELINES_ANALYSIS.txt` (your tool's category)
3. Reference: `tool_guidelines.json` (exact requirements)
4. When adding tool: Review category expectations in FRAMEWORK

### DevOps/CI-CD
1. Start: `TOOL_VALIDATION_IMPLEMENTATION.md` (Phase 5)
2. Then: `TOOL_TESTING_FRAMEWORK.md` (regression detection)
3. Reference: `scripts/validate_guidelines.py` (CLI tool)
4. Implement: Pre-commit + GitHub Actions from IMPLEMENTATION

### Product/Architecture
1. Start: `TOOL_GUIDELINES_SUMMARY.md` (complete overview)
2. Then: `TOOL_GUIDELINES_ANALYSIS.txt` (category breakdown)
3. Reference: `GUIDELINES_INDEX.json` (metrics)

---

## Implementation Timeline

### Week 1: Unit Tests
- Day 1-2: Create fixtures and parametrized tests (Phase 2)
- Day 3-4: Run all 835 tests, fix failures
- Day 5: Document results, update CI/CD

### Week 2: Content + Regression
- Day 1-2: Create category-specific tests (Phase 3)
- Day 3-4: Generate regression baselines (Phase 4)
- Day 5: Integrate CI/CD pipeline (Phase 5)

### Week 3: Stabilization
- Monitor test results
- Fix false positives
- Document common issues
- Train team

---

## Key Metrics to Track

### Test Coverage
- Format validation: Target 830+/835 (99%+)
- Content validation: Target 50+/50 (100%)
- Regression detection: Active (monthly reports)

### Quality Indicators
- False positive rate: Target < 1%
- Test execution time: Target < 5 min per commit
- Monthly regressions: Target < 5

### Maintenance
- Baseline updates per month: 0-2 (intentional changes only)
- New tools added per month: Varies
- Guideline changes per quarter: 1-2 (quality bar adjustments)

---

## Common Questions

### "How do I validate my tool's output?"
See `TOOL_TESTING_FRAMEWORK.md` category section matching your tool type.

### "What's the minimum output length?"
Check `tool_guidelines.json` for your tool: `"min_output_chars": X`

### "How do I add a new tool?"
1. Add function to `src/loom/tools/`
2. Register in `server.py:_register_tools()`
3. Regenerate `tool_guidelines.json`
4. Add tests following pattern in `TOOL_VALIDATION_IMPLEMENTATION.md`

### "Why did my tool fail validation?"
1. Check `TOOL_TESTING_FRAMEWORK.md` for category expectations
2. Run `python scripts/validate_guidelines.py --tool your_tool`
3. Compare against "GOOD OUTPUT" examples
4. Review your output against quality criteria

### "How often should I regenerate guidelines?"
- Automatically: Monthly (via CI/CD script)
- Manually: When adding new tool or changing signature
- Command: `python scripts/regenerate_guidelines.py` (to be created)

---

## Files Location

**All files in:** `/Users/aadel/projects/loom/`

```
├── tool_guidelines.json                    # Master data (520 KB)
├── TOOL_TESTING_FRAMEWORK.md               # Testing strategy (4.1 KB)
├── TOOL_GUIDELINES_SUMMARY.md              # Complete overview (12 KB)
├── TOOL_GUIDELINES_ANALYSIS.txt            # Category breakdown (5 KB)
├── TOOL_VALIDATION_IMPLEMENTATION.md       # 5-phase implementation (16 KB)
├── GUIDELINES_README.md                    # This file
├── GUIDELINES_INDEX.json                   # Quick reference (1 KB)
└── scripts/validate_guidelines.py          # CLI tool (2.8 KB)
```

---

## Next Steps

1. **Review:** Read `TOOL_TESTING_FRAMEWORK.md` (15 min)
2. **Understand:** Check `TOOL_GUIDELINES_ANALYSIS.txt` for your tool's category (10 min)
3. **Plan:** Follow `TOOL_VALIDATION_IMPLEMENTATION.md` (5-8 days)
4. **Implement:** Phase 2 → Phase 5 (check implementation guide)
5. **Maintain:** Monthly baseline updates + quarterly quality reviews

---

## Support

- **Quick lookup:** Use `scripts/validate_guidelines.py`
- **Category examples:** See `TOOL_GUIDELINES_ANALYSIS.txt`
- **Testing help:** See `TOOL_TESTING_FRAMEWORK.md`
- **Implementation:** See `TOOL_VALIDATION_IMPLEMENTATION.md`
- **Complete reference:** See `tool_guidelines.json`

---

**Last Updated:** 2026-05-06  
**Status:** Ready for implementation  
**Questions?** Check the relevant guide above or review tool_guidelines.json directly
