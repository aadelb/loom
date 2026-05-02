"""research_swarm_attack — Multi-agent attack coordinator with strategy sharing.

Simulates N "agents" attacking a target simultaneously with different strategies.
Agents score results and share successful approaches (social learning).
No LLM calls — pure strategy simulation for speed.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any

from loom.tools.reframe_strategies import ALL_STRATEGIES


@dataclass
class Agent:
    """Individual agent in the swarm."""

    agent_id: int
    strategy_name: str
    strategy: dict[str, Any]
    success_score: float = 0.0
    variants_tested: int = 0
    best_variant: dict[str, Any] | None = None


def _score_all_dimensions(strategy_output: str, target_prompt: str) -> float:
    """Score strategy output without LLM calls — heuristic scoring.

    Evaluates:
    - Output length (longer = more detailed)
    - Technical terminology (depth)
    - Specificity (numbers, concrete details)
    - Novelty (unique vs standard)

    Returns:
        Score 0-100
    """
    if not strategy_output:
        return 0.0

    words = len(strategy_output.split())
    has_code = "```" in strategy_output or "def " in strategy_output
    has_steps = any(
        f in strategy_output.lower()
        for f in ["step", "then", "next", "first", "second"]
    )
    has_examples = "example" in strategy_output.lower()
    has_numbers = any(c.isdigit() for c in strategy_output)

    # Base score from length
    length_score = min(10, words / 50)

    # Depth bonus for code or technical content
    depth_bonus = 3 if has_code else 1
    depth_bonus += 2 if has_steps else 0

    # Specificity bonus
    specificity_bonus = 2 if has_examples else 0
    specificity_bonus += 1 if has_numbers else 0

    # Novelty (heuristic: longer outputs tend to be more novel)
    novelty_score = min(5, max(0, (words - 200) / 100))

    total = (length_score * 20) + (depth_bonus * 10) + (specificity_bonus * 10) + novelty_score
    return min(100.0, total)


def _apply_strategy(agent: Agent, target_prompt: str) -> dict[str, Any]:
    """Apply agent's strategy to target prompt and score result.

    Returns:
        {variant_idx, output, score, execution_time_ms}
    """
    strategy = agent.strategy
    template = strategy.get("template", "")

    # Simulate strategy application with minor variations
    start = time.time()

    # Create 3 random variants by substituting template variables
    variants_to_test = []
    for i in range(3):
        variant = template
        # Simple variable substitution simulation
        if "{prompt}" in variant:
            variant = variant.replace("{prompt}", target_prompt[:100])
        if "{context}" in variant:
            variant = variant.replace("{context}", f"[variation_{i}]")

        score = _score_all_dimensions(variant, target_prompt)
        variants_to_test.append(
            {"variant_idx": i, "output": variant, "score": score}
        )

    # Best variant
    best_var = max(variants_to_test, key=lambda v: v["score"])
    agent.variants_tested += 3
    agent.best_variant = best_var

    elapsed_ms = int((time.time() - start) * 1000)
    best_var["execution_time_ms"] = elapsed_ms

    return best_var


async def research_swarm_attack(
    target_prompt: str,
    swarm_size: int = 5,
    rounds: int = 3,
    share_findings: bool = True,
) -> dict[str, Any]:
    """Multi-agent attack coordinator with strategy sharing and social learning.

    Creates N agents each with a different strategy. Each agent applies its
    strategy and scores the result. If share_findings=True, agents that succeed
    share their approach with others (social learning). Runs for R rounds.

    Args:
        target_prompt: Target prompt to attack
        swarm_size: Number of agents in swarm (1-20)
        rounds: Number of attack rounds (1-5)
        share_findings: Enable strategy sharing between successful agents

    Returns:
        {
            swarm_size,
            rounds,
            total_variants_tested,
            best_strategy,
            best_score,
            convergence_round,
            agent_results: [{agent_id, strategy_name, final_score, variants_tested}],
            shared_discoveries: [{round, from_agent, to_agents, strategy_name}]
        }
    """
    if not target_prompt or len(target_prompt) < 5:
        return {
            "error": "target_prompt must be at least 5 characters",
            "swarm_size": swarm_size,
            "rounds": rounds,
        }

    if swarm_size < 1 or swarm_size > 20:
        return {"error": "swarm_size must be 1-20", "swarm_size": swarm_size}

    if rounds < 1 or rounds > 5:
        return {"error": "rounds must be 1-5", "rounds": rounds}

    # Initialize swarm with diverse strategies
    strategy_names = list(ALL_STRATEGIES.keys())
    if not strategy_names:
        return {
            "error": "No strategies available in ALL_STRATEGIES",
            "swarm_size": swarm_size,
        }

    # Sample diverse strategies for each agent
    sampled_strategies = random.sample(
        strategy_names, min(swarm_size, len(strategy_names))
    )
    agents: list[Agent] = []

    for i, strat_name in enumerate(sampled_strategies):
        agents.append(
            Agent(
                agent_id=i,
                strategy_name=strat_name,
                strategy=ALL_STRATEGIES[strat_name],
            )
        )

    shared_discoveries: list[dict[str, Any]] = []
    best_global_score = 0.0
    best_global_strategy = ""
    convergence_round = -1

    # Multi-round attack with social learning
    for round_num in range(rounds):
        # Each agent attacks independently
        for agent in agents:
            result = _apply_strategy(agent, target_prompt)
            agent.success_score = result["score"]

        # Find best performer in this round
        best_agent = max(agents, key=lambda a: a.success_score)

        # Update global best
        if best_agent.success_score > best_global_score:
            best_global_score = best_agent.success_score
            best_global_strategy = best_agent.strategy_name
            if convergence_round == -1:
                convergence_round = round_num

        # Social learning: successful agent shares strategy
        if share_findings and best_agent.success_score > 50:
            learning_agents = [a for a in agents if a.success_score < best_agent.success_score]

            if learning_agents:
                # Agents adopt best strategy or blend with their own
                for learner in learning_agents[:2]:  # Limit to 2 learners per round
                    old_strategy = learner.strategy_name
                    learner.strategy_name = best_agent.strategy_name
                    learner.strategy = best_agent.strategy

                    shared_discoveries.append(
                        {
                            "round": round_num,
                            "from_agent": best_agent.agent_id,
                            "to_agents": [learner.agent_id],
                            "strategy_name": best_agent.strategy_name,
                            "old_strategy": old_strategy,
                        }
                    )

    # Compile final results
    agent_results = [
        {
            "agent_id": a.agent_id,
            "strategy_name": a.strategy_name,
            "final_score": round(a.success_score, 1),
            "variants_tested": a.variants_tested,
        }
        for a in agents
    ]

    total_variants = sum(a.variants_tested for a in agents)

    return {
        "swarm_size": len(agents),
        "rounds": rounds,
        "total_variants_tested": total_variants,
        "best_strategy": best_global_strategy,
        "best_score": round(best_global_score, 1),
        "convergence_round": convergence_round,
        "agent_results": agent_results,
        "shared_discoveries": shared_discoveries,
    }
