"""Task dependency resolver for ordering complex research workflows.

Pure algorithms: topological sort (Kahn's algorithm) and critical path (longest path).
Detects circular dependencies and identifies parallel execution opportunities.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from typing import Any

logger = logging.getLogger("loom.tools.task_resolver")


async def research_resolve_order(
    tasks: list[dict],
) -> dict[str, Any]:
    """Resolve task execution order using topological sort (Kahn's algorithm).

    Detects circular dependencies and identifies tasks that can run in parallel.

    Args:
        tasks: List of task dicts with keys:
            - name (str): Unique task identifier
            - depends_on (list[str]): List of task names this task depends on

    Returns:
        dict with keys:
            - execution_order (list[str]): Linear ordering for sequential execution
            - parallel_groups (list[list[str]]): Tasks grouped by dependency level
            - has_cycles (bool): Whether circular dependencies exist
            - cycle_nodes (list[str]): Names of tasks involved in cycles (if any)

    Example:
        tasks = [
            {"name": "fetch_data", "depends_on": []},
            {"name": "parse", "depends_on": ["fetch_data"]},
            {"name": "validate", "depends_on": ["parse"]},
            {"name": "transform", "depends_on": ["parse"]},
            {"name": "export", "depends_on": ["validate", "transform"]}
        ]
        result = await research_resolve_order(tasks)
        # execution_order: ["fetch_data", "parse", "validate", "transform", "export"]
        # parallel_groups: [["fetch_data"], ["parse"], ["validate", "transform"], ["export"]]
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _resolve_order_sync, tasks)


def _resolve_order_sync(tasks: list[dict]) -> dict[str, Any]:
    """Synchronous topological sort implementation."""
    name_to_deps = {}
    all_names = set()

    for task in tasks:
        name = task.get("name")
        deps = task.get("depends_on", [])
        if not name:
            continue
        name_to_deps[name] = set(deps)
        all_names.add(name)

    in_degree = {name: len(name_to_deps.get(name, set())) for name in all_names}
    graph = defaultdict(set)

    for name, deps in name_to_deps.items():
        for dep in deps:
            if dep in all_names:
                graph[dep].add(name)

    queue = deque([n for n in all_names if in_degree[n] == 0])
    execution_order = []
    visited = set()

    while queue:
        node = queue.popleft()
        execution_order.append(node)
        visited.add(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    has_cycles = len(visited) != len(all_names)
    cycle_nodes = sorted(all_names - visited) if has_cycles else []

    parallel_groups = _compute_parallel_groups(name_to_deps, all_names, execution_order)

    return {
        "execution_order": execution_order,
        "parallel_groups": parallel_groups,
        "has_cycles": has_cycles,
        "cycle_nodes": cycle_nodes,
    }


def _compute_parallel_groups(
    name_to_deps: dict[str, set[str]], all_names: set[str], execution_order: list[str]
) -> list[list[str]]:
    """Group tasks by dependency level for parallel execution."""
    if not execution_order:
        return []

    depth = {}
    for name in execution_order:
        deps = name_to_deps.get(name, set())
        if not deps:
            depth[name] = 0
        else:
            valid_deps = [d for d in deps if d in depth]
            depth[name] = max((depth[d] for d in valid_deps), default=0) + 1

    groups_dict = defaultdict(list)
    for name in execution_order:
        groups_dict[depth[name]].append(name)

    return [groups_dict[i] for i in sorted(groups_dict.keys())]


async def research_critical_path(
    tasks: list[dict],
) -> dict[str, Any]:
    """Find critical path (longest dependency chain) and parallel opportunities.

    Args:
        tasks: List of task dicts with keys:
            - name (str): Unique task identifier
            - depends_on (list[str]): List of task names this task depends on
            - duration_minutes (int): Time to complete task (must be >= 1)

    Returns:
        dict with keys:
            - critical_path (list[str]): Task names in longest path
            - total_duration_minutes (int): Sum of durations on critical path
            - parallel_opportunities (int): Non-critical tasks that can run in parallel
            - bottleneck_task (str): Task with highest impact on total time

    Example:
        tasks = [
            {"name": "fetch", "depends_on": [], "duration_minutes": 5},
            {"name": "parse", "depends_on": ["fetch"], "duration_minutes": 3},
            {"name": "validate", "depends_on": ["parse"], "duration_minutes": 2},
            {"name": "transform", "depends_on": ["parse"], "duration_minutes": 1}
        ]
        result = await research_critical_path(tasks)
        # critical_path: ["fetch", "parse", "validate"]
        # total_duration_minutes: 10
        # parallel_opportunities: 1 (transform can run alongside validate)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _critical_path_sync, tasks)


def _critical_path_sync(tasks: list[dict]) -> dict[str, Any]:
    """Synchronous critical path calculation using dynamic programming."""
    name_to_task = {}
    all_names = set()

    for task in tasks:
        name = task.get("name")
        deps = task.get("depends_on", [])
        duration = task.get("duration_minutes", 0)
        if not name or duration < 1:
            continue
        name_to_task[name] = {"deps": set(deps), "duration": duration}
        all_names.add(name)

    max_path = {}
    paths = {}

    def compute_longest_path(node: str) -> tuple[int, list[str]]:
        """Recursive with memoization: returns (duration, path)."""
        if node in max_path:
            return (max_path[node], paths[node])

        deps = name_to_task[node]["deps"]
        valid_deps = [d for d in deps if d in all_names]

        if not valid_deps:
            dur = name_to_task[node]["duration"]
            max_path[node] = dur
            paths[node] = [node]
            return (dur, [node])

        sub_durations = [compute_longest_path(d) for d in valid_deps]
        max_sub_dur, max_sub_path = max(sub_durations, key=lambda x: x[0])
        total_dur = max_sub_dur + name_to_task[node]["duration"]

        max_path[node] = total_dur
        paths[node] = max_sub_path + [node]
        return (total_dur, paths[node])

    if not all_names:
        return {
            "critical_path": [],
            "total_duration_minutes": 0,
            "parallel_opportunities": 0,
            "bottleneck_task": "",
        }

    for name in all_names:
        compute_longest_path(name)

    critical_dur, critical_path_list = max(
        ((max_path[n], paths[n]) for n in all_names), key=lambda x: x[0]
    )

    critical_set = set(critical_path_list)
    parallel_count = len(all_names) - len(critical_set)

    bottleneck = ""
    if critical_path_list:
        bottleneck = max(
            critical_path_list, key=lambda n: name_to_task[n]["duration"]
        )

    return {
        "critical_path": critical_path_list,
        "total_duration_minutes": critical_dur,
        "parallel_opportunities": parallel_count,
        "bottleneck_task": bottleneck,
    }
