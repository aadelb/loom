# Journey Test

The journey test runs a smart end-to-end exercise of all 23 MCP tools in a realistic research sequence, proving the entire pipeline works end-to-end with one command. It simulates a researcher exploring a topic, gathering information, analyzing data, and producing insights using the full MCP toolset.

## Modes

- **Default (mocked)**: uses recorded HTTP fixtures, completes in under 30 seconds, deterministic, CI-safe
- **`--live`**: makes real network calls, takes 2-5 minutes, non-deterministic content
- **`--record`**: live mode plus captures screenshots from stealth tools, writes to `journey-out/screenshots/`

## Running

```bash
loom journey-test
loom journey-test --live --topic "your research topic"
loom journey-test --fixtures tests/fixtures/journey --out ./journey-out
loom journey-test --live --record --out ./journey-release
```

## Output files

- `report.json`: machine-readable JSON with one object per step containing `duration_ms`, `ok`/`fail` status, tool parameters, and results
- `report.md`: human-readable narrative transcript showing the complete research journey with formatted outputs

## Reading the report

Each step in the report shows step number, tool name, parameters, duration in milliseconds, and ok/fail status. The summary section at the top includes:

- `ok_count`: number of successful steps
- `fail_count`: number of failed steps  
- `total_duration_ms`: total journey execution time
- `cache_stats`: cache hit/miss statistics
- `llm_usage`: token counts and costs if any LLM tools were called

## CI integration

- Mocked runs execute on every PR via `.github/workflows/ci.yml` job `journey-mock`
- Live runs execute Mondays at 06:00 UTC via `.github/workflows/journey-live.yml` (cron schedule + workflow_dispatch trigger)
- Failing live runs automatically open a GitHub issue with diagnostic details via `actions/github-script`

## Regenerating fixtures

```bash
loom journey-test --live --capture-fixtures tests/fixtures/journey/
```

This runs a live journey once and records every HTTP response as a fixture, so subsequent mocked runs replay the same data. Use when API responses have changed or to update test data.

## Exit codes

| Code | Meaning |
|------|---------|
| 0    | All steps succeeded |
| 1    | At least one step failed |
| 2    | Server unreachable (live mode only) |
| 3    | Fixtures directory missing (mocked mode only) |

## See also

- [CLI reference](cli.md) - Complete CLI reference
- [Deployment guide](deployment/claude-code-integration.md) - Production deployment guide
- [Journey implementation](../src/loom/journey.py) - Journey test implementation
