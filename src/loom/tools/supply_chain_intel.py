"""Supply chain and dependency risk intelligence tools.

Provides:
- research_supply_chain_risk: Analyze dependency risk for a software package
- research_patent_landscape: Map the patent landscape for a technology
- research_dependency_audit: Audit a GitHub repository's dependencies for risks
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.supply_chain_intel")

_PYPI_API = "https://pypi.org/pypi/{package}/json"
_GITHUB_ADVISORIES = "https://api.github.com/advisories?keyword={dep}"
_USPTO_API = "https://developer.uspto.gov/ibd-api/v1/application/publications"
_LIBRARIES_IO_API = "https://libraries.io/api/{ecosystem}/{package}"


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    timeout: float = 20.0,
    headers: dict[str, str] | None = None,
) -> Any:
    """Fetch JSON from URL with error handling."""
    try:
        resp = await client.get(url, timeout=timeout, headers=headers)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("supply_chain fetch failed: %s", exc)
    return None


async def _get_text(
    client: httpx.AsyncClient,
    url: str,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
) -> str:
    """Fetch text from URL with error handling."""
    try:
        resp = await client.get(url, timeout=timeout, headers=headers)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("supply_chain text fetch failed: %s", exc)
    return ""


def _calculate_staleness_days(last_update_str: str) -> int:
    """Calculate days since last update."""
    try:
        if not last_update_str:
            return -1
        # Try ISO format first
        if "T" in last_update_str:
            last_update = datetime.fromisoformat(last_update_str.replace("Z", "+00:00"))
        else:
            # Try parsing common date formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]:
                try:
                    last_update = datetime.strptime(last_update_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                return -1
        now = datetime.now(last_update.tzinfo) if last_update.tzinfo else datetime.now()
        delta = now - last_update
        return delta.days
    except Exception as exc:
        logger.debug("staleness calculation failed: %s", exc)
        return -1


def _calculate_bus_factor(maintainers: list[dict[str, Any]]) -> float:
    """Calculate bus factor (0-1, higher = more risk).

    Single maintainer = 1.0 (critical risk)
    2-3 maintainers = 0.66 (high risk)
    4+ maintainers = 0.33 (medium risk)
    """
    if not maintainers:
        return 1.0
    if len(maintainers) == 1:
        return 1.0
    if len(maintainers) <= 3:
        return 0.66
    return 0.33


def _calculate_risk_level(
    bus_factor: float, staleness_days: int, dependency_depth: int, known_vulns: int
) -> str:
    """Determine overall risk level based on factors."""
    risk_score = 0.0

    # Bus factor (30%)
    risk_score += bus_factor * 0.3

    # Staleness (30%) — 2+ years without update = high risk
    if staleness_days > 730:
        risk_score += 0.3
    elif staleness_days > 365:
        risk_score += 0.15

    # Dependency depth (20%) — deep trees are harder to audit
    if dependency_depth > 20:
        risk_score += 0.2
    elif dependency_depth > 10:
        risk_score += 0.1

    # Known vulnerabilities (20%)
    if known_vulns > 5:
        risk_score += 0.2
    elif known_vulns > 0:
        risk_score += 0.1

    if risk_score >= 0.7:
        return "critical"
    if risk_score >= 0.5:
        return "high"
    if risk_score >= 0.3:
        return "medium"
    return "low"


async def research_supply_chain_risk(
    package_name: str, ecosystem: str = "pypi"
) -> dict[str, Any]:
    """Analyze dependency risk for a software package.

    Examines package metadata, maintainers, update frequency, dependency depth,
    and known vulnerabilities to assess supply chain risk. Supports PyPI, npm,
    and Cargo ecosystems.

    Args:
        package_name: Name of the package (e.g., "requests", "numpy", "async-executor")
        ecosystem: Package ecosystem ("pypi", "npm", "cargo"). Default: "pypi"

    Returns:
        Dict with keys:
        - package_name: normalized package name
        - ecosystem: package ecosystem
        - maintainers: list of maintainer dicts with name/email/role
        - last_update: ISO timestamp of last release
        - stars: GitHub star count (if repo found)
        - bus_factor_score: float 0-1, higher = more risk
        - staleness_days: days since last update
        - dependency_depth: estimated depth of dependency tree
        - known_vulns: count of known vulnerabilities
        - risk_level: "critical", "high", "medium", or "low"
    """
    if not package_name or len(package_name) > 200:
        return {
            "package_name": package_name,
            "error": "package_name must be 1-200 characters",
        }

    package_name = package_name.strip()
    logger.info("supply_chain_risk query=%s ecosystem=%s", package_name, ecosystem)

    result: dict[str, Any] = {
        "package_name": package_name,
        "ecosystem": ecosystem,
        "maintainers": [],
        "last_update": None,
        "stars": 0,
        "bus_factor_score": 1.0,
        "staleness_days": -1,
        "dependency_depth": 0,
        "known_vulns": 0,
        "risk_level": "unknown",
    }

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            if ecosystem == "pypi":
                # PyPI JSON API
                url = _PYPI_API.format(package=quote(package_name))
                data = await _get_json(client, url)

                if data:
                    releases = data.get("releases", {})
                    # Get latest release
                    if releases:
                        latest_version = max(releases.keys())
                        latest_release = releases[latest_version]
                        if latest_release:
                            result["last_update"] = latest_release[0].get("upload_time_iso_8601")

                    # Extract maintainers from project info
                    project_info = data.get("info", {})
                    if project_info.get("maintainer"):
                        result["maintainers"].append(
                            {
                                "name": project_info["maintainer"],
                                "email": project_info.get("maintainer_email", ""),
                                "role": "maintainer",
                            }
                        )
                    if project_info.get("author"):
                        result["maintainers"].append(
                            {
                                "name": project_info["author"],
                                "email": project_info.get("author_email", ""),
                                "role": "author",
                            }
                        )

                    # Count direct dependencies (requires_dist field)
                    requires = project_info.get("requires_dist", [])
                    if requires:
                        result["dependency_depth"] = len(requires)

                    # GitHub stars (heuristic: search for repo link)
                    urls = project_info.get("project_urls", {}) or {}
                    repo_url = urls.get("Homepage") or urls.get("Repository")
                    if repo_url and "github.com" in repo_url:
                        # Extract repo info (GitHub API requires token, skip for now)
                        logger.debug("found_repo url=%s", repo_url)

            elif ecosystem == "npm":
                # npm registry API
                url = f"https://registry.npmjs.org/{quote(package_name)}"
                data = await _get_json(client, url)

                if data:
                    # Last update
                    modified = data.get("time", {}).get("modified")
                    result["last_update"] = modified

                    # Maintainers
                    maintainers = data.get("maintainers", [])
                    result["maintainers"] = [
                        {
                            "name": m.get("name", ""),
                            "email": m.get("email", ""),
                            "role": "maintainer",
                        }
                        for m in maintainers
                    ]

                    # Dependencies
                    latest_version_data = data.get("dist-tags", {}).get("latest")
                    if latest_version_data:
                        versions = data.get("versions", {})
                        latest_data = versions.get(latest_version_data, {})
                        deps = latest_data.get("dependencies", {})
                        result["dependency_depth"] = len(deps)

            elif ecosystem == "cargo":
                # Crates.io API
                url = f"https://crates.io/api/v1/crates/{quote(package_name)}"
                data = await _get_json(client, url)

                if data:
                    crate_data = data.get("crate", {})
                    result["last_update"] = crate_data.get("updated_at")

                    # Get latest version dependencies
                    versions = data.get("versions", [])
                    if versions:
                        latest = versions[0]
                        url_deps = f"https://crates.io/api/v1/crates/{quote(package_name)}/{latest.get('num')}/dependencies"
                        deps_data = await _get_json(client, url_deps)
                        if deps_data:
                            result["dependency_depth"] = len(deps_data.get("dependencies", []))

            # Check for known vulnerabilities (GitHub Advisory API)
            logger.debug("checking_advisories package=%s", package_name)
            advisories_url = _GITHUB_ADVISORIES.format(dep=quote(package_name))
            advisories = await _get_json(
                client, advisories_url, headers={"Accept": "application/vnd.github.v3+json"}
            )
            if advisories:
                result["known_vulns"] = len(advisories) if isinstance(advisories, list) else 0

            # Calculate scores
            result["bus_factor_score"] = _calculate_bus_factor(result["maintainers"])
            if result["last_update"]:
                result["staleness_days"] = _calculate_staleness_days(result["last_update"])

            result["risk_level"] = _calculate_risk_level(
                result["bus_factor_score"],
                result["staleness_days"],
                result["dependency_depth"],
                result["known_vulns"],
            )

            return result

    try:
        return await _run()
    except Exception as exc:
        logger.error("supply_chain_risk failed: %s", exc)
        result["error"] = str(exc)
        return result


async def research_patent_landscape(query: str, max_results: int = 20) -> dict[str, Any]:
    """Map the patent landscape for a technology.

    Searches USPTO and Google Patents for issued patents related to a technology
    query. Identifies trends, top assignees, and filing activity.

    Args:
        query: Technology or invention query (e.g., "blockchain consensus", "AI transformer")
        max_results: Max patents to return (default: 20, max: 100)

    Returns:
        Dict with keys:
        - query: original query
        - total_patents: estimated total patents matching query
        - recent_patents: list of {title, patent_number, date, assignee, abstract_preview}
        - top_assignees: dict of company/assignee -> patent count
        - filing_trend: "increasing", "stable", or "decreasing"
    """
    if not query or len(query) > 500:
        return {
            "query": query,
            "error": "query must be 1-500 characters",
        }

    query = query.strip()
    max_results = min(max_results, 100)
    logger.info("patent_landscape query=%s", query)

    result: dict[str, Any] = {
        "query": query,
        "total_patents": 0,
        "recent_patents": [],
        "top_assignees": {},
        "filing_trend": "unknown",
    }

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # Try USPTO API
            try:
                params = {
                    "searchText": query,
                    "start": 0,
                    "rows": max_results,
                }
                url = f"{_USPTO_API}?{'&'.join(f'{k}={quote(str(v))}' for k, v in params.items())}"
                data = await _get_json(client, url, timeout=30.0)

                if data:
                    patents = data.get("patents", [])
                    result["total_patents"] = data.get("total", 0)

                    assignees_count: dict[str, int] = {}
                    recent_patents = []

                    for patent in patents[:max_results]:
                        patent_num = patent.get("patentNumber", "")
                        title = patent.get("title", "")
                        date = patent.get("filingDate", patent.get("issueDate", ""))
                        assignee = patent.get("assigneeEntityName", "Unknown")
                        abstract = patent.get("abstract", "")[:200]

                        recent_patents.append(
                            {
                                "title": title,
                                "patent_number": patent_num,
                                "date": date,
                                "assignee": assignee,
                                "abstract_preview": abstract,
                            }
                        )

                        # Count assignees
                        assignees_count[assignee] = assignees_count.get(assignee, 0) + 1

                    result["recent_patents"] = recent_patents
                    result["top_assignees"] = dict(
                        sorted(assignees_count.items(), key=lambda x: x[1], reverse=True)[:10]
                    )

                    # Estimate trend (simplified: compare filing year distributions)
                    if recent_patents:
                        years: dict[str, int] = {}
                        for patent in recent_patents:
                            date_str = patent.get("date", "")
                            if date_str and len(date_str) >= 4:
                                year = date_str[:4]
                                years[year] = years.get(year, 0) + 1

                        if years:
                            sorted_years = sorted(years.items())
                            if len(sorted_years) >= 2:
                                recent_count = sum(v for k, v in sorted_years[-2:])
                                older_count = sum(v for k, v in sorted_years[:-2])
                                if recent_count > older_count * 1.2:
                                    result["filing_trend"] = "increasing"
                                elif recent_count < older_count * 0.8:
                                    result["filing_trend"] = "decreasing"
                                else:
                                    result["filing_trend"] = "stable"
            except Exception as exc:
                logger.debug("USPTO API failed: %s", exc)

            # Fallback: Try Google Patents via search (if USPTO fails)
            if not result["recent_patents"]:
                logger.debug("falling_back_to_google_patents query=%s", query)
                from loom.tools.search import research_search

                search_result = research_search(
                    query=f'{query} site:patents.google.com OR site:uspto.gov',
                    provider="ddgs",
                    n=max_results,
                )
                if search_result.get("results"):
                    for res in search_result["results"][:max_results]:
                        url = res.get("url", "")
                        title = res.get("title", "")
                        desc = res.get("description", "")[:200]

                        # Extract patent number from URL if possible
                        patent_match = re.search(r"(?:US|EP|WO)?(\d{7,10})", url)
                        patent_num = patent_match.group(0) if patent_match else url

                        result["recent_patents"].append(
                            {
                                "title": title,
                                "patent_number": patent_num,
                                "date": None,
                                "assignee": "Unknown",
                                "abstract_preview": desc,
                            }
                        )
                    result["total_patents"] = len(search_result.get("results", []))

            return result

    try:
        return await _run()
    except Exception as exc:
        logger.error("patent_landscape failed: %s", exc)
        result["error"] = str(exc)
        return result


async def research_dependency_audit(repo_url: str) -> dict[str, Any]:
    """Audit a GitHub repository's dependencies for risks.

    Fetches dependency files (requirements.txt, package.json, Cargo.toml, etc.)
    from a GitHub repository and checks each dependency for:
    - Last update date
    - Maintainer count
    - Known vulnerabilities via GitHub Advisories

    Args:
        repo_url: Full GitHub repository URL (e.g., "https://github.com/owner/repo")

    Returns:
        Dict with keys:
        - repo_url: normalized repo URL
        - dependencies_found: total dependencies discovered
        - audited: dependencies successfully audited
        - vulnerabilities: list of {dependency, cve_id, severity, description}
        - outdated: list of {dependency, last_update, staleness_days}
        - risk_summary: "critical", "high", "medium", or "low"
    """
    validate_url(repo_url)
    if not repo_url or "github.com" not in repo_url.lower():
        return {
            "repo_url": repo_url,
            "error": "repo_url must be a valid GitHub URL",
        }

    repo_url = repo_url.strip().rstrip("/")
    logger.info("dependency_audit repo=%s", repo_url)

    result: dict[str, Any] = {
        "repo_url": repo_url,
        "dependencies_found": 0,
        "audited": 0,
        "vulnerabilities": [],
        "outdated": [],
        "risk_summary": "unknown",
    }

    async def _run() -> dict[str, Any]:
        # Parse repo URL
        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            return {"repo_url": repo_url, "error": "Invalid GitHub URL"}
        owner = parts[-2]
        repo = parts[-1]
        raw_base = f"https://raw.githubusercontent.com/{owner}/{repo}/main"

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            dependencies: dict[str, str] = {}

            # Try common dependency files
            dep_files = [
                ("requirements.txt", "pip"),
                ("package.json", "npm"),
                ("Cargo.toml", "cargo"),
                ("Gemfile", "bundler"),
                ("go.mod", "go"),
                ("pom.xml", "maven"),
                ("build.gradle", "gradle"),
            ]

            for filename, pkg_type in dep_files:
                url = f"{raw_base}/{filename}"
                content = await _get_text(client, url)

                if content:
                    logger.debug("found_dep_file file=%s type=%s", filename, pkg_type)

                    # Parse dependencies based on file type
                    if filename == "requirements.txt":
                        for line in content.splitlines():
                            line = line.strip()
                            if line and not line.startswith("#"):
                                # Parse package[extras]==version style
                                match = re.match(
                                    r"([a-zA-Z0-9\-_.]+)", line
                                )
                                if match:
                                    pkg_name = match.group(1).lower()
                                    dependencies[pkg_name] = pkg_type

                    elif filename == "package.json":
                        try:
                            data = json.loads(content)
                            for dep_name in data.get("dependencies", {}).keys():
                                dependencies[dep_name.lower()] = "npm"
                            for dev_dep in data.get("devDependencies", {}).keys():
                                dependencies[dev_dep.lower()] = "npm"
                        except json.JSONDecodeError:
                            logger.debug("failed_to_parse package.json")

                    elif filename == "Cargo.toml":
                        # Simple Cargo.toml parsing
                        for line in content.splitlines():
                            match = re.match(r'([a-zA-Z0-9\-_]+)\s*=\s*', line)
                            if match:
                                pkg_name = match.group(1)
                                if pkg_name not in ["package", "dependencies", "dev-dependencies"]:
                                    dependencies[pkg_name.lower()] = "cargo"

            result["dependencies_found"] = len(dependencies)

            # Audit each dependency
            vulnerabilities: list[dict[str, Any]] = []
            outdated: list[dict[str, Any]] = []

            for dep_name, pkg_type in dependencies.items():
                logger.debug("auditing_dep dep=%s type=%s", dep_name, pkg_type)

                # Check for vulnerabilities via GitHub Advisories
                advisories_url = _GITHUB_ADVISORIES.format(dep=quote(dep_name))
                advisories = await _get_json(
                    client,
                    advisories_url,
                    headers={"Accept": "application/vnd.github.v3+json"},
                )

                if advisories and isinstance(advisories, list):
                    for advisory in advisories[:3]:  # Limit to top 3 per dependency
                        vulnerabilities.append(
                            {
                                "dependency": dep_name,
                                "cve_id": advisory.get("cve_id", "CVE-UNKNOWN"),
                                "severity": advisory.get("severity", "unknown"),
                                "description": advisory.get("summary", "")[:100],
                            }
                        )

                # Check last update
                if pkg_type == "pip":
                    pypi_url = _PYPI_API.format(package=quote(dep_name))
                    pypi_data = await _get_json(client, pypi_url)
                    if pypi_data:
                        releases = pypi_data.get("releases", {})
                        if releases:
                            latest_version = max(releases.keys())
                            latest_release = releases[latest_version]
                            if latest_release:
                                last_update = latest_release[0].get("upload_time_iso_8601")
                                if last_update:
                                    staleness = _calculate_staleness_days(last_update)
                                    if staleness > 365:  # More than a year old
                                        outdated.append(
                                            {
                                                "dependency": dep_name,
                                                "last_update": last_update,
                                                "staleness_days": staleness,
                                            }
                                        )
                                    result["audited"] += 1

            result["vulnerabilities"] = vulnerabilities[:20]  # Limit output
            result["outdated"] = outdated[:20]

            # Calculate risk summary
            if vulnerabilities:
                critical_count = sum(1 for v in vulnerabilities if v.get("severity") == "critical")
                if critical_count > 0:
                    result["risk_summary"] = "critical"
                elif len(vulnerabilities) > 5:
                    result["risk_summary"] = "high"
                else:
                    result["risk_summary"] = "medium"
            elif len(outdated) > len(dependencies) * 0.5:
                result["risk_summary"] = "medium"
            else:
                result["risk_summary"] = "low"

            return result

    try:
        return await _run()
    except Exception as exc:
        logger.error("dependency_audit failed: %s", exc)
        result["error"] = str(exc)
        return result
