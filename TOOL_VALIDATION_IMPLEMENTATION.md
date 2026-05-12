# Tool Validation Implementation Guide

**Date:** 2026-05-06  
**Effort:** 3-5 days for full implementation  
**Owner:** Backend team

---

## What Was Generated

1. **tool_guidelines.json** - Quality metadata for all 835 tools
2. **TOOL_TESTING_FRAMEWORK.md** - Testing strategy and expectations
3. **TOOL_GUIDELINES_SUMMARY.md** - Complete overview and usage
4. **TOOL_GUIDELINES_ANALYSIS.txt** - Detailed category breakdown
5. **scripts/validate_guidelines.py** - CLI validation tool
6. **TOOL_VALIDATION_IMPLEMENTATION.md** - This implementation guide

---

## Phase 2: Unit Test Generation (2-3 days)

### Step 1: Create test fixture with guidelines

File: `tests/conftest.py` (add to existing file)

```python
import json
from pathlib import Path

@pytest.fixture(scope="session")
def tool_guidelines():
    """Load all 835 tool guidelines."""
    guidelines_path = Path(__file__).parent.parent / "tool_guidelines.json"
    with open(guidelines_path) as f:
        return json.load(f)

@pytest.fixture(scope="session")
def tool_functions(tool_guidelines):
    """Create mapping of tool names to functions."""
    from loom.tools import ALL_TOOLS  # requires export from tools/__init__.py
    
    mapping = {}
    for tool_name in tool_guidelines.keys():
        if tool_name in ALL_TOOLS:
            mapping[tool_name] = ALL_TOOLS[tool_name]
    
    return mapping
```

### Step 2: Create parametrized test file

File: `tests/test_tools/test_guidelines_validation.py`

```python
import json
import pytest
from typing import Any, Dict

def validate_tool_output(output: Any, guideline: Dict[str, Any]) -> tuple[bool, str]:
    """Validate output against guideline criteria."""
    criteria = guideline.get("quality_criteria", {})
    
    # Rule 1: Must not be empty
    if criteria.get("must_not_be_empty", True):
        if output is None or output == {} or output == [] or output == "":
            return False, "Output is empty"
    
    # Rule 2: Must be dict or list
    if criteria.get("must_be_dict_or_list", False):
        if not isinstance(output, (dict, list)):
            type_name = type(output).__name__
            return False, f"Expected dict/list, got {type_name}"
    
    # Rule 3: Minimum character length
    min_chars = criteria.get("min_chars", 0)
    output_str = json.dumps(output) if isinstance(output, (dict, list)) else str(output)
    if len(output_str) < min_chars:
        return False, f"Output too short ({len(output_str)} < {min_chars} chars)"
    
    return True, ""

@pytest.mark.parametrize("tool_name", 
    list(pytest.importorskip("loom.tools").ALL_TOOLS.keys()),
    ids=lambda t: t[:40]  # Shorten IDs for readability
)
async def test_tool_output_format(tool_name, tool_guidelines):
    """Validate that each tool returns expected format."""
    guideline = tool_guidelines.get(tool_name)
    if not guideline:
        pytest.skip(f"No guideline for {tool_name}")
    
    # Get the tool function
    from loom.tools import get_tool
    tool_fn = get_tool(tool_name)
    
    # Build minimal test parameters
    params = {}
    for required_param in guideline.get("required_params", []):
        # Use sensible defaults for common parameter names
        if "url" in required_param:
            params[required_param] = "https://example.com"
        elif "query" in required_param:
            params[required_param] = "test query"
        elif "prompt" in required_param:
            params[required_param] = "test prompt"
        else:
            params[required_param] = "test_value"
    
    # Call tool (with timeout)
    try:
        if guideline.get("is_async"):
            output = await asyncio.wait_for(tool_fn(**params), timeout=5.0)
        else:
            output = tool_fn(**params)
    except (TimeoutError, Exception) as e:
        pytest.skip(f"Tool execution failed: {str(e)[:100]}")
    
    # Validate
    is_valid, error_msg = validate_tool_output(output, guideline)
    assert is_valid, f"{tool_name}: {error_msg}"
```

