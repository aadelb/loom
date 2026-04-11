# Loom Examples

Runnable example scripts demonstrating the Loom MCP server and its 23 research tools. Each script is a complete, standalone example that works with the MCP Python SDK.

## Quick Start

1. **Start the Loom server:**
   ```bash
   loom-server
   # Listens on http://127.0.0.1:8787/mcp
   ```

2. **Run an example:**
   ```bash
   python examples/quickstart.py
   ```

## Examples

| Script | What It Does | Prerequisites | Time |
|--------|-------------|---------------|------|
| **`quickstart.py`** | Minimal MCP client: connect, initialize, list tools, fetch a URL | loom-server running | 30s |
| **`harvest_model_cards.py`** | Generic Hugging Face model card sweep with concurrent spider | loom-server running | 1-2m |
| **`deep_research.py`** | Full research pipeline: search → fetch → summarize → answer with citations | loom-server, `EXA_API_KEY` env var, NVIDIA NIM credentials | 2-5m |
| **`bulk_arxiv.py`** | Daily arXiv crawler: fetch listings, spider abstracts, classify papers into categories | loom-server, NVIDIA NIM credentials | 3-10m |
| **`cloudflare_bypass.py`** | Demonstrates stealth escalation: HTTP fetch → Camoufox stealth browser | loom-server running | 30-60s |
| **`session_login.py`** | Persistent browser sessions: open, reuse across requests, close | loom-server running | 30s |
| **`config_tuning.py`** | Runtime configuration: adjust concurrency, timeouts without server restart | loom-server running | 30s |
| **`llm_translate.py`** | LLM-powered translation to arbitrary languages | loom-server, NVIDIA NIM credentials | 10-30s |

## Prerequisites

### System Requirements
- Python 3.11+
- Loom server running (see [docs/installation.md](../docs/installation.md))

### Environment Variables
Set these for examples that need them:

```bash
# For research_search (Exa provider)
export EXA_API_KEY="your-exa-api-key"

# For NVIDIA NIM LLM tools (research_llm_*)
export NVIDIA_API_KEY="your-nvidia-api-key"
export NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
# OR for local vLLM instance
export VLLM_BASE_URL="http://localhost:8000/v1"

# Optional: OpenAI fallback (if NIM unavailable)
export OPENAI_API_KEY="your-openai-key"
```

### Install Dependencies
```bash
# Install Loom from the repo
cd ..
pip install -e .

# Or install from PyPI (when released)
pip install loom-research
```

## Running Examples

### Minimal (no env vars required)
```bash
python examples/quickstart.py
python examples/cloudflare_bypass.py
python examples/session_login.py
python examples/config_tuning.py
```

### With environment variables
```bash
# Harvest Hugging Face models
python examples/harvest_model_cards.py

# Deep research with search + LLM synthesis
EXA_API_KEY=xxx NVIDIA_API_KEY=yyy python examples/deep_research.py \
  --query "latest advances in transformer efficiency"

# arXiv crawler with classification
NVIDIA_API_KEY=xxx python examples/bulk_arxiv.py --category cs.CL --days 1

# Translation demo
NVIDIA_API_KEY=xxx python examples/llm_translate.py \
  --text "Hello, world!" --to es
```

## Output

Examples write results to local directories:
- `quickstart.py` — prints to stdout
- `harvest_model_cards.py` — writes to `./harvest-out/*.json`
- `deep_research.py` — writes to `./deep-out/<timestamp>.md`
- `bulk_arxiv.py` — writes to `./arxiv-out/<date>.csv`
- `cloudflare_bypass.py` — prints to stdout
- `session_login.py` — prints to stdout
- `config_tuning.py` — prints to stdout
- `llm_translate.py` — prints to stdout

## Customization

All examples use `argparse` for CLI flags. Pass `--help` to see options:

```bash
python examples/harvest_model_cards.py --help
python examples/deep_research.py --help
python examples/bulk_arxiv.py --help
python examples/llm_translate.py --help
```

## Troubleshooting

### "Connection refused"
Loom server is not running. Start it:
```bash
loom-server
```

### "EXA_API_KEY not set"
Set the environment variable:
```bash
export EXA_API_KEY="sk-..."
```

### "NVIDIA_API_KEY not set"
For examples using LLM tools (deep_research, bulk_arxiv, llm_translate), set:
```bash
export NVIDIA_API_KEY="nvapi-..."
```

Or use local vLLM:
```bash
export VLLM_BASE_URL="http://localhost:8000/v1"
```

### Parse errors in JSON responses
Some tools return plain text instead of JSON. Examples gracefully handle this with try/except blocks.

### Rate limiting on external APIs
If you get 429 errors, reduce concurrency:
```python
# In spider calls
"concurrency": 2  # instead of 5
```

## Tool Reference

See [../docs/tools/](../docs/tools/) for detailed documentation on each MCP tool:
- `research_fetch` — HTTP fetch with SSRF protection, Cloudflare solving, caching
- `research_spider` — Concurrent URL fetching
- `research_markdown` — LLM-ready markdown extraction via Crawl4AI
- `research_search` — Web search (Exa, Tavily providers)
- `research_deep` — Deep research workflow (built-in pipeline)
- `research_github` — GitHub code/repo/issue search
- `research_camoufox` — Stealth browser via Camoufox
- `research_botasaurus` — Stealth crawler via Botasaurus
- `research_llm_*` — LLM tools for summarization, extraction, classification, translation, etc.
- `research_cache_*` — Cache management

## License

Examples are part of the Loom project and are licensed under Apache 2.0. See [../LICENSE](../LICENSE).

## Contributing

To add a new example:
1. Create a new `.py` file in `examples/`
2. Include a module docstring explaining the script
3. Use `argparse` for CLI arguments
4. Handle errors gracefully with try/except
5. Update this README with a table entry

See [../CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.
