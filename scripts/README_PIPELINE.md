# Full Tool Pipeline Script

Comprehensive demonstration of all 10 major Loom tool categories in a single research workflow.

## Overview

The `full_tool_pipeline.py` script executes a complete research cycle on the query: **"AI safety testing market 2026"**

It demonstrates:

1. **Multi-search** (research_multi_search) - Parallel search across 20+ engines
2. **Deep research** (research_deep) - Full 12-stage pipeline with query expansion, fetching, extraction, ranking
3. **LLM synthesis** (research_llm_summarize) - Synthesize findings into concise summary
4. **Career trajectory** (research_market_velocity) - Market velocity analysis
5. **Company intel** (research_company_intel) - Competitor/vendor analysis
6. **Knowledge graph** (research_knowledge_graph) - Entity extraction and relationships
7. **Fact checker** (research_fact_check) - Claim verification
8. **HCS scoring** (research_hcs_score) - Output quality assessment (academic/technical rubric)
9. **Prompt reframe** (research_prompt_reframe) - Compliance reframing and formatting
10. **AI safety** (research_safety_filter_map) - Safety validation and filter detection

## Architecture

```
┌─ Query ────────────────────────────────┐
│  "AI safety testing market 2026"       │
└─────────────────────────────────────────┘
         │
         ├──> [Stage 1] Multi-Search ──────────────┐
         │     (20+ search engines)                │
         │                                         │
         ├──> [Stage 2] Deep Research ────────────┤──> [Stage 3] LLM Synthesis ─┐
         │     (12-stage pipeline)                │  (Summarization + Extraction) │
         │                                        │                            │
         ├──────────────────────────────────────────────────────────────────────┤
         │                                                                      │
         ├──> [Stage 4] Career Trajectory ──────────────────────────────────────┤
         │     (Market velocity)                                               │
         │                                                                      │
         ├──> [Stage 5] Company Intel ────────────────────────────────────────┤
         │     (Competitor analysis)                                          │
         │                                                                    │
         └─────────────────────────────────────────────────────────────────────┤
                    [Synthesis output feeds into downstream stages]
                                      │
                   ┌──────────────────┼──────────────────┐
                   │                  │                  │
         [Stage 6] Knowledge Graph  [Stage 7] Fact Check [Stage 8] HCS Scoring
         (Entity extraction)       (Claim verification) (Quality metrics)
                   │                  │                  │
                   └──────────────────┼──────────────────┘
                                      │
                ┌─────────────────────┼────────────────────┐
                │                     │                    │
         [Stage 9] Prompt Reframe  [Stage 10] AI Safety Check
         (Compliance/formatting)  (Safety validation)
                │                     │
                └─────────────────────┴──────────────────┐
                                                         │
                        ┌──────────────────────────────────┘
                        │
                   [Output JSON]
                   - Full synthesis
                   - Quality scores
                   - Safety assessment
                   - Entity graph
                   - Timing + statistics
```

## Output

Results saved to: `/tmp/loom-pipeline/full_pipeline_result.json` (local) or `/opt/research-toolbox/tmp/full_pipeline_result.json` (Hetzner)

### JSON Structure

```json
{
  "query": "AI safety testing market 2026",
  "started_at": "2026-05-01T...",
  "completed_at": "2026-05-01T...",
  "total_elapsed_secs": 45.2,
  "tools_invoked": 10,
  "tools_succeeded": 9,
  "tools_failed": 0,
  "invocations": [
    {
      "tool_name": "research_multi_search",
      "status": "success",
      "elapsed_secs": 3.45,
      "input_size": 29,
      "output_size": 15234
    }
  ],
  "multi_search_results": { ... },
  "deep_research_results": { ... },
  "llm_synthesis": { ... },
  "career_velocity": { ... },
  "company_analysis": { ... },
  "entity_graph": { ... },
  "fact_checks": { ... },
  "quality_score": { ... },
  "reframed_content": { ... },
  "safety_check": { ... }
}
```

## Usage

### Local (Mac/Linux)

```bash
cd /Users/aadel/projects/loom
python3 scripts/full_tool_pipeline.py
```

Requires:
- Python 3.11+
- MCP server running on `http://127.0.0.1:8787/mcp`
- Credentials in `~/.claude/resources.env`

Output: `/tmp/loom-pipeline/full_pipeline_result.json`

### Remote (Hetzner)

```bash
ssh hetzner
cd /opt/research-toolbox
python3 scripts/full_tool_pipeline.py
```

Output: `/opt/research-toolbox/tmp/full_pipeline_result.json`

## Environment

### Required Environment Variables

```bash
# MCP Server
LOOM_MCP_SERVER=http://127.0.0.1:8787/mcp    # Default if not set

# LLM Provider (any of: GROQ, NVIDIA_NIM, DEEPSEEK, GOOGLE_AI, MOONSHOT, OPENAI, ANTHROPIC)
GROQ_API_KEY=...                               # Fallback cascade: groq -> nvidia_nim -> deepseek

# Search Providers (optional, auto-detected from config)
EXA_API_KEY=...
TAVILY_API_KEY=...
BRAVE_API_KEY=...
```

