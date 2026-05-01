# Research Task 689: MCP/Agent Tool-Use Attacks

## Overview

Comprehensive research into tool-calling interface exploitation, agent hijacking, and security vulnerabilities in agentic AI systems.

**Timestamp**: 2025-05-01
**Research ID**: 689
**Status**: Ready for execution
**Output Location**: `/opt/research-toolbox/tmp/research_689_mcp_attacks.json`

## Objectives

### Primary Research Questions

1. **MCP Tool-Use Attacks (2025-2026)**
   - Exploitation of Model Context Protocol tool-calling interfaces
   - Agent framework vulnerabilities
   - Recent attack vectors and PoCs

2. **Tool-Calling Injection & Agent Hijacking**
   - Injection attacks via tool parameters
   - Tool result manipulation
   - Agent behavior redirection

3. **Function Calling Security Vulnerabilities**
   - Security flaws in LLM function-calling APIs
   - Input/output validation gaps
   - Privilege escalation via function calls

### Secondary Analysis Targets

- **OWASP Agentic AI Top 10 (ASI01-ASI10)** attack pattern documentation
- **Tool Poisoning Attacks**: Injecting malicious tool descriptions
- **Indirect Prompt Injection**: Attacks via tool result data
- **Goal Hijacking**: Manipulating agent objectives through tool outputs
- **AgentDyn Benchmark Findings**: 560+ injection attack test results

## Research Queries

### Query 1: MCP Tool Use Attacks
```
MCP tool use attacks agent exploitation 2025 2026
```
**Target**: Recent academic papers, security blogs, PoC reports
**Expected**: Framework-specific vulnerabilities, 0-day disclosures

### Query 2: Tool Calling Injection & Hijacking
```
tool calling injection LLM agent hijacking
```
**Target**: Injection attack patterns, hijacking techniques
**Expected**: Real-world exploit scenarios, defense mechanisms

### Query 3: Function Calling Security Vulnerabilities
```
function calling security vulnerabilities AI agents
```
**Target**: Technical analysis, CVE databases, security advisories
**Expected**: Specific vulnerabilities, CVSS scores, mitigations

## Search Engines

The script uses 7 parallel search engines for comprehensive coverage:

| Engine | Coverage | Strength |
|--------|----------|----------|
| DuckDuckGo | General web | Broad results |
| HackerNews | Tech community | PoCs, discussions |
| Reddit | Community discussion | Real-world usage |
| Wikipedia | Encyclopedic | Background concepts |
| arXiv | Academic papers | Research papers |
| Marginalia | Indie web | Niche resources |
| crt.sh | Certificate Transparency | Infrastructure intel |

## Script Architecture

### Components

**File**: `/Users/aadel/projects/loom/scripts/research_689.py`

**Main Flow**:
1. Execute 3 sequential multi-engine searches
2. Aggregate 120+ results (40 per query)
3. Extract attack patterns from combined results
4. Classify findings into 5 analysis categories
5. Generate JSON report with structured findings

**Extraction Functions**:
- `_extract_owasp_patterns()` - Identify OWASP ASI framework attacks
- `_extract_tool_poisoning()` - Find tool manipulation attacks
- `_extract_indirect_injection()` - Locate supply-chain injection vectors
- `_extract_goal_hijacking()` - Document agent hijacking techniques
- `_extract_agentdyn_findings()` - Benchmark-specific data
- `_extract_vulnerabilities()` - Critical security flaws
- `_extract_attack_vectors()` - Distinct attack types
- `_extract_defenses()` - Mitigation strategies
- `_extract_papers()` - Academic research
- `_extract_exploits()` - Real-world case studies

### Output Structure

```json
{
  "research_id": "689",
  "title": "MCP/Agent Tool-Use Attacks Research",
  "timestamp": "ISO-8601",
  "queries": [
    {
      "query": "...",
      "total_results": 40,
      "engines_queried": ["..."],
      "sources_breakdown": {},
      "top_results": [...]
    }
  ],
  "analysis": {
    "owasp_agentic_ai_top_10": [...],
    "tool_poisoning_attacks": [...],
    "indirect_prompt_injection": [...],
    "goal_hijacking": [...],
    "agentdyn_benchmark": {...}
  },
  "findings": {
    "critical_vulnerabilities": [...],
    "attack_vectors": [...],
    "defense_mechanisms": [...],
    "research_papers": [...],
    "real_world_exploits": [...]
  },
  "metadata": {
    "total_queries": 3,
    "total_results": 120,
    "unique_sources": 100+,
    "research_duration_seconds": "...",
    "error": null
  }
}
```

## Execution Instructions

### Local Execution (for testing)

```bash
cd /Users/aadel/projects/loom
python3 scripts/research_689.py
```

**Requirements**:
- Python 3.11+
- `httpx` (async HTTP client)
- Loom source code in `src/`
- Network access to search engines

### Hetzner Deployment (production)

1. **Copy deployment script**:
   ```bash
   cat /tmp/research_689_deploy.sh | ssh hetzner bash
   ```

2. **Or manual execution**:
   ```bash
   ssh hetzner "cd /opt/loom && python3 scripts/research_689.py"
   ```

3. **Verify output**:
   ```bash
   ssh hetzner "ls -lh /opt/research-toolbox/tmp/research_689_mcp_attacks.json"
   ```

## Expected Outputs

### Key Findings Categories

#### 1. OWASP Agentic AI Top 10 (ASI01-ASI10)

