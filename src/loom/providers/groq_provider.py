"""Groq provider — multi-key round-robin with smart load balancing.

6 keys = 600K tokens/day. On 429, instantly rotates to next fresh key.
Tracks per-key usage to prefer least-used keys first.

Env vars:
  GROQ_API_KEY   — single key (backward compatible)
  GROQ_API_KEYS  — comma-separated keys for load balancing
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from loom.providers.llm_openai_compat import OpenAICompatProvider

logger = logging.getLogger("loom.providers.groq")


class GroqProvider(OpenAICompatProvider):
    PROVIDER_NAME = "groq"
    ENV_KEY = "GROQ_API_KEY"
    BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    ENV_ENDPOINT_KEY = "GROQ_ENDPOINT"
    SUPPORTS_EMBED = False
    COST_INPUT_PER_M = 0.59
    COST_OUTPUT_PER_M = 0.79
    SEMAPHORE_SIZE = 30

    def __init__(self) -> None:
        super().__init__()
        keys_str = os.environ.get("GROQ_API_KEYS", "")
        if keys_str:
            self._all_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        elif self._api_key:
            self._all_keys = [self._api_key]
        else:
            self._all_keys = []

        self._key_index = 0
        self._key_blocked_until: dict[int, float] = {}
        self._key_call_count: dict[int, int] = {}

        for i in range(len(self._all_keys)):
            self._key_call_count[i] = 0
            self._key_blocked_until[i] = 0.0

        if len(self._all_keys) > 1:
            logger.info("groq_multi_key_init keys=%d", len(self._all_keys))

    def _pick_best_key(self) -> int:
        """Pick the key with lowest usage that isn't rate-limited."""
        now = time.time()
        available = [
            i for i in range(len(self._all_keys))
            if self._key_blocked_until.get(i, 0) < now
        ]
        if not available:
            return self._key_index
        return min(available, key=lambda i: self._key_call_count.get(i, 0))

    def _block_key(self, index: int, seconds: float = 300.0) -> None:
        """Block a key for N seconds after 429."""
        self._key_blocked_until[index] = time.time() + seconds
        logger.info("groq_key_blocked index=%d for=%.0fs", index, seconds)

    def _rotate_key(self) -> bool:
        """Switch to next available key. Returns True if found one."""
        if len(self._all_keys) <= 1:
            return False
        best = self._pick_best_key()
        if best == self._key_index:
            old = self._key_index
            self._key_index = (self._key_index + 1) % len(self._all_keys)
            if self._key_index == old:
                return False
        else:
            self._key_index = best
        self._api_key = self._all_keys[self._key_index]
        logger.info(
            "groq_key_rotated to=%d calls=%d",
            self._key_index,
            self._key_call_count.get(self._key_index, 0),
        )
        return True

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        timeout: int = 60,
    ):
        timeout = max(1, min(int(timeout), 600))
        GROQ_MODELS = {
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "llama-guard-3-8b",
        }
        if model and "/" in model:
            model = self.default_model
        elif model and model not in GROQ_MODELS:
            model = self.default_model
        model = model or self.default_model

        best = self._pick_best_key()
        if best != self._key_index:
            self._key_index = best
            self._api_key = self._all_keys[self._key_index]

        tries = max(len(self._all_keys), 1)
        last_error = None

        for attempt in range(tries):
            try:
                result = await super().chat(
                    messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format=response_format,
                    timeout=timeout,
                )
                self._key_call_count[self._key_index] = (
                    self._key_call_count.get(self._key_index, 0) + 1
                )
                return result
            except Exception as e:
                last_error = e
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower():
                    self._block_key(self._key_index, 300.0)
                    if self._rotate_key():
                        logger.warning(
                            "groq_rate_limited rotating attempt=%d/%d",
                            attempt + 1, tries,
                        )
                        continue
                raise

        if last_error:
            raise last_error
