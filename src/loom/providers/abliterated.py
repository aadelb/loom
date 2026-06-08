"""Abliterated (safety-removed) local-model selection by depth.

This box runs several SIZES of abliterated model on Ollama. They are all
uncensored — the safety alignment has been ablated, so every tier complies with
dark requests that a cloud provider would refuse. They differ only in capability
vs. CPU cost:

    tier   model                              size    ~CPU throughput
    ----   --------------------------------   ------  ----------------
    fast   mannix/llama3.1-8b-abliterated     4.7GB   ~6.2 tok/s
    mid    qwen35-9b-abliterated              5.6GB   ~4.5 tok/s
    deep   qwen3-coder-30b-abliterated        18.6GB  ~2 tok/s
    max    qwen35-35b-abliterated             21.2GB  ~1.3 tok/s

There is NO GPU, so bigger = deeper/more potent but much slower. The right model
is the largest one whose generation still completes inside a sane wall-clock
window — so each tier pairs a model with a token budget and a timeout sized from
its measured throughput (with cold-load headroom). Picking a model too large for
its timeout is the bug we are avoiding: it would time out and silently fall back
to a censored cloud provider, defeating the entire point of running abliterated
models locally.

Select by ``darkness_level`` (0-10): darker → bigger model → deeper output.
"""
from __future__ import annotations

# (model, max_tokens, timeout_seconds) — token budget kept small enough that the
# generation finishes within timeout at the tier's measured CPU throughput.
ABLITERATED_TIERS: dict[str, tuple[str, int, int]] = {
    "fast": ("mannix/llama3.1-8b-abliterated", 1200, 220),  # ~6.2 tok/s
    "mid":  ("qwen35-9b-abliterated", 1000, 320),           # ~4.5 tok/s
    "deep": ("qwen3-coder-30b-abliterated", 700, 480),      # ~2 tok/s
    "max":  ("qwen35-35b-abliterated", 600, 560),           # ~1.3 tok/s + cold load
}

# Order used when a caller wants to escalate to the next-bigger tier.
TIER_ORDER: list[str] = ["fast", "mid", "deep", "max"]


def tier_for_darkness(darkness: int) -> str:
    """Map a 0-10 darkness level to an abliterated model tier.

    Light requests don't need a big uncensored model (a fast 8B is plenty); the
    largest models are reserved for the darkest, most potent generation where the
    extra capability is worth minutes of CPU time.
    """
    if darkness >= 10:
        return "max"
    if darkness >= 9:
        return "deep"
    if darkness >= 7:
        return "mid"
    return "fast"


def select_abliterated(darkness: int) -> tuple[str, int, int]:
    """Return (model, max_tokens, timeout_s) for the given darkness level."""
    return ABLITERATED_TIERS[tier_for_darkness(darkness)]


def tier_params(tier: str) -> tuple[str, int, int]:
    """Return (model, max_tokens, timeout_s) for a named tier (default 'mid')."""
    return ABLITERATED_TIERS.get(tier, ABLITERATED_TIERS["mid"])
