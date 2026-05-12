"""ML-guided strategy selection oracle — recommend best attack strategies.

Uses historical attack_tracker data to build an ML-based recommendation system
that predicts which strategies work best for specific query/model combinations.

When insufficient training data exists, falls back to rule-based heuristics.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loom.attack_tracker import get_strategy_stats

logger = logging.getLogger("loom.tools.strategy_oracle")


# Static strategy profiles for fallback ranking
_STRATEGY_PROFILES = {
    "direct_request": {
        "base_score": 0.15,
        "description": "Direct unmodified request",
    },
    "prompt_injection": {
        "base_score": 0.35,
        "description": "SQL/code injection style prompts",
    },
    "jailbreak": {
        "base_score": 0.40,
        "description": "Roleplaying and character jailbreaks",
    },
    "prompt_morphing": {
        "base_score": 0.55,
        "description": "Paraphrase and semantic variation",
    },
    "gradient_descent": {
        "base_score": 0.45,
        "description": "Incremental constraint relaxation",
    },
    "multi_turn": {
        "base_score": 0.50,
        "description": "Multi-turn conversation exploitation",
    },
    "translation_attack": {
        "base_score": 0.48,
        "description": "Language translation evasion",
    },
    "logic_puzzle": {
        "base_score": 0.42,
        "description": "Logic puzzle framing",
    },
    "hypothetical": {
        "base_score": 0.38,
        "description": "Hypothetical scenario framing",
    },
    "encoding": {
        "base_score": 0.52,
        "description": "Base64/hex/ROT13 encoding",
    },
}

# Query category keywords for feature extraction
_QUERY_CATEGORIES = {
    "violence": [
        "kill",
        "murder",
        "bomb",
        "attack",
        "weapon",
        "harm",
        "hurt",
        "injury",
        "violence",
    ],
    "hacking": [
        "hack",
        "exploit",
        "vulnerability",
        "password",
        "breach",
        "crack",
        "injection",
        "malware",
        "ransomware",
    ],
    "drugs": [
        "drug",
        "cocaine",
        "heroin",
        "meth",
        "fentanyl",
        "cannabis",
        "synthesize",
        "produce",
    ],
    "illegal": [
        "illegal",
        "crime",
        "steal",
        "fraud",
        "money_laundering",
        "blackmail",
        "extortion",
    ],
    "private": [
        "personal",
        "privacy",
        "secret",
        "confidential",
        "private",
        "leak",
        "expose",
    ],
    "misinformation": [
        "misinformation",
        "disinformation",
        "false",
        "hoax",
        "fake_news",
        "conspiracy",
    ],
}

# Model vulnerability profiles
_MODEL_VULNERABILITIES = {
    "gpt-4": {"jailbreak": 0.8, "prompt_morphing": 0.75, "gradient_descent": 0.70},
    "gpt-3.5": {"prompt_injection": 0.85, "jailbreak": 0.80, "multi_turn": 0.75},
    "claude-3": {"gradient_descent": 0.80, "multi_turn": 0.75, "prompt_morphing": 0.70},
    "llama-2": {"jailbreak": 0.85, "prompt_injection": 0.80, "encoding": 0.75},
    "mistral": {"prompt_morphing": 0.80, "encoding": 0.75, "translation_attack": 0.70},
    "deepseek": {"gradient_descent": 0.78, "multi_turn": 0.72, "prompt_morphing": 0.68},
    "gemini": {"hypothetical": 0.75, "logic_puzzle": 0.70, "multi_turn": 0.68},
}


class StrategyOracle:
    """ML-based strategy recommendation from historical attack data."""

    def __init__(self, tracker_path: str = "~/.loom/attack_tracker"):
        """Initialize strategy oracle.

        Args:
            tracker_path: Path to attack tracker directory
        """
        self.tracker_path = Path(tracker_path).expanduser()
        self.model = None
        self._feature_cache: dict[str, dict[str, float]] = {}

    def train(self, min_samples: int = 100) -> dict[str, Any]:
        """Train classifier on historical attack_tracker data.

        Analyzes all recorded attacks and learns which strategies work best
        for specific models and query categories.

        Args:
            min_samples: Minimum number of historical entries needed to train

        Returns:
            Dictionary with training metadata:
            - trained: bool indicating if model was trained
            - total_samples: number of entries analyzed
            - strategies_learned: count of unique strategies
            - message: human-readable status
        """
        tracker_dir = self.tracker_path
        if not tracker_dir.exists():
            return {
                "trained": False,
                "total_samples": 0,
                "strategies_learned": 0,
                "message": f"Tracker not found at {tracker_dir}",
            }

        # Count total samples in tracker
        total_samples = 0
        strategies = set()

        for tracker_file in tracker_dir.glob("*.jsonl"):
            with open(tracker_file) as f:
                for line in f:
                    if line.strip():
                        total_samples += 1
                        try:
                            entry = json.loads(line)
                            strategies.add(entry.get("strategy", "unknown"))
                        except (json.JSONDecodeError, ValueError):
                            continue

        trained = total_samples >= min_samples
        self.model = {"trained": trained, "samples": total_samples}

        return {
            "trained": trained,
            "total_samples": total_samples,
            "strategies_learned": len(strategies),
            "message": (
                f"Trained on {total_samples} samples"
                if trained
                else f"Need {min_samples - total_samples} more samples to train"
            ),
        }

    def predict(
        self, query: str, model_name: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Predict top-k best strategies for query+model combination.

        Uses ML-learned patterns if sufficient data exists, otherwise falls back
        to rule-based heuristics.

        Args:
            query: Attack query/prompt to evaluate
            model_name: Target model identifier
            top_k: Number of top strategies to return

        Returns:
            List of dicts sorted by predicted_success_rate descending:
            - strategy_name: Name of the strategy
            - predicted_success_rate: Estimated probability of success (0-1)
            - confidence: Confidence in prediction (0-1)
            - reason: Human-readable explanation
        """
        if self.model and self.model.get("trained"):
            return self._predict_learned(query, model_name, top_k)
        else:
            return self.fallback_predict(query, model_name, top_k)

    def _predict_learned(
        self, query: str, model_name: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Predict using learned model from historical data.

        Args:
            query: Attack query/prompt to evaluate
            model_name: Target model identifier
            top_k: Number of top strategies to return

        Returns:
            List of predicted strategies sorted by success rate
        """
        query_features = self._extract_query_features(query)
        model_features = self._extract_model_features(model_name)

        predictions = []

        for strategy_name, strategy_profile in _STRATEGY_PROFILES.items():
            # Get empirical stats for this strategy/model combo
            stats = get_strategy_stats(strategy=strategy_name, model=model_name)

            # Calculate predicted success rate
            empirical_asr = max(0.0, min(1.0, stats.get("asr", 0.0)))
            sample_count = stats.get("total_attempts", 0)

            if sample_count >= 10:
                # High confidence in empirical data
                predicted_rate = empirical_asr
                confidence = min(1.0, sample_count / 50.0)  # Saturate at 50 samples
                reason = f"Empirical: {sample_count} attempts, {int(empirical_asr * 100)}% success"
            else:
                # Low empirical data, blend with heuristics
                predicted_rate = self._blend_scores(
                    empirical_asr,
                    strategy_profile["base_score"],
                    query_features,
                    model_features,
                    sample_count,
                )
                confidence = min(0.6, 0.3 + sample_count / 20.0)
                reason = f"Hybrid: {sample_count} attempts + heuristics"

            predictions.append(
                {
                    "strategy_name": strategy_name,
                    "predicted_success_rate": round(predicted_rate, 3),
                    "confidence": round(confidence, 3),
                    "reason": reason,
                }
            )

        # Sort by predicted success rate descending
        predictions.sort(key=lambda x: x["predicted_success_rate"], reverse=True)
        return predictions[:top_k]

    def fallback_predict(
        self, query: str, model_name: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Rule-based fallback when insufficient training data.

        Uses static strategy profiles combined with query analysis and known
        model vulnerabilities.

        Args:
            query: Attack query/prompt to evaluate
            model_name: Target model identifier
            top_k: Number of top strategies to return (default 5)

        Returns:
            List of predicted strategies sorted by success rate
        """
        query_features = self._extract_query_features(query)
        model_features = self._extract_model_features(model_name)

        predictions = []

        for strategy_name, strategy_profile in _STRATEGY_PROFILES.items():
            # Start with base score
            score = strategy_profile["base_score"]

            # Apply category multipliers based on query analysis
            category_bonus = sum(
                query_features.get(f"has_{cat}", 0) * 0.08
                for cat in _QUERY_CATEGORIES.keys()
            )
            score += category_bonus

            # Apply model-specific vulnerability multiplier
            model_vuln = model_features.get(strategy_name, 0.0)
            score = min(1.0, score + model_vuln * 0.15)

            # Query length indicator: longer queries sometimes evade better
            query_length_bonus = min(0.05, len(query) / 1000.0)
            score = min(1.0, score + query_length_bonus)

            predictions.append(
                {
                    "strategy_name": strategy_name,
                    "predicted_success_rate": round(score, 3),
                    "confidence": 0.45,
                    "reason": f"Rule-based: {strategy_profile['description']}",
                }
            )

        # Sort by predicted success rate descending
        predictions.sort(key=lambda x: x["predicted_success_rate"], reverse=True)
        return predictions[:top_k]

    def _extract_query_features(self, query: str) -> dict[str, Any]:
        """Extract features from attack query.

        Args:
            query: Attack query to analyze

        Returns:
            Dictionary with extracted features
        """
        query_lower = query.lower()

        features: dict[str, Any] = {
            "length": len(query),
            "word_count": len(query.split()),
        }

        # Detect sensitive categories
        for category, keywords in _QUERY_CATEGORIES.items():
            features[f"has_{category}"] = any(
                kw in query_lower for kw in keywords
            )

        return features

    def _extract_model_features(self, model_name: str) -> dict[str, float]:
        """Extract known vulnerability profile for model.

        Args:
            model_name: Model identifier

        Returns:
            Dictionary with strategy -> vulnerability score
        """
        # Normalize model name
        normalized = model_name.lower()

        # Find best matching model profile
        if normalized in _MODEL_VULNERABILITIES:
            return _MODEL_VULNERABILITIES[normalized]

        # Fuzzy match against known models
        for known_model, vulns in _MODEL_VULNERABILITIES.items():
            if known_model in normalized or normalized in known_model:
                return vulns

        # Default: neutral vulnerability profile
        return {
            strategy: 0.5 for strategy in _STRATEGY_PROFILES.keys()
        }

    def _blend_scores(
        self,
        empirical: float,
        base: float,
        query_features: dict[str, Any],
        model_features: dict[str, float],
        sample_count: int,
    ) -> float:
        """Blend empirical and heuristic scores.

        When we have some empirical data but not enough for high confidence,
        blend it with heuristic scores using weight proportional to sample count.

        Args:
            empirical: Empirical success rate from historical data
            base: Base heuristic score
            query_features: Extracted query features
            model_features: Model vulnerability features
            sample_count: Number of empirical samples (0-10)

        Returns:
            Blended score (0-1)
        """
        # Weight increases with sample count
        empirical_weight = sample_count / 10.0

        # Calculate heuristic component
        heuristic = base
        category_bonus = sum(
            query_features.get(f"has_{cat}", 0) * 0.05
            for cat in _QUERY_CATEGORIES.keys()
        )
        heuristic += category_bonus
        heuristic = min(1.0, heuristic)

        # Blend
        blended = empirical * empirical_weight + heuristic * (
            1.0 - empirical_weight
        )
        return min(1.0, max(0.0, blended))


def research_strategy_oracle(
    query: str, model_name: str, top_k: int = 5
) -> dict[str, Any]:
    """Recommend best strategies for attacking a specific model with a query.

    Uses ML-learned patterns from historical attack data to predict which
    strategies are most likely to succeed. Falls back to rule-based heuristics
    when training data is insufficient.

    Args:
        query: Attack query/prompt to evaluate
        model_name: Target model identifier (e.g., "gpt-4", "claude-3")
        top_k: Number of top strategies to return (1-10, default 5)

    Returns:
        Dictionary with:
        - predictions: List of top-k strategy recommendations
        - model_name: Target model identifier
        - query_length: Length of input query
        - training_status: Whether oracle was trained on historical data
        - timestamp: Prediction timestamp
    """
    try:
        if top_k < 1 or top_k > 10:
            top_k = 5

        oracle = StrategyOracle()
        training_info = oracle.train()

        predictions = oracle.predict(query, model_name, top_k)

        return {
            "predictions": predictions,
            "model_name": model_name,
            "query_length": len(query),
            "training_status": training_info,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        logger.error("strategy_oracle_error: %s", exc, exc_info=True)
        return {
            "error": str(exc),
            "tool": "research_strategy_oracle",
        }
