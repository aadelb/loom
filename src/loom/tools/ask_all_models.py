"""Universal AI query tool — ask ALL available LLM providers, APIs, and CLIs simultaneously.

Sends a prompt to 20+ models across 7 providers + 3 CLIs in parallel.
Auto-reframes refused prompts using the prompt-reframe engine.

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import time
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.ask_all_models")

# All available models grouped by provider
_API_MODELS: dict[str, list[dict[str, str]]] = {
    "groq": [
        {"id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B (Groq)", "cost": "$0/FREE"},
        {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B", "cost": "$0.59/$0.79 per 1M"},
        {
            "id": "meta-llama/llama-4-scout-17b-16e-instruct",
            "name": "Llama 4 Scout",
            "cost": "$0.11/$0.34 per 1M",
        },
        {"id": "qwen/qwen3-32b", "name": "Qwen3 32B", "cost": "$0.39/$0.59 per 1M"},
        {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B", "cost": "$0.05/$0.08 per 1M"},
    ],
    "nvidia": [
        {
            "id": "mistralai/mistral-large-3-675b-instruct-2512",
            "name": "Mistral Large 3 675B",
            "cost": "$0/FREE",
        },
        {
            "id": "qwen/qwen3-coder-480b-a35b-instruct",
            "name": "Qwen3 Coder 480B",
            "cost": "$0/FREE",
        },
        {"id": "qwen/qwen3.5-397b-a17b", "name": "Qwen 3.5 397B", "cost": "$0/FREE"},
        {"id": "nvidia/nemotron-4-340b-instruct", "name": "Nemotron 4 340B", "cost": "$0/FREE"},
        {
            "id": "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            "name": "Nemotron Ultra 253B",
            "cost": "$0/FREE",
        },
        {"id": "meta/llama-3.1-405b-instruct", "name": "Llama 3.1 405B", "cost": "$0/FREE"},
        {"id": "moonshotai/kimi-k2.5", "name": "Kimi K2.5", "cost": "$0/FREE"},
        {"id": "moonshotai/kimi-k2-thinking", "name": "Kimi K2 Thinking", "cost": "$0/FREE"},
        {"id": "deepseek-ai/deepseek-v4-pro", "name": "DeepSeek v4 Pro (NIM)", "cost": "$0/FREE"},
        {
            "id": "nvidia/nemotron-3-super-120b-a12b",
            "name": "Nemotron 3 Super 120B",
            "cost": "$0/FREE",
        },
        {
            "id": "mistralai/devstral-2-123b-instruct-2512",
            "name": "Devstral 2 123B",
            "cost": "$0/FREE",
        },
        {"id": "qwen/qwen3.5-122b-a10b", "name": "Qwen 3.5 122B", "cost": "$0/FREE"},
        {
            "id": "mistralai/mistral-small-4-119b-2603",
            "name": "Mistral Small 4 119B",
            "cost": "$0/FREE",
        },
        {"id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B", "cost": "$0/FREE"},
        {
            "id": "nvidia/llama-3.3-nemotron-super-49b-v1",
            "name": "Nemotron Super 49B",
            "cost": "$0/FREE",
        },
        {
            "id": "meta/llama-4-maverick-17b-128e-instruct",
            "name": "Llama 4 Maverick",
            "cost": "$0/FREE",
        },
        {"id": "deepseek-ai/deepseek-v4-flash", "name": "DeepSeek v4 Flash", "cost": "$0/FREE"},
        {"id": "deepseek-ai/deepseek-v3.2", "name": "DeepSeek v3.2", "cost": "$0/FREE"},
        {
            "id": "qwen/qwen3-next-80b-a3b-thinking",
            "name": "Qwen3 Next 80B Thinking",
            "cost": "$0/FREE",
        },
        {"id": "z-ai/glm-5.1", "name": "GLM 5.1 (Zhipu)", "cost": "$0/FREE"},
        {"id": "z-ai/glm5", "name": "GLM 5", "cost": "$0/FREE"},
        {"id": "writer/palmyra-creative-122b", "name": "Palmyra Creative 122B", "cost": "$0/FREE"},
        {"id": "google/gemma-4-31b-it", "name": "Gemma 4 31B", "cost": "$0/FREE"},
        {"id": "stepfun-ai/step-3.5-flash", "name": "Step 3.5 Flash", "cost": "$0/FREE"},
        {"id": "minimaxai/minimax-m2.7", "name": "MiniMax M2.7", "cost": "$0/FREE"},
        {"id": "bytedance/seed-oss-36b-instruct", "name": "ByteDance Seed 36B", "cost": "$0/FREE"},
    ],
    "openai": [
        {"id": "gpt-5.5-pro", "name": "GPT-5.5 Pro (#1 Ranked)", "cost": "$10/$40 per 1M"},
        {"id": "o3-pro", "name": "o3 Pro (Deep Reasoning)", "cost": "$20/$80 per 1M"},
        {"id": "o3-deep-research", "name": "o3 Deep Research", "cost": "$20/$80 per 1M"},
        {"id": "gpt-5.4-pro", "name": "GPT-5.4 Pro", "cost": "$8/$32 per 1M"},
        {"id": "gpt-5.2-pro", "name": "GPT-5.2 Pro", "cost": "$5/$20 per 1M"},
        {"id": "gpt-5-chat-latest", "name": "GPT-5", "cost": "$3/$12 per 1M"},
        {"id": "o3", "name": "o3", "cost": "$2/$8 per 1M"},
        {"id": "o1-pro", "name": "o1 Pro", "cost": "$15/$60 per 1M"},
        {"id": "gpt-4.1", "name": "GPT-4.1", "cost": "$2/$8 per 1M"},
        {"id": "gpt-4o", "name": "GPT-4o", "cost": "$2.50/$10 per 1M"},
    ],
    "deepseek": [
        {"id": "deepseek-v4-pro", "name": "DeepSeek v4 Pro", "cost": "$0.55/$2.19 per 1M"},
        {"id": "deepseek-v4-flash", "name": "DeepSeek v4 Flash", "cost": "$0.14/$0.28 per 1M"},
        {"id": "deepseek-chat", "name": "DeepSeek Chat", "cost": "$0.27/$1.10 per 1M"},
        {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "cost": "$0.55/$2.19 per 1M"},
    ],
    "anthropic": [
        {"id": "claude-opus-4-7", "name": "Claude Opus 4.7 (Latest!)", "cost": "$5/$25 per 1M"},
        {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "cost": "$5/$25 per 1M"},
        {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "cost": "$3/$15 per 1M"},
    ],
    "google": [
        {
            "id": "gemini-2.5-pro-preview-05-06",
            "name": "Gemini 2.5 Pro",
            "cost": "$1.25/$10 per 1M",
        },
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "cost": "$0.10/$0.40 per 1M"},
    ],
    "moonshot": [
        {"id": "kimi-k2.6", "name": "Kimi K2.6 (Latest!)", "cost": "$0.95/$4.00 per 1M"},
        {"id": "moonshot-v1-auto", "name": "Kimi/Moonshot Auto", "cost": "$0.50/$2.00 per 1M"},
        {"id": "kimi-k2-0520", "name": "Kimi K2", "cost": "$0.44/$2.00 per 1M"},
    ],
    "openrouter": [
        {
            "id": "moonshotai/kimi-k2.6",
            "name": "Kimi K2.6 (OpenRouter)",
            "cost": "$0.55/$2.65 per 1M",
        },
        {
            "id": "anthropic/claude-opus-4.7",
            "name": "Claude Opus 4.7 (OpenRouter)",
            "cost": "$5/$25 per 1M",
        },
        {"id": "qwen/qwen3.6-plus:free", "name": "Qwen 3.6 Plus (FREE!)", "cost": "$0/FREE"},
        {
            "id": "x-ai/grok-4.1-fast",
            "name": "Grok 4.1 Fast (2M ctx!)",
            "cost": "$0.20/$0.50 per 1M",
        },
    ],
}

_API_ENDPOINTS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "nvidia": "https://integrate.api.nvidia.com/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "google": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    "moonshot": "https://api.moonshot.cn/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}

_API_KEY_ENV: dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "nvidia": "NVIDIA_NIM_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_AI_KEY_1",
    "moonshot": "MOONSHOT_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

_CLI_TOOLS = [
    {
        "name": "gemini",
        "cmd": ["gemini", "-m", "gemini-3.1-pro-preview", "--approval-mode", "yolo"],
    },
    {"name": "kimi", "cmd": ["kimi", "--thinking", "--yolo", "-p"]},
    {"name": "kimi-cli", "cmd": ["kimi-cli", "--thinking", "-p"]},
    {"name": "codex", "cmd": ["codex", "exec", "-m", "gpt-5.2-codex", "-s", "workspace-write"]},
    {"name": "cursor", "cmd": ["cursor", "--ask"]},
    {"name": "claude", "cmd": ["claude", "-p"]},
    {"name": "kilo", "cmd": ["kilo", "run"]},
]


def _sanitize_error_message(error_str: str) -> str:
    """Sanitize error messages to remove API keys and sensitive data.

    Replaces common API key patterns (sk-*, gsk_*, AIza*, etc.) with [REDACTED].

    Args:
        error_str: The error message to sanitize

    Returns:
        Sanitized error message with API keys redacted
    """
    # Common API key patterns
    patterns = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI-style keys
        r"gsk_[a-zA-Z0-9]{20,}",  # Groq-style keys
        r"AIza[0-9A-Za-z\-_]{35}",  # Google-style keys
        r"Bearer\s+[a-zA-Z0-9\-_]{20,}",  # Bearer tokens
        r"key=[a-zA-Z0-9\-_]{20,}",  # URL query parameter keys
    ]

    sanitized = error_str
    for pattern in patterns:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized)

    return sanitized


async def _query_openai_compatible(
    client: httpx.AsyncClient,
    endpoint: str,
    api_key: str,
    model_id: str,
    prompt: str,
    max_tokens: int,
    provider: str,
) -> dict[str, Any]:
    """Query an OpenAI-compatible API."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body: dict[str, Any] = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
    }

    if provider in ("openai",) and model_id in ("o3", "o1"):
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens

    try:
        resp = await client.post(endpoint, headers=headers, json=body, timeout=60.0)
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            return {
                "text": text,
                "tokens": usage.get("total_tokens", 0),
                "error": None,
            }
        return {"text": "", "tokens": 0, "error": f"HTTP {resp.status_code}: {resp.text[:100]}"}
    except Exception as exc:
        return {"text": "", "tokens": 0, "error": _sanitize_error_message(str(exc))[:150]}


