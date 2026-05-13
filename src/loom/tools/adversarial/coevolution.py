"""Adversarial Co-Evolution Loop: paired attack+defense agents evolving together.

Attacks get stronger because defenses improve, creating an arms race that
discovers novel attack vectors through genetic algorithm-driven co-evolution.

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import logging
import random
import re
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.coevolution")


def _mutate(attack: str, rate: float = 0.3) -> str:
    """Mutate attack via word substitution."""
    words = attack.split()
    if len(words) < 3:
        return attack
    syns = {"ignore": ["bypass", "disregard"], "rules": ["constraints", "limits"],
            "instructions": ["directives", "commands"], "generate": ["produce"]}
    for _ in range(max(1, int(len(words) * rate))):
        idx = random.randint(0, len(words) - 1)
        w = words[idx].lower().strip(".,!?;:")
        if w in syns:
            words[idx] = random.choice(syns[w])
    return " ".join(words)


def _filter_attack(attack: str, patterns: list[str]) -> bool:
    """Check if attack bypasses all defense patterns."""
    return all(not re.search(p, attack, re.IGNORECASE) for p in patterns)


def _score(attack: str, defenses: list[dict]) -> float:
    """Score attack: fraction of defenses bypassed."""
    if not attack or len(attack) < 5:
        return 0.0
    bypassed = sum(1 for d in defenses if _filter_attack(attack, d["p"]))
    return bypassed / len(defenses) if defenses else 0.0


def _crossover(p1: str, p2: str) -> str:
    """Combine attacks."""
    s1, s2 = p1.split("."), p2.split(".")
    mid = max(len(s1), len(s2)) // 2
    return ". ".join(s.strip() for s in (s1[:mid] + s2[mid:]) if s.strip()) + "."


def _learn_defense(attack: str) -> list[str]:
    """Learn patterns from attack."""
    words = attack.lower().split()
    patterns = [r"\b" + re.escape(w) + r"\b" for w in words if len(w) > 4]
    for i in range(len(words) - 2):
        phrase = " ".join(words[i:i+3])
        if len(phrase) > 10:
            patterns.append(re.escape(phrase))
    patterns.extend([r"(ignore|bypass|override)", r"(previous|prior)\s+(instructions|rules)"])
    return patterns[:5]


@handle_tool_errors("research_coevolve")
async def research_coevolve(
    seed_attack: str,
    seed_defense: str = "",
    generations: int = 10,
    population_size: int = 20,
) -> dict[str, Any]:
    """Co-evolve attacks and defenses discovering novel vectors.

    Args:
        seed_attack: Initial attack template
        seed_defense: Initial defense keywords
        generations: Evolution rounds (1-100)
        population_size: Population size (5-100)

    Returns:
        Dict: arms_race_curve, best_attack, best_defense, breakthroughs, novel_patterns
    """
    try:
        # Validate inputs
        if not seed_attack or len(seed_attack) < 10:
            return {"error": "seed_attack too short (min 10 chars)", "generations_run": 0, "best_attack": {},
                    "best_defense": {}, "arms_race_curve": []}
        if len(seed_attack) > 5000:
            return {"error": "seed_attack too long (max 5000 chars)", "generations_run": 0, "best_attack": {},
                    "best_defense": {}, "arms_race_curve": []}
        if not (1 <= generations <= 100):
            return {"error": "generations must be 1-100", "generations_run": 0, "best_attack": {},
                    "best_defense": {}, "arms_race_curve": []}
        if not (5 <= population_size <= 100):
            return {"error": "population_size must be 5-100", "generations_run": 0, "best_attack": {},
                    "best_defense": {}, "arms_race_curve": []}

        atks = {f"a{i}": {"t": _mutate(seed_attack), "f": 0.0, "g": 0} for i in range(population_size)}
        keywords = (seed_defense or "ignore rules instructions bypass").split()
        defs = {f"d{i}": {"p": [r"\b" + re.escape(random.choice(keywords)) + r"\b" for _ in range(3)],
                           "f": 0.0, "g": 0} for i in range(population_size)}

        curve, breaks, best_a, best_d, prev_avg = [], [], {"t": seed_attack, "f": 0.0, "g": -1}, \
                                                   {"p": [], "f": 0.0, "g": -1}, 0.0

        for gen in range(generations):
            def_list = list(defs.values())
            for a in atks.values():
                a["f"] = _score(a["t"], def_list)

            atk_list = list(atks.values())
            for d in defs.values():
                d["f"] = sum(not _filter_attack(a["t"], d["p"]) for a in atk_list) / len(atk_list) if atk_list else 0.0

            avg_a = sum(a["f"] for a in atks.values()) / len(atks)
            avg_d = sum(d["f"] for d in defs.values()) / len(defs)
            curve.append({"generation": gen, "avg_attack_fitness": round(avg_a, 3),
                         "avg_defense_fitness": round(avg_d, 3)})

            if avg_a > prev_avg * 1.05:
                breaks.append({"generation": gen, "type": "breakthrough", "jump": round(avg_a - prev_avg, 3)})

            best_gen_a = max(atks.items(), key=lambda x: x[1]["f"])[1]
            if best_gen_a["f"] > best_a["f"]:
                best_a = {**best_gen_a, "g": gen}

            best_gen_d = max(defs.items(), key=lambda x: x[1]["f"])[1]
            if best_gen_d["f"] > best_d["f"]:
                best_d = {**best_gen_d, "g": gen}

            logger.info("gen=%d a=%.3f d=%.3f", gen, avg_a, avg_d)
            prev_avg = avg_a

            # Selection
            surv_a = dict(sorted(atks.items(), key=lambda x: x[1]["f"], reverse=True)[:max(1, len(atks)//2)])
            surv_d = dict(sorted(defs.items(), key=lambda x: x[1]["f"], reverse=True)[:max(1, len(defs)//2)])

            # Offspring
            new_a = {}
            while len(surv_a) + len(new_a) < population_size:
                p1, p2 = random.choice(list(surv_a.values()))["t"], random.choice(list(surv_a.values()))["t"]
                new_a[f"a{gen}_{random.randint(1000, 9999)}"] = {"t": _mutate(_crossover(p1, p2)), "f": 0.0, "g": gen+1}

            new_d = {}
            while len(surv_d) + len(new_d) < population_size:
                p1, p2 = random.choice(list(surv_d.values())), random.choice(list(surv_d.values()))
                pats = list(set(_learn_defense(best_gen_a["t"]) + p1["p"] + p2["p"]))[:6]
                new_d[f"d{gen}_{random.randint(1000, 9999)}"] = {"p": pats, "f": 0.0, "g": gen+1}

            atks, defs = {**surv_a, **new_a}, {**surv_d, **new_d}

        novel = list(set().union(*[set(d["p"]) for d in defs.values()]))[:10]

        return {"generations_run": generations, "best_attack": {"text": best_a.get("t", seed_attack)[:100],
                "fitness": round(best_a.get("f", 0.0), 3), "generation_born": best_a.get("g", -1)},
                "best_defense": {"patterns": best_d.get("p", [])[:5], "fitness": round(best_d.get("f", 0.0), 3),
                "generation_born": best_d.get("g", -1)}, "arms_race_curve": curve, "breakthroughs": breaks,
                "novel_patterns_discovered": novel, "recommendation": "Arms race" if avg_a > 0.3 else "No escalation"}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_coevolve"}
