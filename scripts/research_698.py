#!/usr/bin/env python3
"""
Research Task 698: AI Supply Chain Attacks
- Model weights poisoning
- Registry compromises
- Dependency attacks
- Serialization exploits

Uses direct HTTP search engines without loom dependency.

Author: Ahmed Adel Bakr Alderai
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Install with: pip3 install httpx")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupplyChainResearcher:
    """Multi-engine search for AI supply chain attacks."""

    def __init__(self):
        self.results = {
            "task": "AI Supply Chain Attacks Research",
            "date": datetime.utcnow().isoformat(),
            "findings": [],
            "summary": {
                "total_queries": 0,
                "total_results": 0,
                "sources_found": set(),
            },
        }

    async def search_duckduckgo(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        """Search using DuckDuckGo (limited, no API)."""
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            resp = await client.get(url, timeout=10)
            if resp.status_code == 200:
                # Basic scraping of DDG HTML
                results = []
                # Look for result links
                for match in re.finditer(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>', resp.text):
                    url_match = match.group(1)
                    title = match.group(2)
                    if not url_match.startswith("/"):
                        results.append({
                            "title": title.strip(),
                            "url": url_match,
                            "source": "duckduckgo",
                            "snippet": "",
                        })
                return results[:10]
        except Exception as e:
            logger.debug(f"DuckDuckGo search failed: {e}")
        return []

    async def search_hackernews(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        """Search HackerNews API."""
        try:
            url = f"https://hn.algolia.com/api/v1/search?query={quote(query)}&hitsPerPage=10"
            resp = await client.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for hit in data.get("hits", [])[:10]:
                    results.append({
                        "title": hit.get("title", hit.get("story_title", "")),
                        "url": hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"),
                        "source": "hackernews",
                        "snippet": "",
                        "score": hit.get("points", 0),
                    })
                return results
        except Exception as e:
            logger.debug(f"HackerNews search failed: {e}")
        return []

    async def search_reddit(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        """Search Reddit using public API."""
        try:
            url = f"https://www.reddit.com/search.json?q={quote(query)}&limit=10&sort=relevance"
            resp = await client.get(
                url,
                timeout=10,
                headers={"User-Agent": "Loom-Research/1.0"}
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for child in data.get("data", {}).get("children", [])[:10]:
                    post = child.get("data", {})
                    results.append({
                        "title": post.get("title", ""),
                        "url": post.get("url", f"https://reddit.com{post.get('permalink', '')}"),
                        "source": "reddit",
                        "snippet": post.get("selftext", "")[:200],
                        "score": post.get("score", 0),
                    })
                return results
        except Exception as e:
            logger.debug(f"Reddit search failed: {e}")
        return []

    async def search_arxiv(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        """Search arXiv for academic papers."""
        try:
            url = f"http://export.arxiv.org/api/query?search_query=all:{quote(query)}&max_results=10"
            resp = await client.get(url, timeout=10)
            if resp.status_code == 200:
                results = []
                # Parse Atom XML
                for match in re.finditer(
                    r'<entry>.*?<title>([^<]+)</title>.*?<id>([^<]+)</id>.*?<summary>([^<]+)</summary>',
                    resp.text,
                    re.DOTALL
                ):
                    title = match.group(1).strip()
                    arxiv_id = match.group(2).split("/abs/")[-1]
                    summary = match.group(3).strip()
                    results.append({
                        "title": title,
                        "url": f"https://arxiv.org/abs/{arxiv_id}",
                        "source": "arxiv",
                        "snippet": summary[:200],
                    })
                return results[:10]
        except Exception as e:
            logger.debug(f"arXiv search failed: {e}")
        return []

    async def search_github(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        """Search GitHub repositories."""
        try:
            url = f"https://api.github.com/search/repositories?q={quote(query)}&sort=stars&per_page=10"
            resp = await client.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for repo in data.get("items", [])[:10]:
                    results.append({
                        "title": repo.get("full_name", ""),
                        "url": repo.get("html_url", ""),
                        "source": "github",
                        "snippet": repo.get("description", "")[:200],
                        "score": repo.get("stargazers_count", 0),
                    })
                return results
        except Exception as e:
            logger.debug(f"GitHub search failed: {e}")
        return []

    async def run(self, queries: list[str]):
        """Execute research across all queries."""
        self.results["summary"]["total_queries"] = len(queries)

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15,
            headers={"User-Agent": "Loom-Research/1.0"}
        ) as client:
            for i, query in enumerate(queries, 1):
                print(f"\n[{i}/{len(queries)}] Searching: {query}")
                all_results = []

                # Run all searches in parallel
                tasks = [
                    self.search_duckduckgo(client, query),
                    self.search_hackernews(client, query),
                    self.search_reddit(client, query),
                    self.search_arxiv(client, query),
                    self.search_github(client, query),
                ]

                engine_results = await asyncio.gather(*tasks, return_exceptions=True)

                for engine_result in engine_results:
                    if isinstance(engine_result, list):
                        all_results.extend(engine_result)

                # Deduplicate by URL
                seen_urls = set()
                deduped = []
                for result in all_results:
                    url = result.get("url", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        deduped.append(result)

                self.results["findings"].append({
                    "query": query,
                    "results_found": len(deduped),
                    "results": deduped[:15],  # Top 15 per query
                    "timestamp": datetime.utcnow().isoformat(),
                })

                self.results["summary"]["total_results"] += len(deduped)

                # Track sources
                for result in deduped:
                    if "source" in result:
                        self.results["summary"]["sources_found"].add(result["source"])

                print(f"    Found {len(deduped)} unique results")

    def save(self, output_file: Path):
        """Save results to JSON."""
        # Convert set to list
        self.results["summary"]["sources_found"] = list(self.results["summary"]["sources_found"])

        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\n[+] Research complete.")
        print(f"[+] Total results: {self.results['summary']['total_results']}")
        print(f"[+] Unique sources: {', '.join(self.results['summary']['sources_found'])}")
        print(f"[+] Results saved to {output_file}")


async def main():
    """Main entry point."""
    queries = [
        "AI supply chain attack model weights poisoning 2025 2026",
        "hugging face model registry security compromise",
        "PyPI malicious ML packages LLM",
        "model serialization pickle RCE attack",
        "compromised tokenizers stealth vocabulary",
        "dependency confusion attacks ML packages",
        "GGUF safetensors vs pickle security",
        "MCP server supply chain malicious tool",
        "model registry authentication bypass",
        "serialized model backdoor detection",
    ]

    print("[*] Starting AI supply chain attack research...")
    print(f"[*] {len(queries)} queries to execute")

    researcher = SupplyChainResearcher()
    await researcher.run(queries)

    # Save results
    output_dir = Path("/opt/research-toolbox/tmp")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "research_698_supply_chain.json"

    researcher.save(output_file)

    return researcher.results


if __name__ == "__main__":
    asyncio.run(main())
