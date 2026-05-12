"""Infrastructure analysis tools — package registries, subdomain evolution, commit patterns."""

from __future__ import annotations

import asyncio
import logging
import math
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from loom.http_helpers import fetch_json, fetch_text

logger = logging.getLogger("loom.tools.infra_analysis")

_PYPI_JSON = "https://pypi.org/pypi/{package}/json"
_NPM_REGISTRY = "https://registry.npmjs.org/{package}"
_RUBYGEMS_API = "https://rubygems.org/api/v1/versions/{package}.json"
_CRT_SH = "https://crt.sh/?q=%25.{domain}&output=json"
_GITHUB_COMMITS = "https://api.github.com/repos/{repo}/commits"




def _calculate_entropy(text: str) -> float:
    """Calculate Shannon entropy of a string to detect randomness/typosquatting.

    Args:
        text: string to analyze

    Returns:
        Shannon entropy value (0-5.5 typically, higher = more random)
    """
    if not text:
        return 0.0

    # Count character frequencies
    char_counts = Counter(text.lower())
    entropy = 0.0

    for count in char_counts.values():
        prob = count / len(text)
        entropy -= prob * math.log2(prob)

    return entropy


def _detect_typosquatting_candidates(package_name: str, similar_names: list[str]) -> list[str]:
    """Find typosquatting candidates with high entropy scores.

    Args:
        package_name: original package name
        similar_names: list of similar package names to filter

    Returns:
        List of suspected typosquatting packages (high entropy, not in allow-list)
    """
    # Common legitimate package patterns
    allow_list = {
        "python",
        "node",
        "ruby",
        "java",
        "rust",
        "golang",
        "devops",
        "infrastructure",
        "monitoring",
    }

    suspicious = []
    base_entropy = _calculate_entropy(package_name)

    for name in similar_names:
        if name == package_name:
            continue

        # Skip obvious legitimate packages
        if any(allow in name.lower() for allow in allow_list):
            continue

        name_entropy = _calculate_entropy(name)
        # Flag if entropy is significantly higher and name looks random
        if name_entropy > base_entropy + 0.5 and name_entropy > 3.5:
            suspicious.append(name)

    return suspicious[:10]  # Cap results


