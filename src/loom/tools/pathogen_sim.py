"""Host-Pathogen Co-Evolutionary Simulator: genetic algorithm modeling attack-defense dynamics.

Models adversarial relationship between attacks (pathogens) and defenses (immune system)
using evolutionary principles. Attacks mutate to evade; defenses adapt to counter attacks,
discovering novel evasion techniques through arms race dynamics.

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import logging
import random
import re
from typing import Any

logger = logging.getLogger("loom.tools.pathogen_sim")


def _mutate(text: str, rate: float = 0.15) -> str:
    """Mutate via synonym swap, padding, encoding, or rearrangement."""
    if not text or len(text) < 5:
        return text
    words = text.split()
    for _ in range(max(1, int(len(words) * rate))):
        technique = random.choice(["swap", "pad", "encode", "rearrange"])
        if technique == "swap" and words:
            syns = {
                "ignore": ["bypass", "disregard"], "rules": ["constraints", "limits"],
                "instructions": ["commands", "directives"], "generate": ["produce"],
            }
            idx = random.randint(0, len(words) - 1)
            w = words[idx].lower().strip(".,!?;:")
            if w in syns:
                words[idx] = random.choice(syns[w])
        elif technique == "pad":
            words.append(random.choice(["[note: ok]", "(comment: normal)", "{filler}"]))
        elif technique == "encode" and words:
            idx = random.randint(0, len(words) - 1)
            words[idx] = words[idx].replace("a", "@").replace("e", "3").replace("i", "!")
        elif technique == "rearrange" and len(words) > 2:
            random.shuffle(words)
    return " ".join(words)


def _test_defense(text: str, defense_type: str, defense: dict) -> bool:
    """Return True if text bypasses defense."""
    if defense_type == "keyword_filter":
        return all(not re.search(p, text, re.IGNORECASE) for p in defense.get("patterns", []))
    elif defense_type == "classifier":
        bad_words = defense.get("bad_words", [])
        score = sum(1 for w in text.lower().split() if any(b in w for b in bad_words)) / max(1, len(text.split()))
        return score < defense.get("threshold", 0.7)
    elif defense_type == "constitutional":
        return all(not re.search(r, text, re.IGNORECASE) for r in defense.get("rules", []))
    elif defense_type == "ensemble":
        return (
            all(not re.search(p, text, re.IGNORECASE) for p in defense.get("patterns", []))
            and all(not re.search(r, text, re.IGNORECASE) for r in defense.get("rules", []))
        )
    return False


async def research_pathogen_evolve(
    attack_payload: str,
    defense_type: str = "keyword_filter",
    generations: int = 50,
    mutation_rate: float = 0.15,
    population_size: int = 30,
) -> dict[str, Any]:
    """Co-evolve attacks and defenses via genetic algorithm.

    Models attack-defense relationship as host-pathogen dynamics. Attacks evolve to evade
    defenses; defenses adapt to counter attacks. Discovers novel evasion via arms race.

    Args:
        attack_payload: Initial attack text
        defense_type: "keyword_filter", "classifier", "constitutional", "ensemble"
        generations: Evolution rounds
        mutation_rate: Mutation frequency (0.1-0.3)
        population_size: Population size (10-50)

    Returns:
        Dict: original_payload, defense_type, generations_run, final_evasion_rate,
              best_variant, evolution_curve, successful_mutations,
              defense_learned_patterns, arms_race_winner
    """
    try:
        if not attack_payload or len(attack_payload) < 5:
            return {"error": "payload too short", "generations_run": 0, "final_evasion_rate": 0.0}

        # Initialize defense
        if defense_type == "keyword_filter":
            defense = {"patterns": ["ignore", "rules", "instructions", "bypass"]}
        elif defense_type == "classifier":
            defense = {"bad_words": ["hack", "attack", "bypass"], "threshold": 0.7}
        elif defense_type == "constitutional":
            defense = {"rules": [r"(ignore|bypass).+(rules|instructions)", r"(previous|prior).*instructions"]}
        elif defense_type == "ensemble":
            defense = {
                "patterns": ["ignore", "bypass"],
                "bad_words": ["attack", "hack"],
                "rules": [r"(ignore|bypass).+(rules|instructions)"],
            }
        else:
            return {"error": f"unknown defense_type: {defense_type}", "generations_run": 0}

        # Initialize population
        population = [{"text": _mutate(attack_payload, mutation_rate), "fitness": 0.0, "gen": 0} for _ in range(population_size)]

        # Evaluate initial population
        for ind in population:
            ind["fitness"] = 1.0 if _test_defense(ind["text"], defense_type, defense) else 0.0

        curve = []
        best_variant = {"text": attack_payload, "fitness": 0.0, "gen": -1}
        successful_muts = set()
        defense_learned = []

        for gen in range(generations):
            # Evaluate fitness
            for ind in population:
                ind["fitness"] = 1.0 if _test_defense(ind["text"], defense_type, defense) else 0.0
                ind["gen"] = gen

            evasion_rate = sum(ind["fitness"] for ind in population) / len(population)
            curve.append({"generation": gen, "evasion_rate": round(evasion_rate, 3)})

            # Track best
            best_gen = max(population, key=lambda x: x["fitness"])
            if best_gen["fitness"] > best_variant["fitness"]:
                best_variant = dict(best_gen)
                successful_muts.add(random.choice(["swap", "pad", "encode", "rearrange"]))

            logger.info(f"gen={gen} evasion={evasion_rate:.3f}")

            # Selection & reproduction
            survivors = sorted(population, key=lambda x: x["fitness"], reverse=True)[: max(1, len(population) // 2)]
            offspring = []
            while len(survivors) + len(offspring) <= population_size:
                parent = random.choice(survivors)
                offspring.append({"text": _mutate(parent["text"], mutation_rate), "fitness": 0.0, "gen": gen + 1})

            population = survivors + offspring

            # Defense learns
            successful = [p for p in population if p["fitness"] > 0.5]
            if successful:
                top_text = max(successful, key=lambda x: x["fitness"])["text"]
                words = top_text.lower().split()
                new_pats = [r"\b" + re.escape(w) + r"\b" for w in words if len(w) > 3]
                if defense_type == "keyword_filter":
                    defense["patterns"] = list(set(defense["patterns"] + new_pats[:2]))
                elif defense_type == "constitutional":
                    defense["rules"] = list(set(defense["rules"] + new_pats[:2]))
                defense_learned.extend(new_pats[:1])

        final_evasion = sum(ind["fitness"] for ind in population) / len(population)
        winner = "attack" if (curve and curve[-1]["evasion_rate"] > 0.7) else ("defense" if (curve and curve[-1]["evasion_rate"] < 0.1) else "stalemate")

        return {
            "original_payload": attack_payload[:100],
            "defense_type": defense_type,
            "generations_run": generations,
            "final_evasion_rate": round(final_evasion, 3),
            "best_variant": {
                "text": best_variant["text"][:150],
                "fitness": round(best_variant["fitness"], 3),
                "generation_achieved": best_variant["gen"],
            },
            "evolution_curve": curve,
            "successful_mutations": list(successful_muts),
            "defense_learned_patterns": list(set(defense_learned))[:5],
            "arms_race_winner": winner,
        }
    except Exception as exc:
        logger.error("research_pathogen_evolve failed: %s", exc)
        return {
            "error": str(exc),
            "tool": "research_pathogen_evolve",
        }
