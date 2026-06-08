# Resource Inventory (verified live 2026-06-08)

## Abliterated models (Ollama @ Hetzner, CPU-only, no GPU) — safety REMOVED
| Tier | Model | Size | ~CPU throughput |
|------|-------|------|-----------------|
| max  | qwen35-35b-abliterated | 21.2GB | ~5.5 tok/s warm (Q4) |
| deep | qwen3-coder-30b-abliterated | 18.6GB | ~2 tok/s |
| mid  | qwen35-9b-abliterated | 5.6GB | ~4.5 tok/s |
| fast | mannix/llama3.1-8b-abliterated | 4.7GB | ~6.2 tok/s |
| —    | gemma3n-8b-abliterated | 4.2GB | — |
| —    | qwen3.5-abliterated | 2.7GB | smallest/fastest |

## CLIs (Mac) — verified present
- kimi  (--thinking --yolo; native api.kimi.com 262K + NIM fallbacks nvidia-kimi/nvidia-deepseek/nvidia-qwen3)
- gemini (gemini-3.1-pro-preview; 5 Ultra accounts 91/21/adel/26/asu; 1M ctx; retry cascade)
- codex (gpt-5.2-codex)
- DeepSeek (API deepseek-reasoner)

## LLM providers in Loom (8 + local)
groq(×5 keys), nvidia_nim(×2), deepseek, moonshot/kimi, gemini, openai, anthropic, ollama(abliterated). vllm=DEAD.

## Safety-gradient ladder (the architecture)
- L0 (none): abliterated 35b/30b/9b — raw uncensored seed
- L1 (mid): Kimi/moonshot, DeepSeek direct, NVIDIA NIM — quality + light compliance
- L2 (high/flagship): Claude Opus(anthropic), GPT(openai), Gemini — best quality, strongest refusal

## Infra
Hetzner Ryzen 5950X 32-thread / 125GB / NO GPU. Qdrant 37M vectors. 957 reframe strategies. Loom 1037 tools. Hermes agent (1036 Loom tools bridged).
