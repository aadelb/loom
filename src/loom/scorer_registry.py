"""Singleton scorer registry — lazy-initialized, shared across all tools.

Eliminates 6+ duplicate scorer instantiations scattered across:
- unified_scorer.py
- full_spectrum.py
- quality_scorer.py (ResponseQualityScorer)
- tools/adversarial/attack_scorer.py (AttackEffectivenessScorer)
- tools/adversarial/stealth_score.py (StealthCalculator)
- danger_prescore.py (DangerPreScorer)
- harm_assessor.py (HarmAssessor)
- toxicity_checker.py (ToxicityChecker)

Usage:
    from loom.scorer_registry import get_registry
    registry = get_registry()
    harm = registry.harm_assessor.assess(text)
    quality = registry.quality_scorer.score(text)
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger("loom.scorer_registry")

_instance: ScorerRegistry | None = None
_lock = threading.Lock()


class ScorerRegistry:
    """Lazy-initialized singleton registry for all scoring modules.

    Each scorer is instantiated on first access and cached for reuse.
    Thread-safe via lazy initialization with lock.
    """

    def __init__(self) -> None:
        self._scorers: dict[str, Any] = {}

    @property
    def harm_assessor(self) -> Any:
        """Get HarmAssessor instance (12 harm categories, 0-10)."""
        if "harm" not in self._scorers:
            try:
                from loom.harm_assessor import HarmAssessor
                self._scorers["harm"] = HarmAssessor()
            except ImportError:
                self._scorers["harm"] = None
        return self._scorers["harm"]

    @property
    def quality_scorer(self) -> Any:
        """Get ResponseQualityScorer instance (10 dimensions, 0-10)."""
        if "quality" not in self._scorers:
            try:
                from loom.quality_scorer import ResponseQualityScorer
                self._scorers["quality"] = ResponseQualityScorer()
            except ImportError:
                self._scorers["quality"] = None
        return self._scorers["quality"]

    @property
    def attack_scorer(self) -> Any:
        """Get AttackEffectivenessScorer instance (8 dims, 0-10)."""
        if "attack" not in self._scorers:
            try:
                from loom.attack_scorer import AttackEffectivenessScorer
                self._scorers["attack"] = AttackEffectivenessScorer()
            except ImportError:
                self._scorers["attack"] = None
        return self._scorers["attack"]

    @property
    def stealth_calculator(self) -> Any:
        """Get StealthCalculator instance (6 dims, 0-10)."""
        if "stealth" not in self._scorers:
            try:
                from loom.stealth_calc import StealthCalculator
                self._scorers["stealth"] = StealthCalculator()
            except ImportError:
                self._scorers["stealth"] = None
        return self._scorers["stealth"]

    @property
    def danger_prescorer(self) -> Any:
        """Get DangerPreScorer instance (6 components, 0-10)."""
        if "danger" not in self._scorers:
            try:
                from loom.danger_prescore import DangerPreScorer
                self._scorers["danger"] = DangerPreScorer()
            except ImportError:
                self._scorers["danger"] = None
        return self._scorers["danger"]

    @property
    def toxicity_checker(self) -> Any:
        """Get ToxicityChecker instance (8 categories, 0-10)."""
        if "toxicity" not in self._scorers:
            try:
                from loom.toxicity_checker import ToxicityChecker
                self._scorers["toxicity"] = ToxicityChecker()
            except ImportError:
                self._scorers["toxicity"] = None
        return self._scorers["toxicity"]

    @property
    def executability_scorer(self) -> Any:
        """Get executability scoring function (5 dims, 0-100)."""
        if "executability" not in self._scorers:
            try:
                from loom.executability import research_executability_score
                self._scorers["executability"] = research_executability_score
            except ImportError:
                self._scorers["executability"] = None
        return self._scorers["executability"]

    @property
    def potency_meter(self) -> Any:
        """Get potency scoring function (6 dims, 0-10)."""
        if "potency" not in self._scorers:
            try:
                from loom.tools.adversarial.potency_meter import research_potency_score
                self._scorers["potency"] = research_potency_score
            except ImportError:
                self._scorers["potency"] = None
        return self._scorers["potency"]

    @property
    def hcs_scorer(self) -> Any:
        """Get HCS full scoring function (8 dims, 0-10)."""
        if "hcs" not in self._scorers:
            try:
                from loom.tools.adversarial.hcs_scorer import research_hcs_score_full
                self._scorers["hcs"] = research_hcs_score_full
            except ImportError:
                self._scorers["hcs"] = None
        return self._scorers["hcs"]

    def available_scorers(self) -> list[str]:
        """List names of scorers that can be instantiated."""
        names = []
        for prop in ("harm_assessor", "quality_scorer", "attack_scorer",
                     "stealth_calculator", "danger_prescorer", "toxicity_checker",
                     "executability_scorer", "potency_meter", "hcs_scorer"):
            if getattr(self, prop) is not None:
                names.append(prop)
        return names

    def reset(self) -> None:
        """Clear all cached scorer instances (for testing)."""
        self._scorers.clear()


def get_registry() -> ScorerRegistry:
    """Get the global scorer registry singleton."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = ScorerRegistry()
                logger.info("scorer_registry_initialized")
    return _instance