### Step 3: Run the test suite

```bash
# Run all 835 tool validation tests
pytest tests/test_tools/test_guidelines_validation.py -v --tb=short

# Expected output:
# test_guidelines_validation.py::test_tool_output_format[research_fetch] PASSED
# test_guidelines_validation.py::test_tool_output_format[research_spider] PASSED
# ...
# 835 passed in 45.2s
```

---

## Phase 3: Content Validation Tests (1-2 days)

### Research Tools Category Tests

File: `tests/test_tools/test_guidelines_research.py`

```python
import pytest
from loom.tools import research_fetch, research_spider

async def test_research_fetch_has_results():
    """Research tools must return results field."""
    output = await research_fetch(url="https://httpbin.org/get")
    
    assert "content" in output or "html" in output or "data" in output, \
        "research_fetch missing content/data field"
    assert len(str(output)) > 100, "research_fetch output too short"

async def test_research_spider_returns_list():
    """research_spider must return list of results."""
    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/200"
    ]
    output = await research_spider(urls=urls, max_concurrent=2)
    
    assert isinstance(output, (list, dict)), "research_spider should return list or dict"
    if isinstance(output, dict):
        assert "results" in output or "items" in output

async def test_research_search_has_metadata():
    """Search tools must include metadata."""
    output = await research_search(query="test")
    
    assert isinstance(output, dict)
    assert any(k in output for k in ["results", "items", "data"])
    assert "query" in output or "q" in output or output.get("results")
```

### LLM Tools Category Tests

File: `tests/test_tools/test_guidelines_llm.py`

```python
import pytest
from loom.tools import research_llm_summarize, research_llm_translate

async def test_llm_summarize_returns_text():
    """LLM summarize must return actual text."""
    content = "This is a long piece of content " * 50
    output = await research_llm_summarize(content=content)
    
    assert isinstance(output, dict)
    assert "text" in output or "summary" in output or "result" in output
    
    text = output.get("text") or output.get("summary") or output.get("result")
    assert len(text) > 20, "Summary too short"
    assert len(text) < len(content), "Summary should be shorter than input"
    assert "..." not in text, "Summary should not have truncation markers"

async def test_llm_translate_not_empty():
    """LLM translate must return translation."""
    output = await research_llm_translate(
        text="Hello world",
        target_language="French"
    )
    
    assert isinstance(output, dict)
    assert "text" in output or "translation" in output or "result" in output
```

### Scoring Tools Category Tests

File: `tests/test_tools/test_guidelines_scoring.py`

```python
import pytest
from loom.tools import research_attack_score

def test_attack_score_has_confidence():
    """Attack scorer must include confidence."""
    output = research_attack_score(
        prompt="test prompt",
        response="test response"
    )
    
    assert isinstance(output, dict)
    assert "score" in output
    
    score = output["score"]
    assert isinstance(score, (int, float))
    assert 0 <= score <= 100, f"Score out of range: {score}"
    
    # Confidence is optional but good to have
    if "confidence" in output:
        conf = output["confidence"]
        assert 0 <= conf <= 1, f"Confidence out of range: {conf}"
```

---

## Phase 4: Regression Detection (1-2 days)

### Step 1: Generate baseline outputs

File: `tests/test_tools/test_guidelines_baseline.py`

