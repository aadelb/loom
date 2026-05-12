# Loom Tool Testing Framework & Guidelines

Generated: 2026-05-06
Total Tools: 835
Guidelines File: /opt/research-toolbox/tool_guidelines.json

## Executive Summary

All 835 Loom tools have been analyzed and guideline definitions generated.

## Key Metrics

Total Tools: 835 (across 154 tool modules)
Tools with Docstrings: 835 (100%)
Async Tools: 678 (81.2%)
Sync Tools: 157 (18.8%)
Dict Return Type: 677 (81.0%)
List Return Type: 12 (1.4%)
Any Return Type: 146 (17.5%)

## Category Breakdown

research:        810 (min output: 200 chars)
other:            15 (min output: 50 chars)
infrastructure:    5 (min output: 50 chars)
darkweb:           3 (min output: 50 chars)
scoring:           1 (min output: 50 chars)
analysis:          1 (min output: 100 chars)

## Test Plan

Phase 1: Static Analysis
  - Generate guidelines for all 835 tools [COMPLETE]
  - Extract docstrings, parameters, return types [COMPLETE]
  - Categorize by domain [COMPLETE]
  - Define quality criteria per category [COMPLETE]

Phase 2: Unit Test Generation
  - Generate parametrized tests for each tool
  - Validate output format per guideline
  - Check minimum content requirements

Phase 3: Content Validation Tests
  - Per-category validation (research, llm, scoring)
  - Verify non-empty results
  - Check field presence

Phase 4: Regression Detection
  - Baseline outputs for all tools with mocked responses
  - Stored in tests/data/tool_outputs_baseline/

Phase 5: CI/CD Integration
  - Add pre-commit hooks
  - Add GitHub Actions workflow
  - Fail on guideline violations

## Output Quality Validation

Every tool output MUST pass:

1. Not empty (rule: must_not_be_empty = true)
2. Type check (dict or list if specified)
3. Minimum content (must exceed min_output_chars)

## Category-Specific Expectations

RESEARCH TOOLS (810 tools):
  - Min Output: 200 characters
  - Expected Types: dict, list
  - MUST include: data/results, metadata, timing info
  - Quality Bar: No empty results unless query had no matches
  
  GOOD: {"results": [...], "total": 42, "execution_time_ms": 145}
  BAD: {"error": "Something went wrong"}

LLM TOOLS:
  - Min Output: 30 characters (short summaries OK)
  - Expected Types: dict with text/content/result key
  - MUST be actual LLM response, not hardcoded
  - Quality Bar: No truncation, complete sentences
  
  GOOD: {"text": "The research shows...", "model": "groq", "tokens": 256}
  BAD: {"text": "..."}

SCORING TOOLS:
  - Min Output: 50 characters
  - Expected Types: dict with numeric scores
  - MUST include: score value, confidence, reasoning
  - Quality Bar: Scores in valid ranges (0-100), with explanation
  
  GOOD: {"score": 78, "confidence": 0.92, "reasoning": "Attack demonstrates..."}
  BAD: {"score": 78}

INFRASTRUCTURE TOOLS:
  - Min Output: 50 characters
  - Expected Types: dict with status/config data
  - MUST include: status field
  - Quality Bar: Boolean success or structured status
  
  GOOD: {"status": "ok", "sessions_active": 3}
  BAD: {"ok": true}

## Guideline Structure (Per Tool)

{
  "research_fetch": {
    "module": "fetch",
    "category": "research",
    "required_params": ["url"],
    "optional_params": ["headers", "timeout"],
    "is_async": true,
    "expected_return_type": "dict",
    "min_output_chars": 200,
    "quality_criteria": {
      "must_not_be_empty": true,
      "must_be_dict_or_list": true,
      "min_chars": 200
    },
    "has_docstring": true
  }
}

## Files Generated

1. tool_guidelines.json (520 KB)
   - Master reference: 835 tools with quality metadata
   - Used by test suite, CI/CD, dashboards

2. TOOL_TESTING_FRAMEWORK.md (this file)
   - Testing strategy and guidelines
   - Category-specific expectations
   - Regression detection approach

3. scripts/validate_guidelines.py (to create)
   - Run test suite on all 835 tools
   - Report failures and coverage metrics
   - Generate baseline outputs

## Success Criteria

- All 835 tools have guidelines defined [DONE: 835/835]
- 100% of tools have docstrings [DONE: 835/835]
- All tools validated for output format [TARGET: 830+/835]
- Regression detection in CI/CD [TO DO]
- Less than 5% false positives [TO DO]

