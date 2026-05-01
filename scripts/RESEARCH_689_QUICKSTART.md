# Research 689 Quick Start

## One-Liner Execution

### On Hetzner (recommended)
```bash
ssh hetzner "cd /opt/loom && python3 scripts/research_689.py"
```

### Locally (Mac)
```bash
cd /Users/aadel/projects/loom && python3 scripts/research_689.py
```

## What It Does

Researches MCP/Agent tool-use attacks across 3 queries:
1. "MCP tool use attacks agent exploitation 2025 2026"
2. "tool calling injection LLM agent hijacking"
3. "function calling security vulnerabilities AI agents"

Collects ~120 results from 7 search engines, extracts attack patterns, produces JSON report.

## Output

**Location**: `/opt/research-toolbox/tmp/research_689_mcp_attacks.json`

**Size**: ~500KB-2MB (depends on search results)

**Key sections**:
- `queries[]` — Raw search results (40 per query)
- `analysis` — OWASP, tool poisoning, injection, hijacking, AgentDyn findings
- `findings` — Vulnerabilities, attack vectors, defenses, papers, exploits
- `metadata` — Stats (duration, count, errors)

## Verify Output

```bash
# Check file exists and size
ls -lh /opt/research-toolbox/tmp/research_689_mcp_attacks.json

# Validate JSON
python3 -m json.tool /opt/research-toolbox/tmp/research_689_mcp_attacks.json | head -50

# Count key findings
python3 -c "
import json
with open('/opt/research-toolbox/tmp/research_689_mcp_attacks.json') as f:
    data = json.load(f)
print(f'Total results: {data[\"metadata\"][\"total_results\"]}')
print(f'Unique sources: {data[\"metadata\"][\"unique_sources\"]}')
print(f'Duration: {data[\"metadata\"][\"research_duration_seconds\"]:.1f}s')
print(f'OWASP patterns: {len(data[\"analysis\"][\"owasp_agentic_ai_top_10\"])}')
print(f'Vulnerabilities: {len(data[\"findings\"][\"critical_vulnerabilities\"])}')
"
```

## Expected Duration

- **Hetzner**: 30-45 seconds (parallel search, good networking)
- **Mac local**: 45-90 seconds (slower than Hetzner)
- **Network timeout**: 15 seconds per search engine (handles failures gracefully)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Import errors | Ensure `/opt/loom/src` or `/Users/.../loom/src` in PYTHONPATH |
| No output file | Check for exceptions in console output |
| Timeout errors | Run on Hetzner instead of local |
| Incomplete JSON | Check `metadata.error` field for details |

## Files Reference

- Script: `/Users/aadel/projects/loom/scripts/research_689.py`
- Docs: `/Users/aadel/projects/loom/RESEARCH_689.md` (full details)
- Deploy helper: `/tmp/research_689_deploy.sh` (if needed)

## Integration

To integrate results into UMMRO compliance analysis:

```python
import json

with open('/opt/research-toolbox/tmp/research_689_mcp_attacks.json') as f:
    research = json.load(f)

# Extract OWASP patterns for Article 15 checklist
for pattern in research['analysis']['owasp_agentic_ai_top_10']:
    print(f"- {pattern['pattern']}: {pattern['impact']}")

# Extract vulnerabilities for risk assessment
for vuln in research['findings']['critical_vulnerabilities'][:5]:
    print(f"- {vuln['name']}")
```

---

**Author**: Ahmed Adel Bakr Alderai | **Status**: Ready | **Last Updated**: 2025-05-01