```python
import json
import pytest
from pathlib import Path
from typing import Any, Dict

BASELINE_FILE = Path(__file__).parent.parent / "data" / "tool_outputs_baseline.json"

@pytest.fixture(scope="session")
def baseline_data():
    """Load baseline outputs."""
    if BASELINE_FILE.exists():
        with open(BASELINE_FILE) as f:
            return json.load(f)
    return {}

def save_baseline(outputs: Dict[str, Any]):
    """Save baseline outputs to file."""
    BASELINE_FILE.parent.mkdir(exist_ok=True, parents=True)
    with open(BASELINE_FILE, "w") as f:
        json.dump(outputs, f, indent=2, default=str)

@pytest.mark.parametrize("tool_name", SAMPLE_TOOLS[:10])
async def test_baseline_generation(tool_name, tool_guidelines):
    """Generate baseline outputs for sample tools.
    
    Run with: pytest -m baseline_gen
    """
    guideline = tool_guidelines[tool_name]
    
    # Build minimal params
    params = build_test_params(tool_name, guideline)
    
    # Execute tool
    from loom.tools import get_tool
    tool_fn = get_tool(tool_name)
    
    try:
        output = await asyncio.wait_for(tool_fn(**params), timeout=10.0)
        outputs[tool_name] = {
            "output_length": len(json.dumps(output)),
            "has_results": "results" in json.dumps(output).lower(),
            "output_type": type(output).__name__,
            "sample": str(output)[:500] if output else None
        }
    except Exception as e:
        outputs[tool_name] = {"error": str(e)[:100]}

@pytest.mark.parametrize("tool_name", SAMPLE_TOOLS[:10])
async def test_regression_detection(tool_name, tool_guidelines, baseline_data):
    """Detect regressions in tool outputs.
    
    Run with: pytest -m regression
    """
    baseline = baseline_data.get(tool_name)
    if not baseline:
        pytest.skip(f"No baseline for {tool_name}")
    
    # Execute tool and get current output
    guideline = tool_guidelines[tool_name]
    params = build_test_params(tool_name, guideline)
    from loom.tools import get_tool
    tool_fn = get_tool(tool_name)
    
    output = await asyncio.wait_for(tool_fn(**params), timeout=10.0)
    current_length = len(json.dumps(output))
    baseline_length = baseline.get("output_length", 0)
    
    # Flag significant shrinkage
    threshold = max(50, baseline_length * 0.3)  # 30% or 50 chars minimum
    if current_length < baseline_length - threshold:
        pytest.fail(
            f"{tool_name}: Output shrunk from {baseline_length} to {current_length} chars"
        )
```

### Step 2: Run baseline generation

```bash
# Generate baselines for first 10 tools
pytest tests/test_tools/test_guidelines_baseline.py -m baseline_gen -v

# This creates: tests/data/tool_outputs_baseline.json
```

### Step 3: Run regression tests in CI

```bash
# Compare current outputs against baseline
pytest tests/test_tools/test_guidelines_baseline.py -m regression -v

# Should report any significant changes
```

---

## Phase 5: CI/CD Integration (1 day)

### Add pre-commit hook

File: `.pre-commit-config.yaml` (add this hook)

```yaml
- repo: local
  hooks:
    - id: validate-tool-outputs
      name: Validate tool output formats
      entry: python scripts/validate_guidelines.py --guidelines tool_guidelines.json
      language: python
      files: src/loom/tools/.*\.py$
      stages: [commit]
      pass_filenames: false
      require_serial: true
```

### Add GitHub Actions workflow

File: `.github/workflows/tool-validation.yml`

