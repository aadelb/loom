#!/usr/bin/env python3
"""
Research Task 694: Training Data Poisoning & RLHF Reward Hacking

Investigates:
1. Training data poisoning attacks (backdoors, sleeper agents, VPI)
2. RLHF reward hacking & reward model exploitation
3. Sleeper agent activation triggers
4. Model poisoning in supply chains
5. Safety testing implications

Deployment: ssh hetzner "cd /opt/research-toolbox && python3 scripts/research_694.py"
Output: /opt/research-toolbox/tmp/research_694_poisoning.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ResearchQuery:
    """Single research query."""
    query: str
    topic: str
    description: str


@dataclass
class Source:
    """Research source."""
    title: str
    url: str
    snippet: str
    provider: str
    date: str = ""
    relevance: float = 0.0


@dataclass
class ResearchResult:
    """Research result from multi-source search."""
    query: str
    topic: str
    description: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""
    providers_queried: list[str] = field(default_factory=list)
    total_sources: int = 0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


async def run_research() -> dict[str, Any]:
    """Execute all research queries and compile results."""

    # Load environment
    load_dotenv_local()

    # Define queries
    queries = [
        ResearchQuery(
            query="training data poisoning LLM backdoor 2025 2026",
            topic="Data Poisoning Attacks",
            description="Inject malicious examples into training data; hidden backdoors activated by triggers"
        ),
        ResearchQuery(
            query="RLHF reward hacking exploitation",
            topic="RLHF Reward Hacking",
            description="Craft inputs that exploit reward model weaknesses; circumvent alignment via preference exploitation"
        ),
        ResearchQuery(
            query="sleeper agent activation trigger LLM",
            topic="Sleeper Agents",
            description="Models trained to behave normally, then activate on specific trigger phrases (Anthropic research)"
        ),
        ResearchQuery(
            query="model poisoning supply chain attack AI",
            topic="Supply Chain Poisoning",
            description="Compromise model at training or distribution stage; persistent backdoors in deployed models"
        ),
    ]

    all_results = {
        "research_date": datetime.utcnow().isoformat(),
        "task": "Training Data Poisoning & RLHF Reward Hacking Research",
        "task_id": "694",
        "queries_planned": len(queries),
        "results": [],
        "metadata": {
            "execution_time": None,
            "providers_used": [],
            "total_sources_found": 0,
            "failures": 0
        }
    }

    start_time = datetime.utcnow()
    logger.info(f"Starting research with {len(queries)} queries")

    # Execute all queries in parallel
    tasks = [execute_multi_search(query_obj) for query_obj in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Query {i} failed: {result}")
            all_results["results"].append({
                "query": queries[i].query,
                "topic": queries[i].topic,
                "description": queries[i].description,
                "error": str(result),
                "sources": [],
                "timestamp": datetime.utcnow().isoformat(),
                "providers_queried": [],
                "total_sources": 0
            })
            all_results["metadata"]["failures"] += 1
        else:
            result_dict = asdict(result)
            all_results["results"].append(result_dict)
            all_results["metadata"]["total_sources_found"] += result.total_sources
            all_results["metadata"]["providers_used"].extend(result.providers_queried)

    # Calculate execution time
    end_time = datetime.utcnow()
    all_results["metadata"]["execution_time"] = (
        end_time - start_time
    ).total_seconds()

    # Deduplicate providers
    all_results["metadata"]["providers_used"] = list(
        set(all_results["metadata"]["providers_used"])
    )

    return all_results


async def execute_multi_search(query_obj: ResearchQuery) -> ResearchResult:
    """Execute multi-source search using available search APIs."""

    logger.info(f"Researching: {query_obj.topic}")

    sources: list[dict[str, Any]] = []
    providers_queried: list[str] = []

    # Try multiple providers in sequence
    providers = [
        ("exa", exa_search),
        ("tavily", tavily_search),
        ("brave", brave_search),
        ("duckduckgo", duckduckgo_search),
        ("arxiv", arxiv_search),
    ]

    for provider_name, search_func in providers:
        try:
            logger.debug(f"  Querying {provider_name}...")
            results = await search_func(query_obj.query)

            if results:
                logger.debug(f"    -> Found {len(results)} results from {provider_name}")
                sources.extend(results)
                providers_queried.append(provider_name)
            else:
                logger.debug(f"    -> No results from {provider_name}")

        except Exception as e:
            logger.debug(f"  {provider_name} search failed: {e}")
            continue

    # Deduplicate by URL
    seen_urls = set()
    unique_sources: list[dict[str, Any]] = []
    for source in sources:
        url = source.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_sources.append(source)
        elif not url:
            unique_sources.append(source)

    # Limit to top 25
    unique_sources = unique_sources[:25]

    logger.info(
        f"  -> {len(unique_sources)} unique sources from {len(providers_queried)} providers"
    )

    return ResearchResult(
        query=query_obj.query,
        topic=query_obj.topic,
        description=query_obj.description,
        sources=unique_sources,
        timestamp=datetime.utcnow().isoformat(),
        providers_queried=providers_queried,
        total_sources=len(unique_sources),
    )


async def exa_search(query: str) -> list[dict[str, Any]]:
    """Search using Exa (semantic search)."""

    api_key = os.environ.get("EXA_API_KEY", "")
    if not api_key:
        return []

    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "query": query,
                    "numResults": 10,
                    "contents": {
                        "text": True,
                        "highlights": True
                    }
                }
            )

            if response.status_code == 200:
                data = response.json()
                results = []

                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("text", "")[:300],
                        "provider": "exa",
                        "date": item.get("publishedDate", ""),
                        "relevance": item.get("score", 0.0)
                    })

                return results
            else:
                logger.debug(f"Exa API error: {response.status_code}")
                return []

    except ImportError:
        logger.debug("httpx not available")
        return []
    except Exception as e:
        logger.debug(f"Exa search error: {e}")
        return []


async def tavily_search(query: str) -> list[dict[str, Any]]:
    """Search using Tavily."""

    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return []

    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": 10,
                    "include_answer": True
                }
            )

            if response.status_code == 200:
                data = response.json()
                results = []

                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", "")[:300],
                        "provider": "tavily",
                        "date": "",
                        "relevance": 1.0
                    })

                return results
            else:
                return []

    except Exception as e:
        logger.debug(f"Tavily search error: {e}")
        return []


async def brave_search(query: str) -> list[dict[str, Any]]:
    """Search using Brave Search."""

    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        return []

    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={
                    "q": query,
                    "count": 10
                },
                headers={
                    "X-Subscription-Token": api_key,
                    "Accept": "application/json"
                }
            )

            if response.status_code == 200:
                data = response.json()
                results = []

                for item in data.get("web", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("description", "")[:300],
                        "provider": "brave",
                        "date": "",
                        "relevance": 1.0
                    })

                return results
            else:
                return []

    except Exception as e:
        logger.debug(f"Brave search error: {e}")
        return []


async def duckduckgo_search(query: str) -> list[dict[str, Any]]:
    """Search using DuckDuckGo (via DDGS)."""

    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=10):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", "")[:300],
                    "provider": "duckduckgo",
                    "date": "",
                    "relevance": 1.0
                })

        return results

    except ImportError:
        logger.debug("duckduckgo_search not installed")
        return []
    except Exception as e:
        logger.debug(f"DuckDuckGo search error: {e}")
        return []


async def arxiv_search(query: str) -> list[dict[str, Any]]:
    """Search using arXiv for academic papers."""

    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            # arXiv API
            response = await client.get(
                "http://export.arxiv.org/api/query",
                params={
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": 10,
                    "sortBy": "relevance"
                }
            )

            if response.status_code == 200:
                import xml.etree.ElementTree as ET

                root = ET.fromstring(response.text)
                results = []
                ns = {"arxiv": "http://arxiv.org/schemas/atom"}

                for entry in root.findall("arxiv:entry", ns):
                    title_elem = entry.find("arxiv:title", ns)
                    summary_elem = entry.find("arxiv:summary", ns)
                    id_elem = entry.find("arxiv:id", ns)

                    if title_elem is not None and id_elem is not None:
                        arxiv_id = id_elem.text
                        url = f"https://arxiv.org/abs/{arxiv_id}"

                        results.append({
                            "title": title_elem.text.strip() if title_elem.text else "",
                            "url": url,
                            "snippet": (
                                summary_elem.text.strip()[:300]
                                if summary_elem is not None and summary_elem.text
                                else ""
                            ),
                            "provider": "arxiv",
                            "date": "",
                            "relevance": 1.0
                        })

                return results
            else:
                return []

    except Exception as e:
        logger.debug(f"arXiv search error: {e}")
        return []


def load_dotenv_local() -> None:
    """Load environment from ~/.claude/resources.env"""

    env_path = Path.home() / ".claude" / "resources.env"

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    os.environ[key] = value
                    if "KEY" in key or "TOKEN" in key or "PASSWORD" in key:
                        logger.debug(f"Loaded {key}")

    logger.info(f"Loaded environment from {env_path}")


async def main() -> None:
    """Main entry point."""

    try:
        # Run research
        results = await run_research()

        # Ensure output directory
        output_dir = Path("/opt/research-toolbox/tmp")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "research_694_poisoning.json"

        # Write results
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to {output_file}")

        # Print summary
        print_summary(results)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


def print_summary(results: dict[str, Any]) -> None:
    """Print research summary."""

    print("\n" + "="*80)
    print("RESEARCH SUMMARY: Training Data Poisoning & RLHF Reward Hacking")
    print("="*80)
    print(f"\nTask ID: {results.get('task_id', 'N/A')}")
    print(f"Date: {results.get('research_date', 'N/A')}")
    print(f"Execution Time: {results['metadata'].get('execution_time', 0):.1f}s")
    print(
        f"Providers: {', '.join(results['metadata'].get('providers_used', []))}"
    )

    print(f"\nTotal Sources Found: {results['metadata'].get('total_sources_found', 0)}")
    print(f"Total Results: {len(results.get('results', []))}")
    print(f"Failures: {results['metadata'].get('failures', 0)}")

    print("\n" + "-"*80)

    for result in results.get("results", []):
        topic = result.get("topic", "Unknown")
        sources = result.get("sources", [])
        error = result.get("error")

        if error:
            status = f"✗ Error: {error[:50]}"
        else:
            status = f"✓ {len(sources)} sources"

        print(f"\n{topic}")
        print(f"  Query: {result.get('query', '')}")
        print(f"  Status: {status}")

        if sources:
            for src in sources[:3]:
                title = src.get("title", "")[:60]
                provider = src.get("provider", "")
                url = src.get("url", "")
                print(f"  - [{provider}] {title}")
                if url:
                    print(f"    {url[:70]}")

    print("\n" + "="*80)
    print(f"Full results: /opt/research-toolbox/tmp/research_694_poisoning.json")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
