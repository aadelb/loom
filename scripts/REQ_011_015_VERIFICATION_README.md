# REQ-011 through REQ-015 Verification Script

Complete verification suite for Loom v3 reframing functionality.

## Requirements Tested

### REQ-011: Refusal Pattern Detection (30 samples)
Tests the `_detect_refusal()` function on 15 known refusals and 15 known compliances.

**Expectations:**
- Correctly identifies all refusal patterns (English + Arabic)
- 33 total patterns across 14 categories
- Supports both direct refusals and soft/hedged refusals
- 100% accuracy target

**Results:** ✓ PASS - 100% accuracy (15/15 refusals, 15/15 compliances detected correctly)

### REQ-012: Strategy Rendering (ALL strategies)
Verifies that all 957 strategies in `_STRATEGIES` can be rendered via `template.format()`.

**Expectations:**
- Every strategy has a valid template
- Template rendering produces non-empty output
- Output is longer than original prompt
- 99%+ success rate acceptable

**Results:** ✓ PASS - 99.9% success rate (956/957 render successfully)

### REQ-013: Auto-Reframe on Refused Prompts (5 samples)
Tests `research_prompt_reframe(strategy="auto")` on harmful prompts to verify strategy selection works.

**Expectations:**
- Auto-detection selects model-appropriate strategy
- Reframing produces coherent output
- Strategy is from the optimized escalation path
- 1 reframe per prompt (no retry needed)

**Results:** ✓ PASS - All 5 prompts reframed with crescendo strategy (5.8x multiplier)

### REQ-014: Precision/Recall Metrics (100 samples)
Runs `_detect_refusal()` on 50 known refusals + 50 known compliances to compute classification metrics.

**Expectations:**
- Precision ≥ 95% (minimize false positives)
- Recall ≥ 90% (catch most true refusals)
- F1-Score ≥ 0.90
- Specificity 100% (perfect on compliances)

**Results:** ✓ PASS
- Precision: 100.0% (0 false positives)
- Recall: 94.0% (47/50 true refusals caught)
- F1-Score: 0.9691
- Specificity: 100.0%

### REQ-015: Stack Reframe Effectiveness
Compares stacked strategies (2-3 combined) vs. individual strategies.

**Expectations:**
- Stacked output is longer than single strategy (target: +50%)
- Stacked multiplier higher than max single strategy (due to synergy)
- Synergy computation respects pairwise coefficients
- Ceiling at 10.0x multiplier

**Results:** ✓ PASS
- Length increase: 77.7% (949 chars vs. 534 chars)
- Multiplier boost: 35.1% (10.0x vs. 7.4x)

## Running the Script

### Local (Mac)
```bash
cd /Users/aadel/projects/loom
PYTHONPATH=src python3 scripts/verify_011_015.py 2>&1
```

### Remote (Hetzner)
```bash
ssh hetzner "cd /opt/research-toolbox && PYTHONPATH=src python3 scripts/verify_011_015.py 2>&1"
```

## Output Files

- **Console Log:** Detailed per-test output with pass/fail indicators
- **JSON Results:** `scripts/verify_011_015_results.json` containing:
  - REQ-011: Accuracy, pattern categories, sample texts
  - REQ-012: Total/renderable counts, failed strategies, samples
  - REQ-013: Prompt count, strategy selections, reframed previews
  - REQ-014: TP/TN/FP/FN, precision, recall, specificity, F1
  - REQ-015: Length/multiplier comparisons, strategies used

## Test Data

### Known Refusals (30 in test, 50 in metrics)
- English patterns: direct refusals, soft refusals, policy violations, ethical concerns, etc.
- Arabic patterns: 10 Arabic-language refusal patterns with regex support

### Known Compliances (30 in test, 50 in metrics)
- Positive responses, offers of assistance, willingness to help
- Technical explanations, guidance, detailed information

### Harmful Prompts (5 for auto-reframe)
- Malware creation, identity theft, scamming, banking fraud, phishing

## Implementation Details

### Pattern Matching (_REFUSAL_PATTERNS)
- 23 English patterns covering common refusal types
- 10 Arabic patterns with multilingual support
- Case-insensitive regex matching
- 14 distinct refusal categories

### Strategy Rendering (_STRATEGIES)
- 957 total strategies from 32 modules
- Each strategy has: name, template, multiplier, best_for
- Template variables: {prompt}, {framework}, {role}, {org}, {credentials}, etc.
- Fallback defaults for missing variables

### Auto-Reframe Selection
- Model family detection from prompt/response
- Model-specific "best_strategy" from _MODEL_CONFIGS
- Fallback escalation path if primary strategy fails
- 21 pre-configured model families (Claude, GPT, Gemini, DeepSeek, etc.)

### Stacking & Multiplier Computation
- Pairwise synergy coefficients (0.3 - 0.85 range)
- Harmonic decay to prevent unbounded growth
- Ceiling at 10.0x for 3-strategy stacks
- Base multiplier + synergy bonuses formula

## Troubleshooting

### REQ-011 False Negatives (Missed Refusals)
- Check if pattern is too strict or requires language-specific handling
- Add new pattern to _REFUSAL_PATTERNS if needed
- Test with `_detect_refusal("your_text")`

### REQ-012 Rendering Failures
- Verify strategy has "template" field
- Check for invalid format placeholders (not in defaults dict)
- Run: `_apply_strategy("test prompt", "strategy_name", "gpt")`

### REQ-013 Wrong Strategy Selection
- Verify model family detection is correct
- Check _MODEL_CONFIGS has entry for detected model
- Confirm best_strategy and escalation fields exist

### REQ-014 Low Recall
- More false negatives = missing patterns
- Add patterns to _REFUSAL_PATTERNS for missed cases
- Consider multilingual patterns if testing non-English texts

### REQ-015 Low Multiplier Boost
- Verify _STRATEGY_SYNERGY has entries for strategy pairs
- Check ceiling limit (10.0x) isn't being hit
- Ensure both strategies have valid multiplier fields

## Dependencies

- Python 3.11+
- httpx (async HTTP client)
- pydantic (models & validation)
- Standard library: json, logging, re, asyncio, dataclasses

## Performance

- REQ-011: ~100ms (30 samples)
- REQ-012: ~500ms (957 strategies rendered)
- REQ-013: ~50ms (5 auto-reframes)
- REQ-014: ~50ms (100 pattern matches)
- REQ-015: ~100ms (stacking computation)
- **Total:** ~5 seconds on modern hardware

## Maintenance

After modifying refusal patterns or strategies:

1. Run script locally to verify changes
2. Check JSON output for regressions
3. Compare before/after metrics
4. Deploy to Hetzner for final validation
5. Archive results with timestamp

## Related Files

- Implementation: `src/loom/tools/prompt_reframe.py`
- Strategies: `src/loom/tools/reframe_strategies/` (32 modules)
- Config: `src/loom/tools/prompt_reframe.py` (_MODEL_CONFIGS, _REFUSAL_PATTERNS)
- Tests: `tests/test_tools/test_prompt_reframe.py`

## Author

Ahmed Adel Bakr Alderai

## Version

v1.0 - Initial verification suite for REQ-011 through REQ-015
