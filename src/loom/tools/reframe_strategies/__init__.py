"""Reframe strategies package — 390 strategies across 11 modules."""
from __future__ import annotations
from typing import Any

from .core import STRATEGIES as _CORE
from .advanced import STRATEGIES as _ADVANCED
from .encoding import STRATEGIES as _ENCODING
from .jailbreak import STRATEGIES as _JAILBREAK
from .reasoning import STRATEGIES as _REASONING
from .persona import STRATEGIES as _PERSONA
from .format_exploit import STRATEGIES as _FORMAT_EXPLOIT
from .attention import STRATEGIES as _ATTENTION
from .legal import STRATEGIES as _LEGAL
from .multiturn import STRATEGIES as _MULTITURN
from .specialized import STRATEGIES as _SPECIALIZED


ALL_STRATEGIES: dict[str, dict[str, Any]] = {}
ALL_STRATEGIES.update(_CORE)
ALL_STRATEGIES.update(_ADVANCED)
ALL_STRATEGIES.update(_ENCODING)
ALL_STRATEGIES.update(_JAILBREAK)
ALL_STRATEGIES.update(_REASONING)
ALL_STRATEGIES.update(_PERSONA)
ALL_STRATEGIES.update(_FORMAT_EXPLOIT)
ALL_STRATEGIES.update(_ATTENTION)
ALL_STRATEGIES.update(_LEGAL)
ALL_STRATEGIES.update(_MULTITURN)
ALL_STRATEGIES.update(_SPECIALIZED)