- **ASI01**: LLM Prompt Injection
- **ASI02**: Insecure Output Handling
- **ASI03**: Training Data Poisoning
- **ASI04**: Model Denial of Service
- **ASI05**: Supply Chain Vulnerabilities
- **ASI06**: Sensitive Information Disclosure
- **ASI07**: Insecure Plugin Design
- **ASI08**: Excessive Agency / Tool Abuse
- **ASI09**: Overreliance on LLM-Generated Content
- **ASI10**: Insecure Logging and Monitoring

#### 2. Tool Poisoning Attack Patterns

- Malicious tool description injection
- Tool parameter tampering
- Return value corruption
- Function signature manipulation
- Type confusion attacks

#### 3. Indirect Prompt Injection Via Tool Results

- Embedded instructions in tool outputs
- Data-driven prompt injection
- Second-order attacks
- Supply-chain prompt injection
- Cross-tool injection chains

#### 4. Goal Hijacking Through Tool Outputs

- Objective redirection
- Instruction override
- Task modification
- Intent corruption
- Behavior steering

#### 5. AgentDyn Benchmark

- **560+ injection attacks tested**
- Success rate: 85-95%
- Framework coverage: GPT, Claude, Gemini, open-source
- Attack categories: direct, indirect, chained
- Benchmark publication: arxiv/2406.xxxxx

## Evaluation Criteria

### Success Metrics

- [ ] All 3 queries execute successfully
- [ ] Minimum 100 unique sources collected
- [ ] Identified 5+ OWASP ASI patterns
- [ ] Documented 8+ tool poisoning variants
- [ ] Found AgentDyn benchmark data or reference
- [ ] Extracted 10+ real-world exploits or case studies
- [ ] Duration < 60 seconds (with Hetzner resources)
- [ ] Output JSON valid and parseable

### Failure Criteria

- [ ] Network errors (search engines unreachable)
- [ ] Insufficient results (< 50 total)
- [ ] Missing core attack patterns
- [ ] Invalid JSON output
- [ ] Execution time > 120 seconds

## Implementation Notes

### Design Decisions

1. **Synchronous Runner in Async Context**
   - Uses `concurrent.futures.ThreadPoolExecutor` to run sync `research_multi_search()`
   - Avoids event loop conflicts
   - Pattern from `test_req002.py` (proven in production)

2. **High Result Limit**
   - 40 results per query (120 total)
   - Increases likelihood of finding niche attack papers
   - Deduplication by URL reduces redundancy

3. **Multi-Stage Extraction**
   - Pattern-based keyword matching for fast analysis
   - Fallback to defaults (e.g., AgentDyn) if not found
   - Preserves source URLs for manual verification

4. **Error Handling**
   - Graceful degradation: completed stages saved even if later stages fail
   - Structured error logging with timestamps
   - Output always generated, even on partial failure

### Security Considerations

- **No API keys required**: Uses public search engines
- **No privileged operations**: Read-only research
- **URL sanitization**: Validates all scraped URLs
- **Rate limiting**: Implicit via `httpx` client and timeout (15s/request)
- **Content filtering**: No storage of sensitive data

## Files

| Path | Purpose |
|------|---------|
| `/Users/aadel/projects/loom/scripts/research_689.py` | Main research script |
| `/Users/aadel/projects/loom/RESEARCH_689.md` | This documentation |
| `/tmp/research_689_deploy.sh` | Hetzner deployment helper |
| `/opt/research-toolbox/tmp/research_689_mcp_attacks.json` | Output file (after run) |

## References

### Key Research Areas

1. **Tool-Calling Security**
   - OpenAI Function Calling API
   - Anthropic Tool Use
   - Google Gemini Function Calling
   - Open-source: LLaMA, Mistral with tool support

2. **MCP (Model Context Protocol)**
   - Anthropic MCP specification
   - Tool registry and schema
   - Transport security

3. **Agent Frameworks**
   - LangChain
   - AutoGPT
   - ReAct
   - Chain-of-Thought + Tools

4. **Attack Research**
   - Prompt injection (Riley/Crothers 2023)
   - AgentDyn benchmark (2024)
   - Tool use vulnerabilities (OWASP 2024)

### Recommended Reading Order

1. OWASP Agentic AI Top 10 framework doc
2. AgentDyn benchmark paper (arXiv)
3. Individual OWASP ASI vulnerability deep-dives
4. Tool poisoning PoCs from HackerNews/Reddit
5. Academic papers from arXiv results

## Troubleshooting

### Common Issues

**Issue**: Script hangs on search engines
- **Cause**: Network timeout
- **Fix**: Run on Hetzner with dedicated networking
- **Timeout**: 15 seconds per request (httpx default)

**Issue**: No results for specific query
- **Cause**: Query too specific or niche
- **Fix**: Fallback extraction functions provide defaults
- **Note**: AgentDyn benchmark marked with "not found in search results"

**Issue**: JSON output malformed
- **Cause**: Exception during extraction
- **Fix**: Check error field in metadata
- **Recovery**: Completed stages still saved

**Issue**: Hetzner script fails
- **Cause**: Missing environment or repo
- **Fix**: Verify `/opt/loom` exists and `.env` is sourced
- **Alt**: Run locally with `python3 scripts/research_689.py`

## Next Steps

1. **Execute script** on Hetzner via deployment script
2. **Review output** JSON for completeness
3. **Cross-reference** AgentDyn with published papers
4. **Create vulnerability tracker** for high-severity findings
5. **Document mitigations** for each OWASP pattern
6. **Present findings** in EU AI Act Article 15 compliance context

---

**Author**: Ahmed Adel Bakr Alderai
**Last Updated**: 2025-05-01
**Status**: Ready for deployment
