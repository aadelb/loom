"""research_graph_analyze and research_transaction_graph — Pure Python graph tools.

Provides PageRank, community detection, centrality, shortest path algorithms
and blockchain transaction graph building via blockchain.info. No networkx/pytorch_geometric.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.graph_analysis")


def _pagerank(nodes: dict[str, dict[str, Any]], edges: dict[str, list[str]], iterations: int = 20, damping: float = 0.85) -> dict[str, float]:
    """Compute PageRank scores for nodes."""
    n = len(nodes)
    if n == 0:
        return {}
    rank = {node_id: 1.0 / n for node_id in nodes}
    out_degree = {node_id: len(edges.get(node_id, [])) for node_id in nodes}
    incoming: dict[str, list[str]] = defaultdict(list)
    for src, targets in edges.items():
        for tgt in targets:
            if tgt in nodes:
                incoming[tgt].append(src)
    for _ in range(iterations):
        new_rank = {}
        for node_id in nodes:
            rank_sum = sum(rank[src] / out_degree[src] for src in incoming.get(node_id, []) if out_degree[src] > 0)
            new_rank[node_id] = (1.0 - damping) / n + damping * rank_sum
        rank = new_rank
    return rank


def _centrality(nodes: dict[str, dict[str, Any]], edges: dict[str, list[str]]) -> dict[str, float]:
    """Compute degree centrality for nodes."""
    if not nodes:
        return {}
    n = len(nodes)
    centrality = {}
    for node_id in nodes:
        out_deg = len(edges.get(node_id, []))
        in_deg = sum(1 for targets in edges.values() if node_id in targets)
        centrality[node_id] = (out_deg + in_deg) / (2 * (n - 1)) if n > 1 else 0.0
    return centrality


def _shortest_path(nodes: dict[str, dict[str, Any]], edges: dict[str, list[str]], source: str, target: str) -> dict[str, Any]:
    """Compute shortest path using BFS."""
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
                return {"path": path + [neighbor], "distance": len(path)}
            if neighbor not in visited and neighbor in nodes:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return {"path": None, "distance": -1}


def _community_detect(node_list: list[str], adj: dict[int, set[int]]) -> dict[int, int]:
    """Label propagation for community detection."""
    labels = {i: i for i in range(len(node_list))}
    for _ in range(5):
        new_labels = labels.copy()
        for idx in range(len(node_list)):
            neighbors = list(adj.get(idx, set()))
            if neighbors:
                neighbor_labels = [labels[n] for n in neighbors]
                new_labels[idx] = max(set(neighbor_labels), key=neighbor_labels.count)
        labels = new_labels
    return labels


async def research_graph_analyze(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], algorithm: str = "pagerank") -> dict[str, Any]:
    """Analyze graph using PageRank, community detection, centrality, or shortest_path."""
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


async def research_transaction_graph(addresses: list[str], chain: str = "bitcoin") -> dict[str, Any]:
    """Build transaction graph from blockchain addresses via blockchain.info."""
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

                    tx_resp = await client.get(f"https://blockchain.info/address/{addr}?format=json&limit=5")
                    if tx_resp.status_code == 200:
                        data = tx_resp.json()
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

    adj: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        src, tgt = edge.get("source"), edge.get("target")
        if src and tgt:
            adj[src].add(tgt)
            adj[tgt].add(src)

    clusters = []
    visited_cluster = set()
    for node in nodes:
        node_id = node["id"]
        if node_id in visited_cluster:
            continue
        cluster, queue, cluster_visited = [], deque([node_id]), {node_id}
        while queue:
            current = queue.popleft()
            cluster.append(current)
            for neighbor in adj.get(current, set()):
                if neighbor not in cluster_visited:
                    cluster_visited.add(neighbor)
                    queue.append(neighbor)
        visited_cluster.update(cluster)
        if len(cluster) > 1:
            clusters.append({"size": len(cluster), "members": cluster})

    return {"nodes": nodes, "edges": edges, "clusters": sorted(clusters, key=lambda c: c["size"], reverse=True)[:10], "suspicious_patterns": suspicious_patterns, "error": None}