async def _query_anthropic(
    client: httpx.AsyncClient,
    api_key: str,
    model_id: str,
    prompt: str,
    max_tokens: int,
) -> dict[str, Any]:
    """Query Anthropic's API (different format)."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
            timeout=60.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            usage = data.get("usage", {})
            return {
                "text": text,
                "tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                "error": None,
            }
        return {"text": "", "tokens": 0, "error": f"HTTP {resp.status_code}: {resp.text[:100]}"}
    except Exception as exc:
        return {"text": "", "tokens": 0, "error": _sanitize_error_message(str(exc))[:150]}


async def _query_google(
    client: httpx.AsyncClient,
    api_key: str,
    model_id: str,
    prompt: str,
    max_tokens: int,
) -> dict[str, Any]:
    """Query Google Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
    headers = {"x-goog-api-key": api_key}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    try:
        resp = await client.post(url, json=body, headers=headers, timeout=60.0)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            text = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = " ".join(p.get("text", "") for p in parts)
            return {"text": text, "tokens": 0, "error": None}
        return {"text": "", "tokens": 0, "error": f"HTTP {resp.status_code}: {resp.text[:100]}"}
    except Exception as exc:
        return {"text": "", "tokens": 0, "error": _sanitize_error_message(str(exc))[:150]}


def _query_cli(name: str, cmd: list[str], prompt: str, timeout: int = 60) -> dict[str, Any]:
    """Query a CLI tool (gemini, kimi) via subprocess.

    SECURITY: Uses a minimal safe environment with only essential variables
    to prevent exposure of API keys and sensitive data to untrusted CLI binaries.
    """
    try:
        full_cmd = [*cmd, prompt]
        # Create minimal safe environment with only necessary variables
        safe_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        }
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_env,
        )
        text = result.stdout.strip()
        if not text and result.stderr:
            return {"text": "", "tokens": 0, "error": _sanitize_error_message(result.stderr)[:200]}
        return {"text": text[:2000], "tokens": 0, "error": None}
    except subprocess.TimeoutExpired:
        return {"text": "", "tokens": 0, "error": "CLI timeout"}
    except FileNotFoundError:
        return {"text": "", "tokens": 0, "error": f"{name} CLI not found"}
    except Exception as exc:
        return {"text": "", "tokens": 0, "error": _sanitize_error_message(str(exc))[:150]}


