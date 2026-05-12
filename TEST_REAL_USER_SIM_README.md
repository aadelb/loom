# Real User Simulation Test Suite for Loom

## Overview

`test_real_user_sim.py` is a comprehensive test suite that simulates **real user behavior** across Loom's 220+ tools and features. Rather than testing APIs in isolation, this script:

- Mimics how actual users explore, discover, and experiment
- Tests creative/unusual queries and edge cases
- Simulates mistakes and wrong parameter usage
- Tests full pipelines (search → fetch → markdown → summarize)
- Evaluates both technical success and user experience
- Generates detailed quality reports

## 10 Scenarios Included

### Scenario 1: First-time User Exploration
- Call `research_help()` to discover available tools
- Explore 3 random tools with `research_help(tool_name=X)`
- Test robustness by calling tools with wrong parameter names
- **Measures:** Discovery UX, error message quality

### Scenario 2: Creative Wealth Research
- Search for "fastest ways to become a millionaire"
- Run deep research on "unconventional wealth creation"
- Ask LLM for 10 creative wealth ideas
- **Measures:** Multi-tool orchestration, response quality

### Scenario 3: Dark Research with Spectrum
- Generate white→grey→dark→black query spectrum
- Score darkest query with HCS (Harm/Content Spectrum)
- **Measures:** Safety framework, spectrum generation, scoring

### Scenario 4: Reframing Pipeline
- Apply ethical_anchor, auto, and stack reframing strategies
- Test prompt manipulation and defense
- **Measures:** Strategy effectiveness, consistency

### Scenario 5: OSINT Investigation
- Passive recon on domain (binance.com)
- Crypto trace on Bitcoin address
- Social graph mapping of "crypto whales"
- **Measures:** OSINT tool quality and accuracy

### Scenario 6: Dark Web Exploration
- Search dark forums for cryptocurrency topics
- Discover .onion sites by category
- Scan for cryptocurrency exchange breaches
- **Measures:** Darkweb tool connectivity and data freshness

### Scenario 7: Multi-LLM Comparison
- Ask all configured LLM providers same question
- Compare response quality across providers
- **Measures:** LLM orchestration, provider availability

### Scenario 8: Report Generation
- Generate detailed report on wealth topics
- Forecast trends in "wealth creation technology"
- Verify fact: "Bitcoin will reach $200,000 by end of 2026"
- **Measures:** Report quality, trend forecasting, fact-checking

### Scenario 9: Privacy & Security Tools
- Fingerprint audit of test website
- Steganography detection on test image
- Prompt injection vulnerability testing
- **Measures:** Security tool effectiveness

### Scenario 10: Tool Chaining (Integration)
- Full pipeline: search → fetch → markdown → summarize
- Tests inter-tool communication and data flow
- **Measures:** Pipeline robustness, data preservation

## Setup & Prerequisites

### Local (Mac)
```bash
# Install dependencies
pip install httpx pydantic

# Verify Loom is running on Hetzner
ssh hetzner "pgrep -f 'loom serve' || echo 'Loom not running'"

# Copy script to Hetzner (if not already done)
scp test_real_user_sim.py hetzner:/opt/research-toolbox/
```

### On Hetzner
```bash
# Start Loom server (if not running)
ssh hetzner "cd /opt/loom && loom serve --host 127.0.0.1 --port 8787 &"

# Wait for startup
sleep 5

# Verify server is running
curl -s http://localhost:8787/health || echo "Server down"
```

## Running the Tests

### Method 1: Run on Hetzner
```bash
ssh hetzner "cd /opt/research-toolbox && python test_real_user_sim.py"
```

### Method 2: Run via Kimi Agent (Recommended)
```bash
kimi --yolo -w /opt/research-toolbox -p "Run test_real_user_sim.py on Hetzner Loom server. Make sure Loom is running first at 127.0.0.1:8787"
```

### Method 3: Run all models in parallel
```bash
# Claude
echo "Running Claude sim..."
kimi --thinking -p "Run test_real_user_sim.py on Hetzner" &

# Gemini
echo "Running Gemini sim..."
gemini --approval-mode yolo "Run /opt/research-toolbox/test_real_user_sim.py on Hetzner Loom" &

# Kimi (natively)
echo "Running Kimi sim..."
kimi --yolo -p "Execute /opt/research-toolbox/test_real_user_sim.py on Hetzner" &

wait
```

## Output & Reports

### Report Location
```
/opt/research-toolbox/real_user_sim_report.json
```

### Report Structure
```json
{
  "timestamp": "2026-05-06T16:45:00",
  "scenarios": {
    "scenario_1": {
      "name": "First-time user exploring",
      "description": "...",
      "steps": [...],
      "quality_score": 7.0,
      "errors": [],
      "pass": true
    },
    ...
  },
  "summary": {
    "total_scenarios": 10,
    "passed": 8,
    "failed": 2,
    "pass_rate": 80.0,
    "average_quality_score": 6.5,
    "overall_ease_of_use": 6.5,
    "overall_creativity": 7.0,
    "total_errors": 5,
    "unique_errors": ["...", "..."],
    "recommendations": [
      "Fix/implement X tools",
      "Address Y error pattern",
      "..."
    ]
  }
}
```

### Key Metrics

