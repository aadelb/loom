# Community 3: LLM Provider Abstraction

**Modules:** `providers/base.py`, `providers/anthropic_provider.py`, `providers/openai_provider.py`, `providers/nvidia_nim.py`, `providers/vllm_local.py`, `tools/llm.py`

## Purpose

This community abstracts multi-backend LLM support, enabling Loom to dispatch research queries and content to Anthropic Claude, OpenAI, NVIDIA NIM-hosted models (Kimi, Llama, Mistral, Qwen), and local vLLM instances. Includes cost tracking and provider selection logic.

## Key Classes & Functions

### `providers/base.py`
- **`LLMProvider`** (abstract) — Interface for all LLM backends
  - `complete(prompt, **kwargs)` → `LLMResponse`
  - `supports_streaming()`, `get_model_name()`
- **`LLMResponse`** — Structured output (text, tokens, cost, model, timestamp)

### `providers/anthropic_provider.py`
- **`AnthropicProvider`** — Dispatches to Anthropic API
- Handles message formatting, streaming, cost calculation via token counts

### `providers/openai_provider.py`
- **`OpenAIProvider`** — Dispatches to OpenAI API (gpt-4o, gpt-4-turbo, etc.)
- Chat completions, token counting, parallel requests

### `providers/nvidia_nim.py`
- **`NvidiaNimProvider`** — NVIDIA NIM inference server (Kimi K2, Llama 4, Mistral Large 3, Qwen 3.5)
- Enterprise inference endpoint, cost tracking

### `providers/vllm_local.py`
- **`VllmLocalProvider`** — Local vLLM instance (for on-machine inference)
- Minimal latency, no token metering

### `tools/llm.py`
- **`CostTracker`** — Aggregates cost across provider calls ($/token × calls)
- Used by all tools that invoke LLMs (markdown, search, deep)

## Data Flow

1. Tool (e.g., `tools/search.py`) needs LLM analysis
2. Instantiates provider (from `LOOM_LLM_PROVIDER` env var)
3. Calls `provider.complete(prompt, **kwargs)`
4. `LLMResponse` returned with text, tokens, cost, model name
5. `CostTracker` updates aggregated cost
6. Result used by tool (e.g., filtering search results, reranking)

## Dependencies

- **Inbound:** Called by research tools (fetch, search, markdown, deep)
- **Outbound:** → API endpoints (Anthropic, OpenAI, NVIDIA NIM) or local vLLM
- **Key edges:** ← all tools, ← config.py (API key env vars)

## Module Paths

- `src/loom/providers/base.py` (80 LOC)
- `src/loom/providers/anthropic_provider.py` (120 LOC)
- `src/loom/providers/openai_provider.py` (140 LOC)
- `src/loom/providers/nvidia_nim.py` (150 LOC)
- `src/loom/providers/vllm_local.py` (100 LOC)
- `src/loom/tools/llm.py` (60 LOC)