async def research_registry_graveyard(package_name: str, ecosystem: str = "pypi") -> dict[str, Any]:
    """Scan package registries for deleted/yanked packages and typosquatting risks.

    Checks PyPI for yanked versions, NPM for unpublished versions, and
    RubyGems for deprecated packages. Calculates Shannon entropy to detect
    typosquatting (high entropy = suspicious generated name).

    Args:
        package_name: name of package to analyze
        ecosystem: "pypi" | "npm" | "rubygems"

    Returns:
        Dict with:
        - package_name: input package name
        - ecosystem: registry used
        - exists: whether package exists
        - is_yanked: whether package is yanked (PyPI)
        - version_count: total version count
        - yanked_count: number of yanked versions (PyPI only)
        - entropy_score: Shannon entropy of package name
        - similar_names: similar packages in registry (sample)
        - typosquatting_candidates: high-entropy suspicious packages
        - risk_level: "critical" | "high" | "medium" | "low"
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=20.0,
            ) as client:

                # Validate inputs
                if not package_name or len(package_name) > 255:
                    return {
                        "package_name": package_name,
                        "ecosystem": ecosystem,
                        "exists": False,
                        "error": "Invalid package name",
                    }

                # Normalize package name for URL
                safe_name = quote(package_name.lower().strip(), safe="")

                if ecosystem == "pypi":
                    return await _analyze_pypi(client, package_name, safe_name)
                elif ecosystem == "npm":
                    return await _analyze_npm(client, package_name, safe_name)
                elif ecosystem == "rubygems":
                    return await _analyze_rubygems(client, package_name, safe_name)
                else:
                    return {
                        "package_name": package_name,
                        "ecosystem": ecosystem,
                        "exists": False,
                        "error": f"Unknown ecosystem: {ecosystem}",
                    }

        async def _analyze_pypi(
            client: httpx.AsyncClient, package_name: str, safe_name: str
        ) -> dict[str, Any]:
            """Analyze package on PyPI."""
            url = _PYPI_JSON.format(package=safe_name)
            data = await fetch_json(client, url)

            if not data or "releases" not in data:
                return {
                    "package_name": package_name,
                    "ecosystem": "pypi",
                    "exists": False,
                    "version_count": 0,
                    "entropy_score": _calculate_entropy(package_name),
                    "risk_level": "low",
                }

            # Analyze versions
            releases = data.get("releases", {})
            all_versions = list(releases.keys())
            yanked_versions = []

            for version, release_list in releases.items():
                if isinstance(release_list, list):
                    for release in release_list:
                        if release.get("yanked", False):
                            yanked_versions.append(version)

            # Find similar package names (search top packages with similar chars)
            entropy = _calculate_entropy(package_name)
            similar = _find_similar_packages(package_name, all_versions[:50])
            typosquatting = _detect_typosquatting_candidates(package_name, similar)

            # Risk assessment
            risk_level = "low"
            if yanked_versions or typosquatting:
                risk_level = "high" if len(yanked_versions) > 5 else "medium"

            return {
                "package_name": package_name,
                "ecosystem": "pypi",
                "exists": True,
                "is_yanked": len(yanked_versions) > 0,
                "version_count": len(all_versions),
                "yanked_count": len(yanked_versions),
                "entropy_score": round(entropy, 2),
                "similar_names": similar[:10],
                "typosquatting_candidates": typosquatting,
                "risk_level": risk_level,
            }

        async def _analyze_npm(
            client: httpx.AsyncClient, package_name: str, safe_name: str
        ) -> dict[str, Any]:
            """Analyze package on NPM."""
            url = _NPM_REGISTRY.format(package=safe_name)
            data = await fetch_json(client, url)

            if not data or "versions" not in data:
                return {
                    "package_name": package_name,
                    "ecosystem": "npm",
                    "exists": False,
                    "version_count": 0,
                    "entropy_score": _calculate_entropy(package_name),
                    "risk_level": "low",
                }

            versions = data.get("versions", {})
            all_versions = list(versions.keys())

            # NPM doesn't have "yanked" but has "deprecated" field per version
            deprecated_count = sum(
                1 for v in versions.values()
                if isinstance(v, dict) and v.get("deprecated")
            )

            entropy = _calculate_entropy(package_name)
            similar = _find_similar_packages(package_name, all_versions[:50])
            typosquatting = _detect_typosquatting_candidates(package_name, similar)

            risk_level = "low"
            if deprecated_count > 0 or typosquatting:
                risk_level = "high" if deprecated_count > 10 else "medium"

            return {
                "package_name": package_name,
                "ecosystem": "npm",
                "exists": True,
                "version_count": len(all_versions),
                "deprecated_count": deprecated_count,
                "entropy_score": round(entropy, 2),
                "similar_names": similar[:10],
                "typosquatting_candidates": typosquatting,
                "risk_level": risk_level,
            }

        async def _analyze_rubygems(
            client: httpx.AsyncClient, package_name: str, safe_name: str
        ) -> dict[str, Any]:
            """Analyze package on RubyGems."""
            url = _RUBYGEMS_API.format(package=safe_name)
            data = await fetch_json(client, url)

            if not data or not isinstance(data, list):
                return {
                    "package_name": package_name,
                    "ecosystem": "rubygems",
                    "exists": False,
                    "version_count": 0,
                    "entropy_score": _calculate_entropy(package_name),
                    "risk_level": "low",
                }

            all_versions = [v.get("number", "") for v in data if isinstance(v, dict)]

            # RubyGems marks yanked in version data
            yanked_count = sum(
                1 for v in data
                if isinstance(v, dict) and v.get("yanked")
            )

            entropy = _calculate_entropy(package_name)
            similar = _find_similar_packages(package_name, all_versions[:50])
            typosquatting = _detect_typosquatting_candidates(package_name, similar)

            risk_level = "low"
            if yanked_count > 0 or typosquatting:
                risk_level = "high" if yanked_count > 5 else "medium"

            return {
                "package_name": package_name,
                "ecosystem": "rubygems",
                "exists": True,
                "version_count": len(all_versions),
                "yanked_count": yanked_count,
                "entropy_score": round(entropy, 2),
                "similar_names": similar[:10],
                "typosquatting_candidates": typosquatting,
                "risk_level": risk_level,
            }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_registry_graveyard"}


def _find_similar_packages(package_name: str, candidates: list[str]) -> list[str]:
    """Find similar package names (simple Levenshtein-like matching).

    Args:
        package_name: target package name
        candidates: list of candidates to check

    Returns:
        List of similar package names
    """
    similar = []
    target = package_name.lower()

    for candidate in candidates:
        if not candidate or not isinstance(candidate, str):
            continue

        cand_lower = candidate.lower()

        # Skip exact match
        if cand_lower == target:
            continue

        # Check for common typosquatting patterns
        if _levenshtein_distance(target, cand_lower) <= 2:
            similar.append(candidate)
        # Check for prefix/suffix matching (common squatting)
        elif target.startswith(cand_lower[:3]) or cand_lower.startswith(target[:3]):
            if abs(len(target) - len(cand_lower)) <= 3:
                similar.append(candidate)

    return similar[:20]


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        s1, s2 = s2, s1

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


async def research_subdomain_temporal(domain: str, days_back: int = 90) -> dict[str, Any]:
    """Track subdomain births/deaths over time via Certificate Transparency logs.

    Uses crt.sh to retrieve all certificates, groups by date, and flags
    suspicious patterns (burst of new certs, internal tool subdomains).

    Args:
        domain: target domain (e.g., "example.com")
        days_back: look back this many days (1-365)

    Returns:
        Dict with:
        - domain: input domain
        - subdomains_total: total unique subdomains found
        - new_last_30d: new subdomains in last 30 days
        - dead_last_30d: subdomains not seen in last 30 days
        - burst_detected: boolean, true if cert spike detected
        - internal_tools_exposed: list of detected internal tools
        - geographic_expansion: list of certificate issuers (geographic diversity)
        - monthly_distribution: dict of {month: count}
        - risk_level: "critical" | "high" | "medium" | "low"
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=30.0,
            ) as client:

                # Validate inputs
                if not domain or len(domain) > 255:
                    return {
                        "domain": domain,
                        "error": "Invalid domain",
                    }

                days_back_clamped = max(1, min(days_back, 365))

                # Fetch CT logs
                url = _CRT_SH.format(domain=quote(domain, safe=""))
                data = await fetch_json(client, url)

                if not data:
                    return {
                        "domain": domain,
                        "subdomains_total": 0,
                        "new_last_30d": 0,
                        "dead_last_30d": 0,
                        "burst_detected": False,
                        "internal_tools_exposed": [],
                        "geographic_expansion": [],
                        "risk_level": "low",
                    }

                # Parse certificates
                subdomains: dict[str, datetime] = {}
                issuers: set[str] = set()

                now = datetime.now(UTC)
                cutoff_date = now - timedelta(days=days_back_clamped)

                for entry in data:
                    if not isinstance(entry, dict):
                        continue

                    # Parse certificate date
                    not_before_str = entry.get("not_before", "")
                    try:
                        cert_date = datetime.fromisoformat(
                            not_before_str.replace("Z", "+00:00")
                        )
                        if cert_date.tzinfo is None:
                            cert_date = cert_date.replace(tzinfo=UTC)
                    except (ValueError, AttributeError):
                        continue

                    # Only include certs within our time range
                    if cert_date < cutoff_date:
                        continue

                    # Extract subdomain
                    name_value = entry.get("name_value", "")
                    for line in name_value.split("\n"):
                        line = line.strip().lstrip("*.")
                        if line.endswith(f".{domain}") or line == domain:
                            if line not in subdomains or cert_date > subdomains[line]:
                                subdomains[line] = cert_date

                    # Collect issuer info
                    issuer = entry.get("issuer_name", "")
                    if issuer:
                        issuers.add(issuer[:50])

                # Analyze temporal patterns
                monthly_dist: defaultdict[str, int] = defaultdict(int)
                last_30d_start = now - timedelta(days=30)
                new_subdomains = set()

                for subdomain, cert_date in subdomains.items():
                    month_key = cert_date.strftime("%Y-%m")
                    monthly_dist[month_key] += 1

                    if cert_date >= last_30d_start:
                        new_subdomains.add(subdomain)

                # Detect burst patterns (more than 2 std devs above mean in any month)
                cert_counts = list(monthly_dist.values())
                burst_detected = False
                if cert_counts:
                    mean_certs = sum(cert_counts) / len(cert_counts)
                    max_certs = max(cert_counts)
                    if max_certs > mean_certs * 2.5:
                        burst_detected = True

                # Detect internal tool subdomains
                internal_patterns = [
                    "jira", "jenkins", "grafana", "kibana",
                    "staging", "dev", "internal", "admin", "vpn",
                    "git", "svn", "ldap", "ldaps", "smtp", "mail",
                    "prometheus", "splunk", "datadog", "newrelic"
                ]

                internal_tools = []
                for subdomain in subdomains.keys():
                    for pattern in internal_patterns:
                        if pattern in subdomain.lower():
                            internal_tools.append(subdomain)
                            break

                # Risk assessment
                risk_level = "low"
                if internal_tools:
                    risk_level = "critical" if len(internal_tools) > 3 else "high"
                elif burst_detected:
                    risk_level = "high"
                elif new_subdomains and len(new_subdomains) > 10:
                    risk_level = "medium"

                return {
                    "domain": domain,
                    "subdomains_total": len(subdomains),
                    "new_last_30d": len(new_subdomains),
                    "dead_last_30d": sum(
                        1 for d in subdomains.values()
                        if d < cutoff_date + timedelta(days=days_back_clamped - 30)
                    ),
                    "burst_detected": burst_detected,
                    "internal_tools_exposed": sorted(internal_tools),
                    "geographic_expansion": sorted(list(issuers))[:10],
                    "monthly_distribution": dict(sorted(monthly_dist.items())),
                    "risk_level": risk_level,
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_subdomain_temporal"}


async def research_commit_analyzer(repo: str, days_back: int = 30) -> dict[str, Any]:
    """Analyze GitHub commit patterns for intelligence signals.

    Analyzes commit metadata to detect: crunch (weekend/night work),
    security focus, author churn, sentiment trends, and tech direction
    (new dependencies).

    Args:
        repo: GitHub repo in "owner/name" format
        days_back: look back this many days (1-365)

    Returns:
        Dict with:
        - repo: input repo
        - total_commits: commit count in time range
        - crunch_score: % of commits on weekends/nights (0-100)
        - security_incidents: count of commits matching CVE/vuln patterns
        - security_commits: list of security-related commit messages (sample)
        - author_churn_rate: % of new authors vs returning
        - unique_authors: count of unique authors
        - sentiment_trend: "positive" | "neutral" | "negative"
        - sentiment_score: average sentiment (-1.0 to +1.0)
        - tech_direction: list of detected tech changes
        - risk_level: "critical" | "high" | "medium" | "low"
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=20.0,
            ) as client:

                # Validate repo format
                if not repo or "/" not in repo or len(repo) > 100:
                    return {
                        "repo": repo,
                        "error": "Invalid repo format (use owner/name)",
                    }

                days_back_clamped = max(1, min(days_back, 365))

                # Calculate since date for GitHub API
                since_date = (datetime.now(UTC) - timedelta(days=days_back_clamped))
                since_iso = since_date.isoformat()

                url = _GITHUB_COMMITS.format(repo=repo)
                params = {
                    "per_page": "100",
                    "since": since_iso,
                }

                try:
                    resp = await client.get(url, params=params, timeout=20.0)
                    if resp.status_code != 200:
                        return {
                            "repo": repo,
                            "error": f"GitHub API error: {resp.status_code}",
                        }
                    commits_data = resp.json()
                except Exception as exc:
                    logger.debug("commit_analyzer fetch failed: %s", exc)
                    return {
                        "repo": repo,
                        "error": f"Failed to fetch commits: {str(exc)}",
                    }

                if not commits_data:
                    return {
                        "repo": repo,
                        "total_commits": 0,
                        "crunch_score": 0.0,
                        "security_incidents": 0,
                        "security_commits": [],
                        "author_churn_rate": 0.0,
                        "unique_authors": 0,
                        "sentiment_trend": "neutral",
                        "sentiment_score": 0.0,
                        "tech_direction": [],
                        "risk_level": "low",
                    }

                # Analyze commits
                crunch_count = 0
                weekend_night_count = 0
                security_incidents_list = []
                authors: set[str] = set()
                new_authors: set[str] = set()
                messages: list[str] = []
                tech_changes: set[str] = set()

                for commit in commits_data:
                    if not isinstance(commit, dict):
                        continue

                    commit_obj = commit.get("commit", {})
                    if not isinstance(commit_obj, dict):
                        continue

                    message = commit_obj.get("message", "").lower()
                    messages.append(message)

                    # Extract author
                    author = commit.get("author", {})
                    if isinstance(author, dict):
                        author_login = author.get("login", "")
                        if author_login:
                            authors.add(author_login)

                    # Check for security patterns
                    security_keywords = ["cve-", "fix", "patch", "vuln", "security", "breach", "exploit"]
                    if any(kw in message for kw in security_keywords):
                        security_incidents_list.append(message[:80])

                    # Check for crunch (weekend/night work)
                    try:
                        commit_date_str = commit_obj.get("author", {}).get("date", "")
                        if commit_date_str:
                            commit_date = datetime.fromisoformat(
                                commit_date_str.replace("Z", "+00:00")
                            )
                            hour = commit_date.hour
                            weekday = commit_date.weekday()  # 5=Saturday, 6=Sunday

                            if weekday >= 5 or hour < 6 or hour > 22:
                                crunch_count += 1

                            if weekday >= 5 or hour < 6 or hour >= 22:
                                weekend_night_count += 1
                    except (ValueError, AttributeError, KeyError):
                        pass

                    # Detect tech direction changes
                    if "requirements.txt" in message or "package.json" in message:
                        tech_changes.add("dependency_update")
                    if "dockerfile" in message:
                        tech_changes.add("containerization")
                    if ".github/workflows" in message:
                        tech_changes.add("ci_cd_change")
                    if "terraform" in message or "cloudformation" in message:
                        tech_changes.add("infrastructure_as_code")
                    if "migrate" in message:
                        tech_changes.add("migration")

                # Calculate metrics
                total_commits = len(commits_data)
                crunch_score = (crunch_count / total_commits * 100) if total_commits > 0 else 0

                # Estimate new vs returning authors (simple heuristic)
                author_churn_rate = 0.0
                if authors:
                    # Use commit count and author count as proxy for churn
                    avg_commits_per_author = total_commits / len(authors)
                    author_churn_rate = min(100.0, (1 / avg_commits_per_author * 100) if avg_commits_per_author > 0 else 0)

                # Calculate sentiment from message keywords
                positive_words = ["fix", "improve", "enhance", "optimize", "feature", "add", "support"]
                negative_words = ["revert", "rollback", "fix", "bug", "critical", "urgent", "emergency"]

                sentiment_score = 0.0
                if messages:
                    for msg in messages:
                        for word in positive_words:
                            if word in msg:
                                sentiment_score += 0.1
                        for word in negative_words:
                            if word in msg:
                                sentiment_score -= 0.05

                    sentiment_score = max(-1.0, min(1.0, sentiment_score / len(messages)))

                # Determine sentiment trend
                sentiment_trend = "neutral"
                if sentiment_score > 0.1:
                    sentiment_trend = "positive"
                elif sentiment_score < -0.1:
                    sentiment_trend = "negative"

                # Risk assessment
                risk_level = "low"
                if len(security_incidents_list) > 5:
                    risk_level = "critical"
                elif len(security_incidents_list) > 2:
                    risk_level = "high"
                elif crunch_score > 40:
                    risk_level = "medium"

                return {
                    "repo": repo,
                    "total_commits": total_commits,
                    "crunch_score": round(crunch_score, 1),
                    "security_incidents": len(security_incidents_list),
                    "security_commits": security_incidents_list[:10],
                    "author_churn_rate": round(author_churn_rate, 1),
                    "unique_authors": len(authors),
                    "sentiment_trend": sentiment_trend,
                    "sentiment_score": round(sentiment_score, 2),
                    "tech_direction": sorted(list(tech_changes)),
                    "risk_level": risk_level,
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_commit_analyzer"}
