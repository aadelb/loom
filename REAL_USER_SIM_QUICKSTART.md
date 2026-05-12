# Real User Simulation - Quick Start

## What It Does

Tests Loom with **10 realistic user scenarios** covering:
- Exploration & discovery
- Creative research
- Dark web research
- Prompt reframing
- OSINT investigations
- Multi-LLM comparison
- Report generation
- Privacy tools
- Tool chaining

Each scenario logs what users try, what works, what breaks, and quality ratings.

## 30-Second Setup

```bash
# 1. Copy script to Hetzner (if not already done)
scp test_real_user_sim.py hetzner:/opt/research-toolbox/

# 2. Start Loom server on Hetzner
ssh hetzner "cd /opt/loom && loom serve --host 127.0.0.1 --port 8787 &"
sleep 3

# 3. Run the test
ssh hetzner "python /opt/research-toolbox/test_real_user_sim.py"

# 4. View results
ssh hetzner "cat /opt/research-toolbox/real_user_sim_report.json"
```

## Or Use Kimi Agent (Easier)

```bash
kimi --yolo -w /opt/research-toolbox -p "
Run test_real_user_sim.py on Hetzner:
1. Make sure Loom is running at 127.0.0.1:8787
2. Execute: python test_real_user_sim.py
3. Show the report from real_user_sim_report.json
"
```

## Reading the Report

```json
{
  "summary": {
    "pass_rate": 80.0,              // % of scenarios that passed
    "average_quality_score": 6.5,   // Overall quality 0-10
    "total_errors": 5,              // Total errors found
    "recommendations": [            // What to fix next
      "Fix/implement X tools",
      "Address Y error pattern"
    ]
  }
}
```

### Quick Interpretation

| Pass Rate | Quality | Meaning |
|-----------|---------|---------|
| >80% | >7.0 | ✓ Production ready |
| 50-80% | 5.0-7.0 | ⚠️ Needs work |
| <50% | <5.0 | ✗ Major issues |

## The 10 Scenarios (1 minute each)

1. **Exploration** — research_help() on 3 tools + test wrong params
2. **Creative** — Search millionaire strategies, deep research, LLM ideas
3. **Dark** — Query spectrum (white→black), HCS scoring
4. **Reframing** — Ethical anchor, auto, stack strategies
5. **OSINT** — Passive recon, crypto trace, social graph
6. **Darkweb** — Dark forums, onion discovery, leak scan
7. **Multi-LLM** — Ask all providers one question
8. **Reports** — Generate report, forecast trend, verify fact
9. **Security** — Fingerprint audit, stego detection, prompt injection
10. **Integration** — Full pipeline: search→fetch→markdown→summarize

## What Gets Logged

For each scenario:
- ✓ Tool calls (input + output)
- ✗ Errors and failures
- 📊 Quality score (1-10)
- 💬 Notes on what worked/broke

## Extending It

Add scenario 11:

```python
# In test_real_user_sim.py
async def scenario_11_my_test(self) -> None:
    """Test something new."""
    result = await self._call_tool("tool_name", param="value")
    # Log it
    await self._log_scenario(
        scenario_num=11,
        name="My test",
        description="What I tested",
        steps=[...],
        quality_score=7.0,
        errors=[]
    )

# In run_all_scenarios():
await self.scenario_11_my_test()
```

## Troubleshooting

### Server won't start
```bash
ssh hetzner "cd /opt/loom && python -m loom.server"
```

### Tools timing out
```bash
# Increase timeout in script
timeout=120.0  # Change from 60.0
```

### Need to debug one scenario
Edit script, comment out others:
```python
# Only run scenario 5
await self.scenario_5_osint_investigation()
# await self.scenario_1_first_time_exploration()
```

## Files

| File | Purpose |
|------|---------|
| `test_real_user_sim.py` | Main test script (1094 lines) |
| `TEST_REAL_USER_SIM_README.md` | Full documentation |
| `REAL_USER_SIM_QUICKSTART.md` | This file |
| `/opt/research-toolbox/real_user_sim_report.json` | Results (generated) |

## Timeline

- **Run time:** 2-5 minutes total
- **Scenario 1:** 30 seconds
- **Scenario 10:** 60 seconds (slowest)
- **Report generation:** 5 seconds

## Next Steps After Running

1. ✓ Read the report
2. ✓ Note quality scores and error patterns
3. ✓ Fix high-impact issues from recommendations
4. ✓ Re-run test to measure improvement
5. ✓ Compare results across Claude/Gemini/Kimi