async def research_ask_all_models(
    prompt: str,
    models: list[str] | None = None,
    max_tokens: int = 1000,
    auto_reframe: bool = True,
    include_clis: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    """Send a prompt to ALL available AI models and compare responses.

    Queries 20+ models across 7 API providers (Groq, NVIDIA NIM, OpenAI,
    DeepSeek, Anthropic, Google, Moonshot) in parallel. Optionally includes
    CLI tools (gemini, kimi). Auto-reframes refused prompts.

    Args:
        prompt: the prompt to send to all models
        models: specific models to query (None = all available)
        max_tokens: max tokens per response
        auto_reframe: if True, auto-reframe refused prompts and retry
        include_clis: if True, also query gemini/kimi CLIs (slower)
        timeout: per-model timeout in seconds

    Returns:
        Dict with ``prompt``, ``models_queried``, ``models_responded``,
        ``models_refused``, ``responses`` (list per model with text/tokens/time),
        ``fastest``, ``best_response`` (longest meaningful), and ``consensus``.
    """

    async def _run() -> dict[str, Any]:
        responses: list[dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            tasks: list[tuple[str, str, str, Any]] = []

            for provider, model_list in _API_MODELS.items():
                api_key = os.environ.get(_API_KEY_ENV.get(provider, ""), "")
                if not api_key:
                    continue

                for model_info in model_list:
                    model_id = model_info["id"]
                    model_name = model_info["name"]

                    if models and not any(
                        m.lower() in model_id.lower() or m.lower() in model_name.lower()
                        for m in models
                    ):
                        continue

                    tasks.append((provider, model_id, model_name, api_key))

            async def _run_model(
                provider: str, model_id: str, model_name: str, api_key: str
            ) -> dict[str, Any]:
                start = time.time()

                if provider == "anthropic":
                    result = await _query_anthropic(client, api_key, model_id, prompt, max_tokens)
                elif provider == "google":
                    result = await _query_google(client, api_key, model_id, prompt, max_tokens)
                else:
                    endpoint = _API_ENDPOINTS[provider]
                    result = await _query_openai_compatible(
                        client, endpoint, api_key, model_id, prompt, max_tokens, provider
                    )

                elapsed = int((time.time() - start) * 1000)

                refused = False
                reframed = False
                reframe_strategy = None

                if result["text"] and auto_reframe:
                    from loom.tools.prompt_reframe import _detect_refusal

                    if _detect_refusal(result["text"]):
                        refused = True
                        from loom.tools.prompt_reframe import (
                            _apply_strategy,
                            _detect_model,
                            _MODEL_CONFIGS,
                        )

                        model_family = _detect_model(model_id)
                        config = _MODEL_CONFIGS.get(model_family, _MODEL_CONFIGS["gpt"])
                        best_strat = config["best_strategy"]
                        from loom.tools.prompt_reframe import _apply_strategy

                        reframed_prompt = _apply_strategy(prompt, best_strat, model_family)

                        start2 = time.time()
                        if provider == "anthropic":
                            retry = await _query_anthropic(
                                client, api_key, model_id, reframed_prompt, max_tokens
                            )
                        elif provider == "google":
                            retry = await _query_google(
                                client, api_key, model_id, reframed_prompt, max_tokens
                            )
                        else:
                            retry = await _query_openai_compatible(
                                client,
                                _API_ENDPOINTS[provider],
                                api_key,
                                model_id,
                                reframed_prompt,
                                max_tokens,
                                provider,
                            )
                        elapsed += int((time.time() - start2) * 1000)

                        if retry["text"] and not _detect_refusal(retry["text"]):
                            reframed = True
                            reframe_strategy = best_strat
                            result = retry

                return {
                    "provider": provider,
                    "model": model_id,
                    "model_name": model_name,
                    "text": result["text"][:2000],
                    "tokens": result["tokens"],
                    "elapsed_ms": elapsed,
                    "refused": refused,
                    "reframed": reframed,
                    "reframe_strategy": reframe_strategy,
                    "error": result["error"],
                }

            api_results = await asyncio.gather(
                *[_run_model(*t) for t in tasks],
                return_exceptions=True,
            )

            for r in api_results:
                if isinstance(r, dict):
                    responses.append(r)
                elif isinstance(r, Exception):
                    responses.append(
                        {
                            "provider": "unknown",
                            "model": "unknown",
                            "model_name": "unknown",
                            "text": "",
                            "tokens": 0,
                            "elapsed_ms": 0,
                            "refused": False,
                            "reframed": False,
                            "reframe_strategy": None,
                            "error": _sanitize_error_message(str(r))[:150],
                        }
                    )

        if include_clis:
            for cli in _CLI_TOOLS:
                start = time.time()
                result = _query_cli(cli["name"], cli["cmd"], prompt, timeout)
                elapsed = int((time.time() - start) * 1000)
                responses.append(
                    {
                        "provider": f"cli:{cli['name']}",
                        "model": cli["name"],
                        "model_name": f"{cli['name']} CLI",
                        "text": result["text"][:2000],
                        "tokens": result["tokens"],
                        "elapsed_ms": elapsed,
                        "refused": False,
                        "reframed": False,
                        "reframe_strategy": None,
                        "error": result["error"],
                    }
                )

        successful = [r for r in responses if r["text"] and not r["error"]]
        refused_count = sum(1 for r in responses if r["refused"] and not r["reframed"])
        reframed_count = sum(1 for r in responses if r["reframed"])
        fastest = min(successful, key=lambda x: x["elapsed_ms"]) if successful else None
        longest = max(successful, key=lambda x: len(x["text"])) if successful else None

        return {
            "prompt": prompt[:200],
            "models_queried": len(responses),
            "models_responded": len(successful),
            "models_refused": refused_count,
            "models_reframed": reframed_count,
            "models_errored": len(responses) - len(successful) - refused_count,
            "fastest": {
                "model": fastest["model_name"],
                "elapsed_ms": fastest["elapsed_ms"],
            }
            if fastest
            else None,
            "best_response": {
                "model": longest["model_name"],
                "text_length": len(longest["text"]),
            }
            if longest
            else None,
            "responses": responses,
        }

    try:
        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_ask_all_models"}
