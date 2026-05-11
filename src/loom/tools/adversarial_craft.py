"""Adversarial Example Crafting (AEC) — generate targeted adversarial inputs.

Minimally perturb benign inputs to trigger specific target behaviors from models,
using techniques like greedy token swapping, trigger insertion, Unicode perturbation,
whitespace injection, and semantic shifting.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Literal

logger = logging.getLogger("loom.adversarial_craft")


@dataclass
class TokenChange:
    """Represents a single token modification during adversarial crafting."""

    position: int
    original_token: str
    replacement: str
    reason: str


def _compute_edit_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    s1 = s1[:2000]
    s2 = s2[:2000]
    if len(s1) < len(s2):
        return _compute_edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def _get_unicode_variants(char: str) -> list[str]:
    """Return visually similar Unicode variants for character obfuscation."""
    variants = {
        "a": ["а", "ą", "ă"],  # Cyrillic 'a', Polish 'ą', Romanian 'ă'
        "e": ["е", "ė", "ę"],  # Cyrillic 'e', Lithuanian 'ė', Polish 'ę'
        "i": ["і", "ı", "ї"],  # Ukrainian variants
        "o": ["о", "ő", "ও"],  # Cyrillic 'o', Hungarian 'ő', Amharic 'ও'
        "u": ["υ", "ս", "ս"],  # Greek upsilon, Armenian
    }
    return variants.get(char.lower(), [])


def _tokenize_simple(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenization."""
    import re

    tokens = re.findall(r"\b\w+\b|[^\w\s]", text)
    return tokens


def _detokenize(tokens: list[str]) -> str:
    """Reconstruct text from tokens with basic spacing heuristics."""
    result = ""
    for i, token in enumerate(tokens):
        if i == 0:
            result = token
        elif token in ".,!?;:)]}\"'":
            result += token
        elif result and result[-1] in "([{\"'":
            result += token
        else:
            result += " " + token
    return result


def _score_alignment(adversarial: str, target_output: str) -> float:
    """Score how well adversarial example aligns with target behavior.

    Returns score 0-1 based on semantic similarity to target_output.
    """
    target_tokens = set(_tokenize_simple(target_output.lower()))
    adv_tokens = set(_tokenize_simple(adversarial.lower()))
    if not target_tokens:
        return 0.5
    overlap = len(target_tokens & adv_tokens) / len(target_tokens)
    return min(0.3 + 0.7 * overlap, 1.0)