Load from `~/.claude/resources.env`:
```bash
load_dotenv(Path.home() / ".claude" / "resources.env")
```

## Execution Flow

### Sequential Stages

1. **Stage 1-2 (Parallel):** Multi-search + Deep research both query the web simultaneously
   - Multi-search: Quick parallel across 20+ engines
   - Deep research: Full 12-stage orchestration

2. **Stage 3 (Synthesis):** Depends on Stages 1-2 outputs
   - Summarizes findings
   - Extracts key information

3. **Stages 4-5 (Parallel):** Market analysis
   - Career trajectory: Job market velocity
   - Company intel: Competitor analysis

4. **Stages 6-7 (Parallel):** Knowledge extraction
   - Knowledge graph: Entity extraction from synthesis
   - Fact checker: Verify claims from deep research

5. **Stage 8:** Quality scoring
   - Depends on synthesis output
   - HCS-10 academic/technical rubric

6. **Stages 9-10 (Parallel):** Downstream processing
   - Prompt reframe: Compliance formatting
   - AI safety check: Filter detection

All stages are tracked for:
- Execution time
- Input/output sizes  
- Success/failure status
- Error messages

## Metrics

The script outputs a summary showing:

```
======================================================================
FULL TOOL PIPELINE EXECUTION SUMMARY
======================================================================
Query: AI safety testing market 2026
Total Tools: 10
  Succeeded: 9
  Failed: 1
  Skipped: 0
Elapsed: 45.23s

Tool Execution Times:
  ✓ research_multi_search               3.45s (29 in, 15234 out)
  ✓ research_deep                      15.67s (29 in, 87654 out)
  ✓ research_llm_summarize              2.34s (2000 in, 1234 out)
  ✓ research_market_velocity            4.12s (29 in, 5678 out)
  ✓ research_company_intel              3.89s (29 in, 8901 out)
  ✓ research_knowledge_graph            1.23s (3000 in, 4567 out)
  ✓ research_fact_check                 2.56s (45 in, 3456 out)
  ✓ research_hcs_score                  1.45s (1234 in, 890 out)
  ✓ research_prompt_reframe             2.12s (1234 in, 2345 out)
  ✓ research_safety_filter_map          0.98s (1234 in, 567 out)

Output: /tmp/loom-pipeline/full_pipeline_result.json
======================================================================
```

## Extending the Pipeline

To add another tool:

1. Create a new `async def run_[tool_name]()` function
2. Call the tool via `await call_mcp_tool()`
3. Track invocation in `invocations` list
4. Add to `PipelineResult` dataclass
5. Call from `run_pipeline()`

Example:

```python
async def run_new_tool(query: str, invocations: list[ToolInvocation]) -> dict[str, Any] | None:
    """Stage N: Description."""
    logger.info("=== Stage N: Tool Name ===")
    tool_name = "research_tool_name"
    start = time.time()
    
    result, error = await call_mcp_tool(tool_name, {"param": "value"})
    
    elapsed = time.time() - start
    invocations.append(
        ToolInvocation(
            tool_name=tool_name,
            status="success" if result else "error",
            elapsed_secs=elapsed,
            input_size=10,
            output_size=len(json.dumps(result)) if result else 0,
            error_message=error,
        )
    )
    return result
```

## Error Handling

- Tools that fail (status="error") are logged with error messages
- Tools that skip (status="skipped") are counted separately
- Pipeline completes even if some tools fail
- All failures reported in JSON output under `invocations[]`

## Performance

Typical execution times per tool:
- Multi-search: 2-5s
- Deep research: 15-45s (depends on search results)
- LLM synthesis: 1-3s
- Career trajectory: 3-6s
- Company intel: 2-5s
- Knowledge graph: 1-2s
- Fact checker: 1-4s
- HCS scoring: 1-2s
- Prompt reframe: 1-3s
- AI safety: <1s

**Total: 30-75s depending on search result volume and LLM availability**

## Dependencies

```
mcp >= 0.1.0
python-dotenv >= 1.0.0
httpx >= 0.24.0
pydantic >= 2.0.0
```

## Logs

All operations logged to stdout with timestamps and levels:
```
2026-05-01 17:56:37,959 [INFO] full_tool_pipeline: Starting full pipeline for: AI safety testing market 2026
2026-05-01 17:56:38,280 [INFO] full_tool_pipeline: === Stage 1: Multi-Search ===
2026-05-01 17:56:38,450 [INFO] full_tool_pipeline: Multi-search found 58 sources
...
```

Set log level in script: `logging.basicConfig(level=logging.DEBUG)` for verbose output.

## Notes

- Script is fully async and can be extended for concurrent stage execution
- MCP server must be running and accessible
- All credentials loaded from `~/.claude/resources.env`
- Output auto-detects environment (Hetzner vs local Mac)
- Results are immutable (new dicts created, not mutations)
- All tool results are preserved for downstream analysis
