"""research_graph_analyze and research_transaction_graph — Pure Python graph tools.

DEPRECATED: Use research_graph() unified interface instead.
- research_graph_analyze → use research_graph(action="visualize", ...) for visualization

Provides PageRank, community detection, centrality, shortest path algorithms
and blockchain transaction graph building via blockchain.info. No networkx/pytorch_geometric.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

import httpx
from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json, fetch_text

logger = logging.getLogger("loom.tools.graph_analysis")


def _pagerank(nodes: dict[str, dict[str, Any]], edges: dict[str, list[str]], iterations: int = 20, damping: float = 0.85) -> dict[str, float]:
    """Compute PageRank scores for nodes.

    Handles dangling nodes (zero out-degree) by redistributing their mass.
    """
    n = len(nodes)
    if n == 0:
        return {}
    rank = {node_id: 1.0 / n for node_id in nodes}
    # Only count outgoing edges to valid nodes
    out_degree = {node_id: len([t for t in edges.get(node_id, []) if t in nodes]) for node_id in nodes}
    incoming: dict[str, list[str]] = defaultdict(list)
    for src, targets in edges.items():
        for tgt in targets:
            if tgt in nodes:
                incoming[tgt].append(src)
    for _ in range(iterations):
        new_rank = {}
        dangling_mass = sum(rank[n_id] for n_id in nodes if out_degree[n_id] == 0)
        for node_id in nodes:
            rank_sum = sum(rank[src] / out_degree[src] for src in incoming.get(node_id, []) if out_degree[src] > 0)
            new_rank[node_id] = (1.0 - damping) / n + damping * (rank_sum + dangling_mass / n)
        rank = new_rank
    return rank


def _centrality(nodes: dict[str, dict[str, Any]], edges: dict[str, list[str]]) -> dict[str, float]:
    """Compute in-degree and out-degree centrality for directed graphs.

    Returns average of normalized in-degree and out-degree (range [0, 1]).
    """
    if not nodes:
        return {}
    n = len(nodes)
    centrality = {}
    for node_id in nodes:
        # Count only edges to/from valid nodes
        out_deg = len([t for t in edges.get(node_id, []) if t in nodes])
        in_deg = sum(1 for targets in edges.values() if node_id in targets)
        # Normalize each separately (range [0, 1]) for directed graphs
        norm_out = out_deg / (n - 1) if n > 1 else 0.0
        norm_in = in_deg / (n - 1) if n > 1 else 0.0
        # Return average to get overall centrality
        centrality[node_id] = (norm_out + norm_in) / 2.0
    return centrality


def _shortest_path(nodes: dict[str, dict[str, Any]], edges: dict[str, list[str]], source: str, target: str) -> dict[str, Any]:
    """Compute shortest path using BFS.

    Distance is the number of edges (hops), not nodes.
    """
    if source not in nodes or target not in nodes:
        return {"path": None, "distance": -1}
    if source == target:
        return {"path": [source], "distance": 0}
    queue = deque([(source, [source])])
    visited = {source}
    while queue:
        node, path = queue.popleft()
        for neighbor in edges.get(node, []):
            if neighbor == target:
                full_path = path + [neighbor]
                return {"path": full_path, "distance": len(full_path) - 1}
            if neighbor not in visited and neighbor in nodes:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return {"path": None, "distance": -1}


def _community_detect(node_list: list[str], adj: dict[int, set[int]]) -> dict[int, int]:
    """Label propagation for community detection.

    Stops early if converged. Uses Counter for deterministic label selection.
    """
    from collections import Counter

    labels = {i: i for i in range(len(node_list))}
    max_iterations = 20
    for iteration in range(max_iterations):
        new_labels = labels.copy()
        for idx in range(len(node_list)):
            neighbors = list(adj.get(idx, set()))
            if neighbors:
                neighbor_labels = [labels[n] for n in neighbors]
                # Use Counter.most_common() for deterministic label selection
                label_counts = Counter(neighbor_labels)
                # If neighbor exists, take most common; tie-break by smallest label
                most_common = label_counts.most_common(1)[0][0]
                new_labels[idx] = most_common
        # Early convergence check
        if new_labels == labels:
            break
        labels = new_labels
    return labels


@handle_tool_errors("research_graph_analyze")
async def research_graph_analyze(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], algorithm: str = "pagerank") -> dict[str, Any]:
    """Analyze graph using PageRank, community detection, centrality, or shortest_path.

    DEPRECATED: Use research_graph(action="visualize", nodes=..., edges=...) instead.
    """
    logger.warning(
        "research_graph_analyze is deprecated; use research_graph(action='visualize', ...) instead"
    )
    try:
        node_map: dict[str, dict[str, Any]] = {n["id"]: n for n in nodes if "id" in n}
        if not node_map:
            return {"algorithm": algorithm, "results": None, "metrics": {}, "error": "No valid nodes"}

        edge_map: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            if isinstance(edge, dict):
                src, tgt = edge.get("source"), edge.get("target")
                if src and tgt and src in node_map and tgt in node_map:
                    edge_map[src].append(tgt)

        if algorithm == "pagerank":
            scores = _pagerank(node_map, edge_map)
            results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:20]
            metrics = {"total_nodes": len(node_map), "total_edges": sum(len(t) for t in edge_map.values()), "top_score": results[0][1] if results else 0.0}

        elif algorithm == "community_detection":
            node_list = list(node_map.keys())
            node_idx = {nid: i for i, nid in enumerate(node_list)}
            adj: dict[int, set[int]] = defaultdict(set)
            for src, targets in edge_map.items():
                for tgt in targets:
                    si, ti = node_idx.get(src), node_idx.get(tgt)
                    if si is not None and ti is not None:
                        adj[si].add(ti)
                        adj[ti].add(si)
            labels = _community_detect(node_list, adj)
            communities: dict[int, list[str]] = defaultdict(list)
            for i, node_id in enumerate(node_list):
                communities[labels[i]].append(node_id)
            results = [{"community": cid, "members": mems} for cid, mems in sorted(communities.items())]
            metrics = {"total_nodes": len(node_map), "num_communities": len(communities), "largest_community_size": max((len(m) for m in communities.values()), default=0)}

        elif algorithm == "centrality":
            scores = _centrality(node_map, edge_map)
            results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:20]
            metrics = {"total_nodes": len(node_map), "total_edges": sum(len(t) for t in edge_map.values()), "highest_centrality": results[0][1] if results else 0.0}

        elif algorithm == "shortest_path":
            if len(node_map) < 2:
                return {"algorithm": algorithm, "results": None, "metrics": {}, "error": "Need at least 2 nodes"}
            source, target = next(iter(node_map.keys())), list(node_map.keys())[-1]
            results = _shortest_path(node_map, edge_map, source, target)
            metrics = {"source": source, "target": target, "path_length": results["distance"]}
        else:
            return {"algorithm": algorithm, "results": None, "metrics": {}, "error": f"Unknown algorithm: {algorithm}"}

        return {"algorithm": algorithm, "results": results, "metrics": metrics, "error": None}

    except Exception as e:
        logger.error("graph_analyze error: %s", exc_info=True)
        return {"algorithm": algorithm, "results": None, "metrics": {}, "error": str(e)}


@handle_tool_errors("research_transaction_graph")
async def research_transaction_graph(addresses: list[str], chain: str = "bitcoin") -> dict[str, Any]:
    """Build transaction graph from blockchain addresses via blockchain.info.

    DEPRECATED: Use research_graph() for unified graph interface.
    """
    logger.warning(
        "research_transaction_graph is deprecated; use research_graph() for unified interface"
    )
    if chain not in ("bitcoin", "ethereum"):
        return {"nodes": [], "edges": [], "clusters": [], "suspicious_patterns": [], "error": f"Unsupported chain: {chain}"}

    nodes, edges, visited = [], [], set()
    suspicious_patterns = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for addr in addresses:
            if addr in visited or not addr:
                continue
            visited.add(addr)
            try:
                if chain == "bitcoin":
                    resp = await client.get(f"https://blockchain.info/q/addressbalance/{addr}")
                    if resp.status_code == 200:
                        balance = int(resp.text)
                        nodes.append({"id": addr, "type": "address", "chain": "bitcoin", "balance": balance})
                        if balance > 1_000_000_000:
                            suspicious_patterns.append({"type": "high_balance", "address": addr, "balance_sat": balance})

                    data = await fetch_json(client, f"https://blockchain.info/address/{addr}?format=json&limit=5")
                    if data:
                        if data.get("n_tx", 0) > 100:
                            suspicious_patterns.append({"type": "high_transaction_volume", "address": addr, "tx_count": data["n_tx"]})
                        for tx in data.get("txs", [])[:5]:
                            for inp in tx.get("inputs", [])[:3]:
                                prev_addr = inp.get("prev_out", {}).get("addr")
                                if prev_addr and prev_addr not in visited:
                                    visited.add(prev_addr)
                                    nodes.append({"id": prev_addr, "type": "address", "chain": "bitcoin"})
                                    edges.append({"source": prev_addr, "target": addr, "type": "transaction"})
                            for outp in tx.get("outputs", [])[:3]:
                                next_addr = outp.get("addr")
                                if next_addr and next_addr not in visited:
                                    visited.add(next_addr)
                                    nodes.append({"id": next_addr, "type": "address", "chain": "bitcoin"})
                                    edges.append({"source": addr, "target": next_addr, "type": "transaction"})
            except Exception as e:
                logger.debug("blockchain.info fetch failed for %s: %s", addr, e)

    # Build adjacency list for DIRECTED edges (transactions flow one way)
    adj_out: dict[str, set[str]] = defaultdict(set)
    adj_in: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        src, tgt = edge.get("source"), edge.get("target")
        if src and tgt:
            adj_out[src].add(tgt)
            adj_in[tgt].add(src)

    clusters = []
    visited_cluster: set[str] = set()
    for node in nodes:
        node_id = node["id"]
        if node_id in visited_cluster:
            continue
        # Mark as visited before BFS to avoid revisiting
        cluster: list[str] = []
        queue: deque[str] = deque([node_id])
        cluster_visited: set[str] = {node_id}
        visited_cluster.add(node_id)
        while queue:
            current = queue.popleft()
            cluster.append(current)
            # Follow both outgoing and incoming edges for clustering
            for neighbor in adj_out.get(current, set()) | adj_in.get(current, set()):
                if neighbor not in cluster_visited:
                    cluster_visited.add(neighbor)
                    visited_cluster.add(neighbor)
                    queue.append(neighbor)
        if len(cluster) > 1:
            clusters.append({"size": len(cluster), "members": cluster})

    return {"nodes": nodes, "edges": edges, "clusters": sorted(clusters, key=lambda c: c["size"], reverse=True)[:10], "suspicious_patterns": suspicious_patterns, "error": None}
