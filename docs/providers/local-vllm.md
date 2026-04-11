# Local vLLM (Optional) — Run LLMs Locally

Run a local vLLM server for free, unlimited LLM inference using open-source models. Useful for cost-conscious, privacy-focused, or fully offline setups.

## When to Use Local vLLM

- **Cost control** — No per-token charges (after initial hardware investment)
- **Privacy** — All data stays on your infrastructure
- **Offline capability** — No internet required (except to download models initially)
- **Unlimited usage** — No rate limits or quotas
- **Custom models** — Use any Hugging Face model

## Prerequisites

- GPU with 8GB+ VRAM (16GB+ recommended)
- vLLM installed: `pip install vllm`
- A model (e.g., Llama, Mistral, Qwen)

## Start a Local vLLM Server

Install vLLM:

```bash
pip install vllm
```

Start the server with a model:

```bash
# Using Mistral 7B (recommended; ~7GB VRAM)
python -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.1 \
  --port 8000 \
  --tensor-parallel-size 1

# Or use Llama 2 7B
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --port 8000

# Or use a smaller model (3GB VRAM)
python -m vllm.entrypoints.openai.api_server \
  --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --port 8000
```

The server listens on `http://localhost:8000/v1` (OpenAI-compatible API).

## Configure Loom for Local vLLM

Set environment variables:

```bash
export VLLM_LOCAL_URL="http://localhost:8000/v1"
export VLLM_LOCAL_MODEL="mistral-7b"  # Model name from the vLLM server
```

Or in `.env`:

```bash
VLLM_LOCAL_URL=http://localhost:8000/v1
VLLM_LOCAL_MODEL=mistral-7b
```

## Usage Examples

### Force Local vLLM

```python
result = research_llm_summarize(
    text="...",
    provider_override="vllm"
)
```

### Explicit Model Selection

```python
result = research_llm_summarize(
    text="...",
    model="vllm/mistral-7b"
)
```

### In Provider Cascade

Once configured, vLLM becomes the last fallback:

```bash
# Default cascade: NIM → OpenAI → Anthropic → vLLM
result = research_llm_summarize(text="...")
```

## Model Selection

Recommended open-source models:

| Model | Size | VRAM | Speed | Quality |
|-------|------|------|-------|---------|
| Mistral 7B | 7B | 7-10GB | Very Fast | Good |
| Llama 2 7B | 7B | 7-10GB | Very Fast | Good |
| Llama 2 13B | 13B | 14-16GB | Fast | Very Good |
| Qwen 7B | 7B | 7-10GB | Very Fast | Good |
| Phi 3 | 3.8B | 4-6GB | Very Fast | Fair |
| TinyLlama 1.1B | 1.1B | 2-3GB | Very Fast | Poor |

Download a model (first run only):

```bash
# vLLM auto-downloads from Hugging Face
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --port 8000
# Downloads ~13GB; takes 5-10 minutes
```

## Performance Tips

### Use GPU

vLLM requires GPU. Check GPU usage:

```bash
nvidia-smi
# Should show GPU memory usage
```

If no GPU:

```python
# Fall back to OpenAI instead
result = research_llm_summarize(
    text="...",
    provider_override="openai"
)
```

### Quantization (Save VRAM)

Run a quantized model to save memory:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.1 \
  --quantization awq \  # Reduces VRAM by 50%
  --port 8000
```

### Batch Requests

vLLM is optimized for batch inference:

```python
# Process many texts efficiently
texts = ["text1", "text2", "text3", ...]
for text in texts:
    result = research_llm_summarize(
        text=text,
        provider_override="vllm"
    )
```

## Running in Docker

Create a Dockerfile:

```dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3.11 python3-pip
RUN pip install vllm

EXPOSE 8000

ENTRYPOINT ["python", "-m", "vllm.entrypoints.openai.api_server"]
CMD ["--model", "mistralai/Mistral-7B-Instruct-v0.1", "--port", "8000"]
```

Build and run:

```bash
docker build -t vllm:latest .
docker run --gpus all -p 8000:8000 vllm:latest
```

## Integration with Loom Docker

Run Loom and vLLM together:

```yaml
version: "3.9"
services:
  vllm:
    image: vllm/vllm:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - vllm-cache:/root/.cache
    environment:
      MODEL_NAME: mistralai/Mistral-7B-Instruct-v0.1
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  loom:
    image: ghcr.io/aadelb/loom:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8787:8787"
    depends_on:
      - vllm
    environment:
      VLLM_LOCAL_URL: "http://vllm:8000/v1"
      VLLM_LOCAL_MODEL: "mistral-7b"
    depends_on:
      - vllm

volumes:
  vllm-cache:
```

## Cost Analysis

Costs (hardware amortized):

| Scenario | Cost per Request | Cost per 1M Tokens |
|----------|-----------------|------------------|
| Local vLLM (GPU amortized) | $0.0000 | $0.00 |
| NVIDIA NIM | $0.0001 | $0.10 |
| OpenAI GPT-5-mini | $0.00015 | $0.15 |

One-time hardware cost: $300-1000 (GPU).

## Troubleshooting

### "CUDA out of memory"

Reduce model size or use quantization:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \  # Smaller model
  --port 8000
```

### "Connection refused"

vLLM server isn't running:

```bash
# Check if it's running
curl http://localhost:8000/v1/models

# Start it if not
python -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.1 \
  --port 8000
```

### "Model not found"

Specify the full Hugging Face model name:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.1 \
  --port 8000
```

### Very slow inference

Check GPU usage:

```bash
nvidia-smi
# If GPU% is low, CPU is bottleneck
# If GPU memory is full, out-of-memory warnings in logs
```

## Advanced: Custom Models

Use any Hugging Face model:

```bash
# Code Llama (good for code)
python -m vllm.entrypoints.openai.api_server \
  --model codellama/CodeLlama-7b-Instruct-hf \
  --port 8000

# Gemma (Google)
python -m vllm.entrypoints.openai.api_server \
  --model google/gemma-7b-it \
  --port 8000

# Qwen (Alibaba, multilingual)
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2-7B-Instruct \
  --port 8000
```

## Related Documentation

- [docs/providers/nvidia-nim.md](nvidia-nim.md) — NVIDIA NIM
- [docs/providers/openai.md](openai.md) — OpenAI
- [docs/providers/anthropic.md](anthropic.md) — Anthropic
- [docs/tools/research_llm.md](../tools/research_llm.md) — LLM tools reference
