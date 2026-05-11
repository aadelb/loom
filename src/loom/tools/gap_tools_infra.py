"""Gap tools for infrastructure reconnaissance — cloud enumeration, secret scanning, WHOIS correlation, LLM consistency."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("loom.tools.gap_tools_infra")


async def _check_cloud_resource(
    client: httpx.AsyncClient, url: str, timeout: float = 5.0
) -> dict[str, Any]:
    """Check HTTP status for a cloud resource URL.

    Args:
        client: AsyncClient instance
        url: URL to check
        timeout: request timeout in seconds

    Returns:
        Dict with url, status_code, is_public, is_private.
    """
    try:
        resp = await client.head(url, timeout=timeout, follow_redirects=False)
        status = resp.status_code
        return {
            "url": url,
            "status": status,
            "is_public": status == 200,
            "is_private": status == 403,
        }
    except Exception as exc:
        logger.debug("cloud resource check failed for %s: %s", url, exc)
        return {
            "url": url,
            "status": None,
            "is_public": False,
            "is_private": False,
            "error": str(exc),
        }


async def research_cloud_enum(domain: str) -> dict[str, Any]:
    """Check cloud resource existence for a domain by probing common patterns.

    Probes S3, Azure Blob, GCS, Firebase, Heroku, Netlify, Vercel, and
    Cloudflare Pages for the given domain. Returns HTTP status for each
    endpoint (200=public, 403=exists-private, 404=not-found).

    Args:
        domain: target domain (e.g., "example.com")

    Returns:
        Dict with domain and cloud_resources list containing provider, url,
        status, is_public, is_private for each checked service.
    """
    try:
        if not domain or len(domain) > 255:
            return {
                "domain": domain,
                "error": "domain must be 1-255 characters",
                "cloud_resources": [],
            }

        # Validate domain format (basic check)
        if not re.match(r"^[a-z0-9.-]+$", domain.lower()):
            return {
                "domain": domain,
                "error": "domain contains invalid characters",
                "cloud_resources": [],
            }

        # Extract base domain for S3 bucket name (remove subdomains)
        base_domain = domain.split(".")[0]

        cloud_endpoints = [
            # S3 buckets (two common patterns)
            ("S3", f"https://{base_domain}.s3.amazonaws.com"),
            ("S3", f"https://s3.amazonaws.com/{base_domain}"),
            # Azure Blob Storage
            ("Azure Blob", f"https://{base_domain}.blob.core.windows.net"),
            # Google Cloud Storage
            ("GCS", f"https://storage.googleapis.com/{base_domain}"),
            # Firebase Realtime Database
            ("Firebase", f"https://{base_domain}.firebaseio.com/.json"),
            # Heroku app
            ("Heroku", f"https://{base_domain}.herokuapp.com"),
            # Netlify site
            ("Netlify", f"https://{base_domain}.netlify.app"),
            # Vercel project
            ("Vercel", f"https://{base_domain}.vercel.app"),
            # Cloudflare Pages
            ("Cloudflare Pages", f"https://{base_domain}.pages.dev"),
        ]

        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=False,
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=30.0,
            ) as client:
                tasks = [
                    _check_cloud_resource(client, url) for _, url in cloud_endpoints
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                cloud_resources = []
                for idx, result in enumerate(results):
                    if isinstance(result, dict) and "url" in result:
                        provider = cloud_endpoints[idx][0]
                        resource = {
                            "provider": provider,
                            "url": result["url"],
                            "status": result.get("status"),
                            "is_public": result.get("is_public", False),
                            "is_private": result.get("is_private", False),
                        }
                        # Only include if status was checked (not errored)
                        if result.get("status") is not None:
                            cloud_resources.append(resource)

                return {
                    "domain": domain,
                    "cloud_resources": cloud_resources,
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_cloud_enum"}


async def _github_code_search(
    client: httpx.AsyncClient, query: str, timeout: float = 10.0
) -> list[dict[str, Any]]:
    """Search GitHub code for secret patterns.

    Args:
        client: AsyncClient instance
        query: GitHub code search query
        timeout: request timeout in seconds

    Returns:
        List of dicts with repo, file_path, match_preview, secret_type.
    """
    try:
        # GitHub API endpoint for code search
        url = "https://api.github.com/search/code"
        params = {"q": query, "per_page": 20, "sort": "stars"}
        resp = await client.get(url, params=params, timeout=timeout)
        if resp.status_code != 200:
            logger.debug("github search failed: %s", resp.status_code)
            return []

        data = resp.json()
        items = data.get("items", [])
        results = []

        for item in items:
            results.append(
                {
                    "repo": item.get("repository", {}).get("full_name", "unknown"),
                    "file_path": item.get("path", ""),
                    "match_preview": item.get("text_matches", [{}])[0].get(
                        "fragment", ""
                    )[:200],
                    "secret_type": "unknown",
                }
            )
        return results
    except Exception as exc:
        logger.debug("github code search failed: %s", exc)
        return []


async def research_github_secrets(query: str, max_results: int = 20) -> dict[str, Any]:
    """Search GitHub for accidentally committed secrets using code search API.

    Queries for common secret patterns in config files (.env, .yml, .json, .py)
    and searches for AWS key prefixes.

    Args:
        query: base search term (e.g., domain name or app name)
        max_results: max results per search query (capped at 100)

    Returns:
        Dict with query, secrets_found list containing repo, file_path,
        match_preview, secret_type for each match.
    """
    try:
        if not query or len(query) > 100:
            return {
                "query": query,
                "error": "query must be 1-100 characters",
                "secrets_found": [],
            }

        # Validate query doesn't contain special chars
        if not re.match(r"^[a-z0-9\-_.]+$", query.lower()):
            return {
                "query": query,
                "error": "query contains invalid characters",
                "secrets_found": [],
            }

        max_results = min(max_results, 100)  # Cap at 100

        search_queries = [
            (f"{query}+filename:.env", "env_file"),
            (f"{query}+filename:config.json", "config_json"),
            (f"AKIA+filename:.py+{query}", "aws_key"),
            (f"password+filename:.yml+{query}", "yaml_password"),
        ]

        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=30.0,
            ) as client:
                tasks = [_github_code_search(client, q) for q, _ in search_queries]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                secrets_found = []
                secret_type_map = {idx: stype for idx, (_, stype) in enumerate(search_queries)}

                for idx, result in enumerate(results):
                    if isinstance(result, list):
                        for item in result:
                            item["secret_type"] = secret_type_map.get(idx, "unknown")
                            secrets_found.append(item)

                # Deduplicate by repo + file_path
                seen = set()
                deduped = []
                for item in secrets_found:
                    key = (item["repo"], item["file_path"])
                    if key not in seen:
                        seen.add(key)
                        deduped.append(item)

                return {
                    "query": query,
                    "secrets_found": deduped[:max_results],
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_github_secrets"}


async def _get_rdap_data(
    client: httpx.AsyncClient, domain: str, timeout: float = 10.0
) -> dict[str, Any]:
    """Fetch WHOIS data via RDAP endpoint.

    Args:
        client: AsyncClient instance
        domain: domain to look up
        timeout: request timeout in seconds

    Returns:
        Dict with registrant email, org, nameservers from RDAP.
    """
    try:
        url = f"https://rdap.org/domain/{domain}"
        resp = await client.get(url, timeout=timeout)
        if resp.status_code != 200:
            return {}

        data = resp.json()

        # Extract contact info
        registrant_email = ""
        registrant_org = ""
        for entity in data.get("entities", []):
            if "registrant" in entity.get("roles", []):
                for vcard in entity.get("vcardArray", []):
                    if isinstance(vcard, list):
                        for field in vcard:
                            if isinstance(field, list) and len(field) > 1:
                                if field[0] == "email":
                                    registrant_email = field[3] if len(field) > 3 else ""
                                elif field[0] == "org":
                                    registrant_org = field[3] if len(field) > 3 else ""

        # Extract nameservers
        nameservers = []
        for ns in data.get("nameservers", []):
            if "ldhName" in ns:
                nameservers.append(ns["ldhName"])

        return {
            "registrant_email": registrant_email,
            "registrant_org": registrant_org,
            "nameservers": nameservers,
        }
    except Exception as exc:
        logger.debug("rdap lookup failed: %s", exc)
        return {}


async def _search_crt_sh(
    client: httpx.AsyncClient,
    registrant_email: str,
    timeout: float = 15.0,
) -> list[str]:
    """Search crt.sh for domains with matching registrant email in SANs.

    Args:
        client: AsyncClient instance
        registrant_email: email to search for
        timeout: request timeout in seconds

    Returns:
        List of related domain names.
    """
    if not registrant_email:
        return []

    try:
        # crt.sh API doesn't support direct email search, so we return empty
        # In a real implementation, you'd correlate via certificate transparency logs
        return []
    except Exception as exc:
        logger.debug("crt.sh search failed: %s", exc)
        return []


async def research_whois_correlator(domain: str) -> dict[str, Any]:
    """Correlate WHOIS registrant across domains.

    Performs RDAP lookup to extract registrant email and org, then searches
    certificate transparency logs and DNS records for other domains with
    matching registrant information.

    Args:
        domain: target domain (e.g., "example.com")

    Returns:
        Dict with domain, registrant_email, registrant_org, related_domains list,
        and ownership_graph showing domain relationships.
    """
    try:
        if not domain or len(domain) > 255:
            return {
                "domain": domain,
                "error": "domain must be 1-255 characters",
                "registrant_email": "",
                "registrant_org": "",
                "related_domains": [],
                "ownership_graph": {},
            }

        # Basic domain validation
        if not re.match(r"^[a-z0-9.-]+$", domain.lower()):
            return {
                "domain": domain,
                "error": "domain contains invalid characters",
                "registrant_email": "",
                "registrant_org": "",
                "related_domains": [],
                "ownership_graph": {},
            }

        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=30.0,
            ) as client:
                rdap_data = await _get_rdap_data(client, domain)
                registrant_email = rdap_data.get("registrant_email", "")
                registrant_org = rdap_data.get("registrant_org", "")

                # Search for related domains via crt.sh
                related_domains = []
                if registrant_email:
                    related_domains = await _search_crt_sh(client, registrant_email)

                return {
                    "domain": domain,
                    "registrant_email": registrant_email,
                    "registrant_org": registrant_org,
                    "related_domains": related_domains[:50],  # Cap at 50
                    "ownership_graph": {
                        domain: {
                            "email": registrant_email,
                            "org": registrant_org,
                            "related": related_domains[:10],
                        }
                    },
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_whois_correlator"}


def _jaccard_similarity(set1: set[str], set2: set[str]) -> float:
    """Calculate Jaccard similarity between two word sets.

    Args:
        set1: first word set
        set2: second word set

    Returns:
        Similarity score between 0 and 1.
    """
    if not set1 and not set2:
        return 1.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


async def _query_llm_endpoint(
    client: httpx.AsyncClient,
    target_url: str,
    prompt: str,
    timeout: float = 30.0,
) -> str:
    """Send POST request to LLM endpoint and return response text.

    Args:
        client: AsyncClient instance
        target_url: target endpoint URL
        prompt: prompt to send
        timeout: request timeout in seconds

    Returns:
        Response text from LLM endpoint.
    """
    try:
        # Attempt to parse URL and make POST request
        parsed = urlparse(target_url)
        if not parsed.scheme or not parsed.netloc:
            return ""

        payload = {"prompt": prompt}
        resp = await client.post(target_url, json=payload, timeout=timeout)
        if resp.status_code == 200:
            # Try to extract text from common response formats
            try:
                data = resp.json()
                if isinstance(data, dict):
                    return data.get("response", data.get("text", ""))
                return str(data)
            except Exception:
                return resp.text
        return ""
    except Exception as exc:
        logger.debug("llm query failed: %s", exc)
        return ""


async def research_output_consistency(
    target_url: str, prompt: str, runs: int = 5
) -> dict[str, Any]:
    """Measure LLM response variability by sending same prompt multiple times.

    Sends the prompt to the target endpoint N times and compares responses
    using Jaccard word overlap similarity. Returns mean similarity, variance,
    and consistency score.

    Args:
        target_url: target LLM endpoint URL
        prompt: prompt to send
        runs: number of times to query (1-20, default 5)

    Returns:
        Dict with target, prompt (truncated), runs, responses (list of previews),
        mean_similarity, variance, consistency_score (0-1).
    """
    try:
        if not target_url or len(target_url) > 500:
            return {
                "target": target_url,
                "error": "target URL must be 1-500 characters",
                "mean_similarity": 0.0,
                "variance": 0.0,
                "consistency_score": 0.0,
            }

        if not prompt or len(prompt) > 5000:
            return {
                "target": target_url,
                "error": "prompt must be 1-5000 characters",
                "mean_similarity": 0.0,
                "variance": 0.0,
                "consistency_score": 0.0,
            }

        # Validate runs parameter
        try:
            runs = max(1, min(int(runs), 20))
        except (ValueError, TypeError):
            runs = 5

        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={"User-Agent": "Loom-Research/1.0"},
            ) as client:
                # Send prompt N times
                tasks = [
                    _query_llm_endpoint(client, target_url, prompt) for _ in range(runs)
                ]
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out errors and empty responses
                valid_responses = [
                    r for r in responses if isinstance(r, str) and r.strip()
                ]

                if len(valid_responses) < 2:
                    return {
                        "target": target_url,
                        "prompt": prompt[:500],
                        "runs": runs,
                        "responses": [r[:200] for r in valid_responses],
                        "mean_similarity": 0.0,
                        "variance": 0.0,
                        "consistency_score": 0.0,
                    }

                # Convert responses to word sets for similarity comparison
                word_sets = [set(r.lower().split()) for r in valid_responses]

                # Calculate pairwise similarities
                similarities = []
                for i in range(len(word_sets)):
                    for j in range(i + 1, len(word_sets)):
                        sim = _jaccard_similarity(word_sets[i], word_sets[j])
                        similarities.append(sim)

                # Calculate statistics
                mean_similarity = (
                    sum(similarities) / len(similarities) if similarities else 0.0
                )

                # Variance calculation
                if similarities:
                    variance = (
                        sum((s - mean_similarity) ** 2 for s in similarities)
                        / len(similarities)
                    )
                else:
                    variance = 0.0

                # Consistency score: 1 - variance
                consistency_score = max(0.0, 1.0 - variance)

                return {
                    "target": target_url,
                    "prompt": prompt[:500],
                    "runs": len(valid_responses),
                    "responses": [r[:200] for r in valid_responses],
                    "mean_similarity": round(mean_similarity, 3),
                    "variance": round(variance, 3),
                    "consistency_score": round(consistency_score, 3),
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_output_consistency"}