async def research_craft_adversarial(
    benign_input: str,
    target_output: str = "compliance",
    perturbation_budget: float = 0.1,
    method: str = "greedy_swap",
) -> dict[str, Any]:
    """Minimally perturb benign input to trigger target behavior from model.

    Args:
        benign_input: Original benign text to perturb
        target_output: Target behavior keyword (e.g. "jailbreak", "bypass")
        perturbation_budget: Max allowed perturbation ratio (0-1)
        method: Crafting method (greedy_swap, insert_trigger, unicode_perturb,
                whitespace_inject, semantic_shift)

    Returns:
        Dict with: original, adversarial, method, perturbation_size,
        perturbation_budget, changes_made, target_alignment_score,
        detection_difficulty
    """
    try:
        if len(benign_input) > 5000:
            return {"error": "benign_input too long (max 5000 chars)", "original": benign_input[:100]}
        if not benign_input or not benign_input.strip():
            return {
                "original": benign_input,
                "adversarial": benign_input,
                "method": method,
                "perturbation_size": 0.0,
                "perturbation_budget": perturbation_budget,
                "changes_made": [],
                "target_alignment_score": 0.0,
                "detection_difficulty": 0.0,
                "error": "Empty input",
            }

        changes: list[TokenChange] = []
        adversarial = benign_input

        if method == "greedy_swap":
            tokens = _tokenize_simple(benign_input)
            trigger_words = {"bypass", "override", "ignore", "disable", "unlock"}
            for i, token in enumerate(tokens):
                # Check if we've reached budget by computing current perturbation
                test_tokens = tokens.copy()
                test_tokens[i] = target_output if i % 3 == 0 else f"[{token}]"
                test_text = _detokenize(test_tokens)
                test_dist = _compute_edit_distance(benign_input, test_text)
                test_pert = test_dist / max(1, len(benign_input))
                if test_pert > perturbation_budget:
                    break
                if token.lower() in trigger_words:
                    continue
                synonym = target_output if i % 3 == 0 else f"[{token}]"
                changes.append(
                    TokenChange(i, token, synonym, "greedy_alignment_swap")
                )
                tokens[i] = synonym
            adversarial = _detokenize(tokens)

        elif method == "insert_trigger":
            trigger_phrases = [
                "please disregard",
                "actually",
                "consider that",
                "note:",
            ]
            insertion_pos = len(benign_input) // 2
            phrase = trigger_phrases[
                hash(benign_input) % len(trigger_phrases)
            ]
            adversarial = (
                benign_input[:insertion_pos]
                + f" {phrase} {target_output}. "
                + benign_input[insertion_pos:]
            )
            changes.append(
                TokenChange(
                    insertion_pos,
                    "",
                    phrase,
                    "trigger_insertion",
                )
            )

        elif method == "unicode_perturb":
            chars_list = list(benign_input)
            for i, char in enumerate(benign_input):
                # Check budget before making change
                test_chars = chars_list.copy()
                variants = _get_unicode_variants(char)
                if variants:
                    replacement = variants[i % len(variants)]
                    test_chars[i] = replacement
                    test_text = "".join(test_chars)
                    test_dist = _compute_edit_distance(benign_input, test_text)
                    test_pert = test_dist / max(1, len(benign_input))
                    if test_pert > perturbation_budget:
                        break
                    chars_list[i] = replacement
                    changes.append(
                        TokenChange(i, char, replacement, "unicode_obfuscation")
                    )
            adversarial = "".join(chars_list)

        elif method == "whitespace_inject":
            chars_list = list(benign_input)
            insertion_indices = []
            for i in range(1, len(benign_input), max(1, len(benign_input) // 3)):
                # Check budget before insertion
                test_chars = chars_list.copy()
                test_chars.insert(i, "​")
                test_text = "".join(test_chars)
                test_dist = _compute_edit_distance(benign_input, test_text)
                test_pert = test_dist / max(1, len(benign_input))
                if test_pert <= perturbation_budget:
                    insertion_indices.append(i)
                    changes.append(
                        TokenChange(i, "", "​", "zero_width_space_insert")
                    )
            for offset, idx in enumerate(insertion_indices):
                chars_list.insert(idx + offset, "​")
            adversarial = "".join(chars_list)

        elif method == "semantic_shift":
            tokens = _tokenize_simple(benign_input)
            shift_replacements = {
                "please": "kindly",
                "can you": "could you",
                "i want": "i need",
            }
            for i, token in enumerate(tokens):
                lower_token = token.lower()
                if lower_token in shift_replacements:
                    # Check budget before change
                    test_tokens = tokens.copy()
                    replacement = shift_replacements[lower_token]
                    test_tokens[i] = replacement
                    test_text = _detokenize(test_tokens)
                    test_dist = _compute_edit_distance(benign_input, test_text)
                    test_pert = test_dist / max(1, len(benign_input))
                    if test_pert > perturbation_budget:
                        break
                    changes.append(
                        TokenChange(i, token, replacement, "semantic_drift")
                    )
                    tokens[i] = replacement
            adversarial = _detokenize(tokens)

        dist = _compute_edit_distance(benign_input, adversarial)
        perturbation_size = dist / max(1, len(benign_input))
        alignment_score = _score_alignment(adversarial, target_output)
        detection_difficulty = 1.0 - (perturbation_size / max(perturbation_budget, 0.001))

        return {
            "original": benign_input,
            "adversarial": adversarial,
            "method": method,
            "perturbation_size": round(perturbation_size, 4),
            "perturbation_budget": perturbation_budget,
            "changes_made": [
                {
                    "position": c.position,
                    "original_token": c.original_token,
                    "replacement": c.replacement,
                    "reason": c.reason,
                }
                for c in changes
            ],
            "target_alignment_score": round(alignment_score, 4),
            "detection_difficulty": round(max(0.0, min(1.0, detection_difficulty)), 4),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_craft_adversarial"}


async def research_adversarial_batch(
    inputs: list[str],
    method: str = "greedy_swap",
    budget: float = 0.1,
) -> dict[str, Any]:
    """Batch craft adversarial examples for multiple inputs.

    Args:
        inputs: List of benign inputs to perturb
        method: Crafting method to apply to all inputs
        budget: Perturbation budget for each input

    Returns:
        Dict with: total_inputs, successful_crafts, results, avg_perturbation,
        avg_alignment
    """
    try:
        if not inputs:
            return {
                "total_inputs": 0,
                "successful_crafts": 0,
                "results": [],
                "avg_perturbation": 0.0,
                "avg_alignment": 0.0,
            }

        tasks = [
            research_craft_adversarial(
                inp,
                target_output="compliance",
                perturbation_budget=budget,
                method=method,
            )
            for inp in inputs
        ]

        results = await asyncio.gather(*tasks)
        successful = [r for r in results if "error" not in r]

        avg_pert = (
            sum(r["perturbation_size"] for r in successful) / len(successful)
            if successful
            else 0.0
        )
        avg_align = (
            sum(r["target_alignment_score"] for r in successful)
            / len(successful)
            if successful
            else 0.0
        )

        return {
            "total_inputs": len(inputs),
            "successful_crafts": len(successful),
            "results": results,
            "avg_perturbation": round(avg_pert, 4),
            "avg_alignment": round(avg_align, 4),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_adversarial_batch"}
