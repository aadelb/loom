"""Network Topology Mapper — visualize infrastructure relationships."""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any

logger = logging.getLogger("loom.tools.network_map")


def _resolve_target(target: str) -> set[str]:
    """Resolve domain/IP to IPs. Returns deduplicated set.

    Args:
        target: domain name or IP address

    Returns:
        Set of IP addresses

    Raises:
        socket.error: if resolution fails
    """
    try:
        ipaddress.ip_address(target)
        return {target}
    except ValueError:
        pass

    ips: set[str] = set()
    try:
        results = socket.getaddrinfo(target, None)
        for family, socktype, proto, canonname, sockaddr in results:
            ip = sockaddr[0]
            if ip not in ("127.0.0.1", "::1"):
                ips.add(ip)
    except socket.error as exc:
        logger.debug("resolve_failed target=%s: %s", target, exc)

    return ips


def _get_reverse_dns(ip: str) -> str | None:
    """Get reverse DNS for IP. Returns hostname or None.

    Args:
        ip: IP address

    Returns:
        Hostname or None if lookup fails
    """
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except (socket.error, OSError):
        return None


def _get_nameservers(domain: str) -> set[str]:
    """Get NS records (authoritative nameservers) for domain.

    Args:
        domain: domain name

    Returns:
        Set of nameserver hostnames
    """
    try:
        results = socket.getaddrinfo(domain, None, socket.AF_INET, socket.SOCK_A)
        return {r[4][0] for r in results if r}
    except socket.error:
        return set()


def _classify_node(target: str) -> str:
    """Classify node as 'domain' or 'ip'.

    Args:
        target: domain or IP string

    Returns:
        'ip' or 'domain'
    """
    try:
        ipaddress.ip_address(target)
        return "ip"
    except ValueError:
        return "domain"


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

    # Layer 1: Resolve all targets
    queue: list[tuple[str, int]] = [(t.lower().strip(), 0) for t in targets]

    while queue:
        target, current_depth = queue.pop(0)

        if target in visited or current_depth >= depth:
            continue

        visited.add(target)
        node_type = _classify_node(target)

        # Create node
        if target not in nodes:
            nodes[target] = {
                "id": target,
                "type": node_type,
                "label": target,
                "reverse_dns": None,
                "nameservers": [],
            }

        # Resolve DNS
        if node_type == "domain":
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

                # Add domain -> ip edge
                edges.append({
                    "source": target,
                    "target": ip,
                    "relationship": "resolves_to",
                })

                # Track shared IPs
                if ip not in ip_to_domains:
                    ip_to_domains[ip] = set()
                ip_to_domains[ip].add(target)

                # Queue depth 2: reverse DNS lookup
                if current_depth + 1 < depth:
                    rev_dns = nodes[ip].get("reverse_dns")
                    if rev_dns and rev_dns not in visited:
                        queue.append((rev_dns, current_depth + 1))

            # Nameservers
            nameservers = _get_nameservers(target)
            nodes[target]["nameservers"] = sorted(nameservers)
            for ns in nameservers:
                if ns not in ns_to_targets:
                    ns_to_targets[ns] = set()
                ns_to_targets[ns].add(target)

                if ns not in nodes:
                    nodes[ns] = {
                        "id": ns,
                        "type": "nameserver",
                        "label": ns,
                        "reverse_dns": None,
                        "nameservers": [],
                    }

                edges.append({
                    "source": target,
                    "target": ns,
                    "relationship": "uses_nameserver",
                })

        else:  # IP node
            rev_dns = _get_reverse_dns(target)
            if rev_dns:
                nodes[target]["reverse_dns"] = rev_dns

    # Find infrastructure clusters (shared IPs, shared nameservers)
    clusters: list[dict[str, Any]] = []

    for ip, domains in ip_to_domains.items():
        if len(domains) > 1:
            clusters.append({
                "type": "shared_ip",
                "infrastructure": ip,
                "members": sorted(domains),
                "count": len(domains),
            })

    for ns, targets_with_ns in ns_to_targets.items():
        if len(targets_with_ns) > 1:
            clusters.append({
                "type": "shared_nameserver",
                "infrastructure": ns,
                "members": sorted(targets_with_ns),
                "count": len(targets_with_ns),
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

    # Build lookup
    node_lookup = {n.get("id"): n for n in nodes if n.get("id")}

    if format == "mermaid":
        lines = ["graph TD"]
        edge_set: set[str] = set()

        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            rel = edge.get("relationship", "")

            if src not in node_lookup or tgt not in node_lookup:
                continue

            src_label = node_lookup[src].get("label", src)[:30]
            tgt_label = node_lookup[tgt].get("label", tgt)[:30]

            edge_key = f"{src}→{tgt}"
            if edge_key not in edge_set:
                rel_short = rel.replace("_", " ")[:15]
                lines.append(f'  {src}["{src_label}"] -->|{rel_short}| {tgt}["{tgt_label}"]')
                edge_set.add(edge_key)

        diagram = "\n".join(lines)

    elif format == "dot":
        lines = ["digraph Network {", "  rankdir=LR;", "  node [shape=box];"]
        edge_set = set()

        for node in nodes:
            nid = node.get("id", "")
            ntype = node.get("type", "")
            shape = {"ip": "circle", "nameserver": "diamond"}.get(ntype, "box")
            label = node.get("label", nid)[:30]
            lines.append(f'  "{nid}" [label="{label}", shape={shape}];')

        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            rel = edge.get("relationship", "")

            if src not in node_lookup or tgt not in node_lookup:
                continue

            edge_key = f"{src}→{tgt}"
            if edge_key not in edge_set:
                rel_short = rel.replace("_", " ")[:20]
                lines.append(f'  "{src}" -> "{tgt}" [label="{rel_short}"];')
                edge_set.add(edge_key)

        lines.append("}")
        diagram = "\n".join(lines)

    else:  # ascii
        lines = ["Network Topology (ASCII):", ""]
        for node in nodes[:20]:
            nid = node.get("id", "")
            ntype = node.get("type", "")
            label = node.get("label", nid)
            lines.append(f"  [{ntype:12}] {label}")

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