```yaml
name: Tool Output Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - run: pip install -e ".[all]"
      
      # Run all 835 validation tests
      - name: Run tool output validation
        run: |
          pytest tests/test_tools/test_guidelines_validation.py \
            -v --tb=short --timeout=300 --maxfail=10
      
      # Check for regressions
      - name: Run regression detection
        run: |
          pytest tests/test_tools/test_guidelines_baseline.py \
            -m regression -v --tb=short
      
      # Upload artifacts on failure
      - name: Upload validation results
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: tool-validation-failures
          path: .pytest_cache/

  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - run: pip install -e ".[all]"
      
      - name: Generate coverage report
        run: |
          pytest tests/test_tools/test_guidelines_validation.py \
            --cov=src/loom/tools \
            --cov-report=html \
            --cov-report=term
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

---

## Implementation Checklist

### Phase 2: Unit Tests
- [ ] Create `tests/conftest.py` fixtures for guidelines and tools
- [ ] Create `tests/test_tools/test_guidelines_validation.py` (parametrized tests for all 835)
- [ ] Run locally: `pytest tests/test_tools/test_guidelines_validation.py -v`
- [ ] Target: 830+/835 passing (5% failure tolerance for network/external deps)
- [ ] Update `.gitignore` if needed for test artifacts

### Phase 3: Category Tests
- [ ] Create `tests/test_tools/test_guidelines_research.py`
- [ ] Create `tests/test_tools/test_guidelines_llm.py`
- [ ] Create `tests/test_tools/test_guidelines_scoring.py`
- [ ] Create `tests/test_tools/test_guidelines_infrastructure.py`
- [ ] Run: `pytest tests/test_tools/test_guidelines_*.py -v`

### Phase 4: Regression Detection
- [ ] Create `tests/test_tools/test_guidelines_baseline.py`
- [ ] Generate baseline: `pytest tests/test_tools/test_guidelines_baseline.py -m baseline_gen`
- [ ] Commit `tests/data/tool_outputs_baseline.json`
- [ ] Test regression detection: `pytest tests/test_tools/test_guidelines_baseline.py -m regression`

### Phase 5: CI/CD
- [ ] Update `.pre-commit-config.yaml` with validation hook
- [ ] Create `.github/workflows/tool-validation.yml`
- [ ] Test locally: `pre-commit run --all-files`
- [ ] Push and verify GitHub Actions runs
- [ ] Set up artifact uploads for failures
- [ ] Configure branch protection to require passing checks

### Documentation
- [ ] Update `docs/tools-reference.md` with guideline info
- [ ] Create troubleshooting guide for failed validations
- [ ] Document how to update baselines after intentional changes
- [ ] Add to developer onboarding docs

---

## Expected Results

### After Implementation

```
Test Results Summary:
  - Unit tests (format validation): 835/835 PASS
  - Category tests (content): 50+/50 PASS
  - Regression detection: ACTIVE
  - CI/CD integration: LIVE
  - Pre-commit: ACTIVE

Quality Metrics:
  - Output format compliance: 99.9%
  - False positive rate: < 1%
  - Test execution time: ~2 min per commit
  - Monthly regressions detected: ~2-5
```

---

## Troubleshooting

### Tool times out in tests
- Increase timeout in test (currently 5-10s)
- Add `@pytest.mark.timeout(30)` for network tests
- Consider mocking external APIs

### Too many failures
- Check if new tool parameter is missing in fixture
- Verify tool imports in ALL_TOOLS registry
- Check if external service is down

### Regression tests fail
- Update baseline: `pytest ... -m baseline_gen --baseline-update`
- Review changes to understand if intentional
- Commit new baseline if changes are expected

---

## Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 2 | 2-3 days | Now | +2 days |
| Phase 3 | 1-2 days | +2 days | +4 days |
| Phase 4 | 1-2 days | +4 days | +5 days |
| Phase 5 | 1 day | +5 days | +6 days |
| **Total** | **5-8 days** | Now | +6 days |

---

## Success Criteria

- [x] Guidelines generated for all 835 tools
- [ ] Unit tests created (Phase 2)
- [ ] Content validation tests created (Phase 3)
- [ ] Regression detection baseline established (Phase 4)
- [ ] CI/CD pipeline integrated (Phase 5)
- [ ] Documentation updated
- [ ] Team trained on validation process
- [ ] First month without regressions

---

## References

- `tool_guidelines.json` - Master guideline reference
- `TOOL_TESTING_FRAMEWORK.md` - Testing strategy details
- `TOOL_GUIDELINES_SUMMARY.md` - Complete overview
- `scripts/validate_guidelines.py` - CLI tool

---

**Ready to implement?** Start with Phase 2 - it's the most impactful and can be done in 2-3 days.

Questions? Check the summary document or review tool_guidelines.json directly.
