"""Company intelligence and salary research tools.

Provides:
- research_company_diligence: Deep company analysis for job seekers
- research_salary_intelligence: Aggregate salary data from multiple sources
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger("loom.tools.company_intel")


def _sanitize_company_name(name: str) -> str:
    """Strip prompt injection characters from company name input."""
    sanitized = re.sub(r'["\'\{\}\[\]\\<>]', '', name)
    return sanitized[:200].strip()


async def research_company_diligence(company_name: str) -> dict[str, Any]:
    """Deep company analysis for job seekers.

    Performs multi-stage research:
    1. Company fundamentals via search (funding, size, industry)
    2. Culture and reviews via Glassdoor/Indeed searches
    3. Recent news and developments
    4. LLM-powered culture score and synthesis

    Args:
        company_name: Name of the company to research (e.g., "OpenAI", "Anthropic")

    Returns:
        Dict with keys:
        - company: company name
        - industry: industry/sector
        - size_estimate: employee count estimate (e.g., "50-200", "1000-5000")
        - funding_stage: "seed", "series-a", "series-b", etc. or None
        - culture_score: float 0-5 based on reviews and sentiment
        - pros: list of positive aspects from reviews
        - cons: list of concerns/red flags from reviews
        - recent_news: list of dicts with title and url
        - glassdoor_rating: float 0-5 or None
        - red_flags: list of concerning findings
        - recommendation: summary recommendation for job seekers
    """
    from loom.tools.search import research_search

    if not company_name or len(company_name) > 200:
        return {
            "company": company_name,
            "error": "company_name must be 1-200 characters",
        }

    company_name = _sanitize_company_name(company_name)
    logger.info("company_diligence query=%s", company_name)

    result: dict[str, Any] = {
        "company": company_name,
        "industry": None,
        "size_estimate": None,
        "funding_stage": None,
        "culture_score": 0.0,
        "pros": [],
        "cons": [],
        "recent_news": [],
        "glassdoor_rating": None,
        "red_flags": [],
        "recommendation": "",
    }

    try:
        # Stage 1: Company fundamentals
        logger.debug("stage=fundamentals company=%s", company_name)
        fundamentals = await research_search(
            query=f"{company_name} company funding size employees industry",
            provider="ddgs",
            n=5,
        )

        if fundamentals.get("results"):
            results_text = " ".join(
                [r.get("description", "") for r in fundamentals["results"][:3]]
            )
            # Extract size estimate using regex
            size_match = re.search(
                r"(\d+(?:,\d+)?)\s*(?:to|-)\s*(\d+(?:,\d+)?)\s*(?:employee|staff|person)",
                results_text,
                re.IGNORECASE,
            )
            if size_match:
                result["size_estimate"] = (
                    f"{size_match.group(1).replace(',', '')}-{size_match.group(2).replace(',', '')}"
                )
            else:
                # Try single number
                single_size = re.search(r"(\d+(?:,\d+)?)\s*(?:employee|staff)", results_text)
                if single_size:
                    result["size_estimate"] = single_size.group(1).replace(",", "")

            # Extract funding stage
            funding_match = re.search(
                r"(?:seed|series-?a|series-?b|series-?c|series-?d|ipo|public|unicorn)",
                results_text,
                re.IGNORECASE,
            )
            if funding_match:
                result["funding_stage"] = funding_match.group(0).lower()

            # Extract industry mentions
            industries = [
                "AI",
                "Software",
                "Technology",
                "Finance",
                "Healthcare",
                "Biotech",
                "Cloud",
                "Security",
                "E-commerce",
            ]
            for ind in industries:
                if ind.lower() in results_text.lower():
                    result["industry"] = ind
                    break

        # Stage 2: Culture and reviews (Glassdoor, Indeed)
        logger.debug("stage=reviews company=%s", company_name)
        reviews = await research_search(
            query=f"{company_name} glassdoor reviews culture rating",
            provider="ddgs",
            n=5,
        )

        if reviews.get("results"):
            reviews_text = " ".join(
                [r.get("description", "") for r in reviews["results"][:3]]
            )

            # Extract Glassdoor rating (e.g., "4.2 out of 5")
            rating_match = re.search(
                r"(\d+\.?\d?)\s*(?:out of|/)\s*5", reviews_text, re.IGNORECASE
            )
            if rating_match:
                result["glassdoor_rating"] = float(rating_match.group(1))

            # Simple sentiment extraction for pros/cons
            # Look for positive keywords
            positive_keywords = [
                "great culture",
                "good benefits",
                "flexible",
                "learning",
                "innovation",
                "supportive",
                "competitive",
            ]
            for keyword in positive_keywords:
                if keyword.lower() in reviews_text.lower():
                    result["pros"].append(keyword.capitalize())

            # Look for negative keywords
            negative_keywords = [
                "long hours",
                "overworked",
                "poor management",
                "low pay",
                "turnover",
                "burnout",
                "unclear",
            ]
            for keyword in negative_keywords:
                if keyword.lower() in reviews_text.lower():
                    result["cons"].append(keyword.capitalize())

        # Stage 3: Recent news
        logger.debug("stage=news company=%s", company_name)
        news = await research_search(
            query=f"{company_name} news recent 2024 2025",
            provider="ddgs",
            n=5,
        )

        if news.get("results"):
            for item in news["results"][:3]:
                news_item = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                }
                if news_item["title"] and news_item["url"]:
                    result["recent_news"].append(news_item)

                    # Check for negative news indicators
                    title_lower = news_item["title"].lower()
                    if any(word in title_lower for word in ["layoff", "closure", "lawsuit", "scandal"]):
                        result["red_flags"].append(
                            f"Recent news: {news_item['title']}"
                        )

        # Stage 4: LLM synthesis of culture score and recommendation
        logger.debug("stage=llm_synthesis company=%s", company_name)
        try:
            from loom.tools.llm import _call_with_cascade

            synthesis_prompt = f"""Based on the following company research, provide:
1. A culture_score (0-5 float)
2. A recommendation (1 sentence) for job seekers

Company: {company_name}
Pros: {', '.join(result['pros']) if result['pros'] else 'None found'}
Cons: {', '.join(result['cons']) if result['cons'] else 'None found'}
Glassdoor Rating: {result['glassdoor_rating'] if result['glassdoor_rating'] else 'Unknown'}
Red Flags: {', '.join(result['red_flags']) if result['red_flags'] else 'None'}

Respond as JSON only: {{"culture_score": float, "recommendation": string}}"""

            messages = [{"role": "user", "content": synthesis_prompt}]

            # Call async LLM
            llm_result = await _call_with_cascade(
                messages,
                model="auto",
                max_tokens=200,
                temperature=0.3,
            )

            if llm_result.success and llm_result.text:
                # Parse JSON from response
                json_match = re.search(r"\{.*\}", llm_result.text, re.DOTALL)
                if json_match:
                    synthesis = json.loads(json_match.group(0))
                    result["culture_score"] = float(synthesis.get("culture_score", 2.5))
                    result["recommendation"] = synthesis.get(
                        "recommendation",
                        "Further research recommended.",
                    )
                else:
                    # Fallback scoring based on Glassdoor rating
                    if result["glassdoor_rating"]:
                        result["culture_score"] = result["glassdoor_rating"]
                    else:
                        result["culture_score"] = 2.5
                    result["recommendation"] = (
                        f"Company has {len(result['pros'])} positive aspects and "
                        f"{len(result['cons'])} concerns identified."
                    )
        except Exception as llm_exc:
            logger.warning("llm_synthesis_failed error=%s", llm_exc)
            # Fallback scoring
            if result["glassdoor_rating"]:
                result["culture_score"] = result["glassdoor_rating"]
            else:
                result["culture_score"] = 2.5
            result["recommendation"] = (
                f"Company has {len(result['pros'])} positive aspects and "
                f"{len(result['cons'])} concerns. Further research recommended."
            )

        # Ensure culture_score is in valid range
        result["culture_score"] = max(0.0, min(5.0, result["culture_score"]))

        logger.info(
            "company_diligence_complete company=%s culture_score=%.1f",
            company_name,
            result["culture_score"],
        )

        return result

    except Exception as exc:
        logger.error("company_diligence_error company=%s error=%s", company_name, exc)
        result["error"] = str(exc)
        return result


async def research_salary_intelligence(
    role: str,
    location: str | None = None,
    experience_years: int = 0,
) -> dict[str, Any]:
    """Aggregate salary data from multiple sources.

    Performs multi-stage research:
    1. Search for salary data on Levels.fyi, Glassdoor, PayScale
    2. Search H1B visa salary database
    3. Extract salary numbers via regex ($XXX,XXX patterns)
    4. Compute ranges and median
    5. Estimate PhD premium and remote adjustments

    Args:
        role: Job title or role (e.g., "Software Engineer", "Data Scientist")
        location: Location (e.g., "San Francisco", "New York", "Remote")
        experience_years: Years of experience (0 for entry-level)

    Returns:
        Dict with keys:
        - role: job role
        - location: location or None
        - experience_years: years of experience
        - salary_data: dict with:
          - base: {"min": int, "median": int, "max": int, "currency": "USD"}
          - total_comp: {"min": int, "median": int, "max": int}
        - sources: list of dicts with name, salary_mentioned, url
        - phd_premium: string like "10-20% above base for this role"
        - remote_adjustment: string like "10-15% lower for remote"
        - data_confidence: float 0-1 based on number of data points
    """
    from loom.tools.search import research_search

    if not role or len(role) > 200:
        return {
            "role": role,
            "error": "role must be 1-200 characters",
        }

    role = role.strip()
    location_str = (location or "").strip()
    if location_str and len(location_str) > 100:
        return {
            "role": role,
            "location": location_str,
            "error": "location must be 1-100 characters",
        }

    logger.info(
        "salary_intelligence query=%s location=%s experience=%d",
        role,
        location_str or "global",
        experience_years,
    )

    result: dict[str, Any] = {
        "role": role,
        "location": location_str or None,
        "experience_years": experience_years,
        "salary_data": {
            "base": {"min": 0, "median": 0, "max": 0, "currency": "USD"},
            "total_comp": {"min": 0, "median": 0, "max": 0},
        },
        "sources": [],
        "phd_premium": "",
        "remote_adjustment": "",
        "data_confidence": 0.0,
    }

    try:
        # Build search query
        location_query = f" {location_str}" if location_str else " global"
        exp_query = f" {experience_years} years" if experience_years > 0 else " entry level"

        # Stage 1: Levels.fyi, Glassdoor, PayScale
        logger.debug("stage=salary_searches role=%s", role)
        salary_queries = [
            f"{role} salary levels.fyi{location_query}",
            f"{role} salary glassdoor{location_query}",
            f"{role} salary payscale{location_query}{exp_query}",
            f"{role} compensation h1b database",
        ]

        all_salaries: list[int] = []

        for query in salary_queries:
            try:
                search_result = await research_search(
                    query=query,
                    provider="ddgs",
                    n=5,
                )

                if search_result.get("results"):
                    for item in search_result["results"]:
                        description = item.get("description", "")
                        url = item.get("url", "")
                        title = item.get("title", "")

                        # Extract salary amounts: $XXX,XXX or $XXX,XXX,XXX
                        salary_matches = re.findall(
                            r"\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
                            description + " " + title,
                        )

                        for match in salary_matches:
                            salary_val = int(match.replace(",", "").split(".")[0])
                            # Reasonable salary range: $30k - $500k
                            if 30000 <= salary_val <= 500000:
                                all_salaries.append(salary_val)
                                # Track unique source
                                source_name = item.get("title", "Unknown")[:50]
                                result["sources"].append({
                                    "name": source_name,
                                    "salary_mentioned": f"${salary_val:,}",
                                    "url": url,
                                })

            except Exception as search_exc:
                logger.warning("salary_search_failed query=%s error=%s", query, search_exc)

        # Stage 2: Compute statistics
        logger.debug("stage=statistics total_salaries=%d", len(all_salaries))

        if all_salaries:
            all_salaries.sort()
            base_min = all_salaries[0]
            base_max = all_salaries[-1]
            base_median = all_salaries[len(all_salaries) // 2]

            result["salary_data"]["base"] = {
                "min": base_min,
                "median": base_median,
                "max": base_max,
                "currency": "USD",
            }

            # Estimate total compensation (base + bonus/stock)
            # Typically 1.2x-1.5x base for mid-level, 1.5x-2.0x for senior
            comp_multiplier = 1.3 if experience_years < 3 else (1.6 if experience_years < 7 else 1.8)

            result["salary_data"]["total_comp"] = {
                "min": int(base_min * comp_multiplier),
                "median": int(base_median * comp_multiplier),
                "max": int(base_max * comp_multiplier),
            }

            # Confidence based on data point count
            result["data_confidence"] = min(1.0, len(all_salaries) / 10.0)

        # Stage 3: PhD premium estimation
        logger.debug("stage=phd_premium role=%s", role)
        try:
            phd_search = await research_search(
                query=f"{role} salary PhD vs bachelor degree premium",
                provider="ddgs",
                n=3,
            )
            if phd_search.get("results"):
                phd_text = " ".join(
                    [r.get("description", "") for r in phd_search["results"][:2]]
                )
                # Look for percentage patterns
                premium_match = re.search(
                    r"(\d{1,2})(?:%|-|\s+to\s+)?(\d{1,2})?%", phd_text
                )
                if premium_match:
                    low = premium_match.group(1)
                    high = premium_match.group(2) or str(int(low) + 10)
                    result["phd_premium"] = f"{low}-{high}% above base for this role"
                else:
                    result["phd_premium"] = "5-15% above base for this role"
            else:
                result["phd_premium"] = "5-15% above base for this role"
        except Exception as phd_exc:
            logger.warning("phd_premium_search_failed error=%s", phd_exc)
            result["phd_premium"] = "5-15% above base for this role"

        # Stage 4: Remote adjustment
        logger.debug("stage=remote_adjustment location=%s", location_str)
        if location_str and location_str.lower() in [
            "remote",
            "work from home",
            "distributed",
        ]:
            result["remote_adjustment"] = "Remote roles typically pay 10-20% less than on-site"
        elif not location_str or location_str.lower() == "global":
            try:
                remote_search = await research_search(
                    query=f"{role} remote salary adjustment discount premium",
                    provider="ddgs",
                    n=2,
                )
                if remote_search.get("results"):
                    remote_text = " ".join(
                        [r.get("description", "") for r in remote_search["results"][:1]]
                    )
                    remote_match = re.search(r"(\d{1,2})%", remote_text)
                    if remote_match:
                        result["remote_adjustment"] = (
                            f"Remote roles typically pay {remote_match.group(1)}% "
                            f"less than on-site"
                        )
                    else:
                        result["remote_adjustment"] = "10-15% lower for remote positions"
                else:
                    result["remote_adjustment"] = "10-15% lower for remote positions"
            except Exception as remote_exc:
                logger.warning("remote_adjustment_search_failed error=%s", remote_exc)
                result["remote_adjustment"] = "10-15% lower for remote positions"
        else:
            result["remote_adjustment"] = (
                f"On-site position in {location_str}; remote roles typically "
                f"pay 10-15% less"
            )

        logger.info(
            "salary_intelligence_complete role=%s sources=%d confidence=%.2f",
            role,
            len(result["sources"]),
            result["data_confidence"],
        )

        return result

    except Exception as exc:
        logger.error("salary_intelligence_error role=%s error=%s", role, exc)
        result["error"] = str(exc)
        return result