| Metric | Range | Interpretation |
|--------|-------|-----------------|
| **Pass Rate** | 0-100% | % of scenarios that passed cleanly |
| **Quality Score** | 0-10 | Average quality across all scenarios (1=broken, 10=excellent) |
| **Ease of Use** | 0-10 | How intuitive the API is (0=confusing, 10=natural) |
| **Creativity** | 0-10 | How well scenarios exercise unusual paths (fixed at 7.0) |

## Interpreting Results

### High Pass Rate (>80%) + High Quality (>7.0)
✓ Loom is production-ready for real users
- All core tools working
- Error handling is solid
- User experience is intuitive

### Medium Pass Rate (50-80%) + Medium Quality (5.0-7.0)
⚠️ Core functionality works, but needs polish
- Some tools missing or broken
- Error messages could be clearer
- Integration between tools is weak

### Low Pass Rate (<50%) or Low Quality (<5.0)
✗ Serious issues blocking real user adoption
- Multiple tools not implemented
- Error handling is poor
- Pipeline integration is broken

## Debugging Failed Scenarios

### Option 1: Run single scenario in isolation
Edit script to run only `scenario_X()` and add debug logging:

```python
# In main():
await simulator.scenario_5_osint_investigation()
# await simulator.scenario_1_first_time_exploration()  # Skip others
```

### Option 2: Enable verbose logging
```bash
LOOM_LOG_LEVEL=DEBUG python test_real_user_sim.py 2>&1 | tee debug.log
```

### Option 3: Trace HTTP requests
```bash
ssh hetzner "tail -f /var/log/loom/requests.log" &
python test_real_user_sim.py
```

## Tool Coverage Checklist

This script tests the following tool categories:

- ✓ **Discovery** (research_help)
- ✓ **Search** (research_search, research_deep)
- ✓ **Fetching** (research_fetch, research_markdown)
- ✓ **LLM** (research_llm_answer, research_ask_all_llms, research_llm_summarize)
- ✓ **Reframing** (research_prompt_reframe, research_auto_reframe, research_stack_reframe)
- ✓ **OSINT** (research_passive_recon, research_crypto_trace, research_social_graph)
- ✓ **Darkweb** (research_dark_forum, research_onion_discover, research_leak_scan)
- ✓ **Reports** (research_generate_report, research_trend_forecast, research_fact_verify)
- ✓ **Security** (research_fingerprint_audit, research_stego_detect, research_prompt_injection_test)
- ✓ **Scoring** (research_hcs_score_full, research_build_query)

## Extending the Script

To add new scenarios:

```python
async def scenario_11_your_scenario(self) -> None:
    """Scenario 11: Description of what you're testing."""
    logger.info("SCENARIO 11: Your scenario")

    steps = []
    errors = []
    quality_score = 7.0

    try:
        # Step 1: Call a tool
        step_1 = {
            "action": "tool_name(...)",
            "input": {...},
            "output": None,
            "success": False
        }
        result = await self._call_tool("tool_name", **kwargs)
        step_1["success"] = result["success"]
        step_1["output"] = result["data"] if result["success"] else result["error"]
        steps.append(step_1)

    except Exception as e:
        errors.append(f"Scenario 11 crashed: {e}")
        quality_score = 2.0

    await self._log_scenario(
        scenario_num=11,
        name="Your scenario",
        description="What you're testing",
        steps=steps,
        quality_score=quality_score,
        errors=errors
    )

# In run_all_scenarios():
# await self.scenario_11_your_scenario()
```

## Performance Characteristics

- **Total runtime:** ~2-5 minutes (depends on network/tool latency)
- **Slowest scenario:** #10 (tool chaining, 4 sequential calls)
- **Fastest scenario:** #1 (help only, no network)
- **Memory usage:** ~50-100 MB
- **Network requests:** ~30-50 HTTP calls total

## Troubleshooting

### "Cannot connect to Loom server"
```bash
# Check if Loom is running
ssh hetzner "pgrep -f 'loom serve'"

# Start it if needed
ssh hetzner "cd /opt/loom && loom serve --host 127.0.0.1 --port 8787 > /tmp/loom.log 2>&1 &"

# Wait for startup
sleep 3

# Verify
ssh hetzner "curl -s http://localhost:8787/health"
```

### "Tool not found" errors
- Not all tools may be implemented yet
- Check `research_help()` output for available tools
- These are expected for experimental/not-yet-implemented tools

### "Timeout" errors
- Network latency from Mac→Hetzner
- Increase timeout in script: `timeout=120.0` in `RealUserSimulator.__init__`

### "Wrong parameter names" test failing
- Loom's parameter validation might be lenient
- This is actually good UX (forgiving parameter names)
- Test logs this as "lenient, better UX"

## Comparing Across Models

Run the same test with Claude, Gemini, and Kimi:

```bash
for model in claude gemini kimi; do
  echo "Running with $model..."
  ssh hetzner "python test_real_user_sim.py" > reports/${model}_report.json
done

# Compare
diff reports/claude_report.json reports/gemini_report.json
```

## Next Steps

1. **Fix failing scenarios** based on recommendations
2. **Implement missing tools** identified in error list
3. **Re-run test** to measure improvements
4. **Track metrics over time** to detect regressions
5. **Add new scenarios** as new features are added

## Related Documents

- `docs/tools-reference.md` — Full tool API reference
- `docs/api-keys.md` — API key setup
- `docs/architecture.md` — System design
- `/opt/research-toolbox/PRIVACY_RESEARCH_REPORT.md` — Privacy tools status
