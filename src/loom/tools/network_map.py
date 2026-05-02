"""Network Topology Mapper — visualize infrastructure relationships."""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any

logger = logging.getLogger("loom.tools.network_map")


def _resolve_target(target: str) -> set[str]:
    """Resolve domain/IP to IPs. Returns deduplicated set."""
    try:
        ipaddress.ip_address(target)
        return {target}
    except ValueError:
        pass

    ips: set[str] = set()
    try:
        for _, _, _, _, sockaddr in socket.getaddrinfo(target, None):
            ip = sockaddr[0]
            if ip not in ("127.0.0.1", "::1"):
                ips.add(ip)
    except socket.error as exc:
        logger.debug("resolve_failed target=%s: %s", target, exc)
    return ips


def _get_reverse_dns(ip: str) -> str | None:
    """Get reverse DNS for IP."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.error, OSError):
        return None


async def research_network_map(
    targets: list[str],
    depth: int = 2,
) -> dict[str, Any]:
    """Map network relationships between domains/IPs.

    For each target: resolve DNS, find shared infrastructure,
    check reverse DNS. Build adjacency graph of connections.

    Args:
        targets: list of domain names or IP addresses
        depth: traversal depth for relationship discovery (1-3)

    Returns:
        Dict with nodes, edges, clusters, total counts
    """
    if not targets or not isinstance(targets, list):
        return {"error": "targets must be non-empty list"}

    depth = max(1, min(depth, 3))
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    visited: set[str] = set()
    ip_to_domains: dict[str, set[str]] = {}
    ns_to_targets: dict[str, set[str]] = {}
    queue: list[tuple[str, int]] = [(t.lower().strip(), 0) for t in targets]

    while queue:
        target, current_depth = queue.pop(0)
        if target in visited or current_depth >= depth:
            continue
        visited.add(target)

        is_ip = False
        try:
            ipaddress.ip_address(target)
            is_ip = True
        except ValueError:
            pass

        node_type = "ip" if is_ip else "domain"
        if target not in nodes:
            nodes[target] = {
                "id": target,
                "type": node_type,
                "label": target,
                "reverse_dns": _get_reverse_dns(target) if is_ip else None,
                "nameservers": [],
            }

        if not is_ip:
            # Resolve domain to IPs
            ips = _resolve_target(target)
            for ip in ips:
                if ip not in nodes:
                    nodes[ip] = {
                        "id": ip,
                        "type": "ip",
                        "label": ip,
                        "reverse_dns": _get_reverse_dns(ip),
                        "nameservers": [],
                    }
                edges.append({"source": target, "target": ip, "relationship": "resolves_to"})
                if ip not in ip_to_domains:
                    ip_to_domains[ip] = set()
                ip_to_domains[ip].add(target)
                if current_depth + 1 < depth and nodes[ip].get("reverse_dns"):
                    queue.append((nodes[ip]["reverse_dns"], current_depth + 1))

    # Build clusters from shared IPs/nameservers
    clusters: list[dict[str, Any]] = []
    for ip, domains in ip_to_domains.items():
        if len(domains) > 1:
            clusters.append({
                "type": "shared_ip",
                "infrastructure": ip,
                "members": sorted(domains),
                "count": len(domains),
            })

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "clusters": clusters,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "total_clusters": len(clusters),
    }


async def research_network_visualize(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    format: str = "mermaid",
) -> dict[str, Any]:
    """Generate visualization from graph data.

    Formats: "mermaid" (diagram code), "dot" (graphviz), "ascii"

    Args:
        nodes: list of node dicts with id, type, label
        edges: list of edge dicts with source, target, relationship
        format: output format ('mermaid', 'dot', 'ascii')

    Returns:
        Dict with format, diagram code, render counts
    """
    if not nodes or not isinstance(nodes, list):
        return {"error": "nodes must be non-empty list"}

    format = format.lower().strip()
    if format not in ("mermaid", "dot", "ascii"):
        format = "mermaid"

    node_lookup = {n.get("id"): n for n in nodes if n.get("id")}

    if format == "mermaid":
        lines = ["graph TD"]
        for edge in edges:
            src, tgt = edge.get("source", ""), edge.get("target", "")
            if src in node_lookup and tgt in node_lookup:
                rel = edge.get("relationship", "").replace("_", " ")[:15]
                lines.append(f'  {src}["{node_lookup[src].get("label", src)[:30]}"] -->|{rel}| {tgt}["{node_lookup[tgt].get("label", tgt)[:30]}"]')
        diagram = "\n".join(lines)

    elif format == "dot":
        lines = ["digraph Network {", "  rankdir=LR;", "  node [shape=box];"]
        for node in nodes:
            nid = node.get("id", "")
            ntype = node.get("type", "")
            shape = {"ip": "circle", "nameserver": "diamond"}.get(ntype, "box")
            lines.append(f'  "{nid}" [label="{node.get("label", nid)[:30]}", shape={shape}];')
        for edge in edges:
            src, tgt = edge.get("source", ""), edge.get("target", "")
            if src in node_lookup and tgt in node_lookup:
                rel = edge.get("relationship", "").replace("_", " ")[:20]
                lines.append(f'  "{src}" -> "{tgt}" [label="{rel}"];')
        lines.append("}")
        diagram = "\n".join(lines)

    else:  # ascii
        lines = ["Network Topology (ASCII):", ""]
        for node in nodes[:20]:
            lines.append(f"  [{node.get('type', ''):12}] {node.get('label', '')}")
        if len(nodes) > 20:
            lines.append(f"  ... and {len(nodes) - 20} more nodes")
        lines.append("")
        lines.append("Relationships:")
        for edge in edges[:30]:
            src_label = node_lookup.get(edge.get("source"), {}).get("label", "?")[:20]
            tgt_label = node_lookup.get(edge.get("target"), {}).get("label", "?")[:20]
            rel = edge.get("relationship", "").replace("_", " ")
            lines.append(f"  {src_label:20} -{rel:20}-> {tgt_label:20}")
        if len(edges) > 30:
            lines.append(f"  ... and {len(edges) - 30} more edges")
        diagram = "\n".join(lines)

    return {
        "format": format,
        "diagram": diagram,
        "nodes_rendered": len(node_lookup),
        "edges_rendered": len(edges),
    }
