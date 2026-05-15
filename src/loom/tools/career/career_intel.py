"""PhD career intelligence tools for research-to-market mapping and CV translation."""

from __future__ import annotations

import json
import logging
import re
from loom.error_responses import handle_tool_errors
from typing import Any
try:
    from loom.text_utils import truncate
except ImportError:
    def truncate(text: str, max_chars: int = 500, *, suffix: str = "...") -> str:
        """Fallback truncate if text_utils unavailable."""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - len(suffix)] + suffix

logger = logging.getLogger("loom.tools.career_intel")


# ============================================================================
# TOOL 1: research_map_research_to_product
# ============================================================================


def _extract_research_areas_simple(research_description: str) -> list[str]:
    """Extract research areas using keyword-based fallback analysis.

    When LLM is unavailable, uses regex patterns to identify common
    research methodologies and techniques.

    Args:
        research_description: research abstract or description

    Returns:
        List of identified research areas/techniques
    """
    areas = []
    research_desc_lower = research_description.lower()

    # Define keyword patterns for common research areas
    patterns = {
        "reinforcement learning": [
            r"\breinforcement\s+learning\b",
            r"\bRL\b",
            r"\bpolicy\s+gradient",
            r"\bQ[\s-]?learning\b",
        ],
        "NLP": [r"\bNLP\b", r"\bnatural\s+language", r"\blanguage\s+model"],
        "computer vision": [
            r"\bcomputer\s+vision\b",
            r"\bimage\s+classification",
            r"\bobject\s+detection",
        ],
        "deep learning": [r"\bdeep\s+learning\b", r"\bneural\s+network"],
        "machine learning": [r"\bmachine\s+learning\b", r"\bML\b"],
        "transformer models": [r"\btransformer", r"\bBERT\b", r"\bGPT\b"],
        "graph neural networks": [r"\bgraph\s+neural", r"\bGNN\b"],
        "Bayesian methods": [r"\bBayesian", r"\bprobabilistic\s+model"],
        "time series": [r"\btime\s+series", r"\btemporal"],
        "causal inference": [r"\bcausal", r"\bintervention", r"\btreatment\s+effect"],
        "optimization": [r"\boptimization\b", r"\bconvex"],
        "robotics": [r"\brobotics\b", r"\brobot"],
        "drug discovery": [r"\bdrug\s+discovery", r"\bmolecular"],
        "climate science": [r"\bclimate", r"\bweather\s+prediction"],
        "quantum computing": [r"\bquantum"],
    }

    for area, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, research_desc_lower):
                if area not in areas:
                    areas.append(area)
                break

    return areas if areas else ["machine learning", "data science"]


async def _extract_research_areas_llm(research_description: str) -> list[str]:
    """Extract research areas using LLM-powered analysis.

    Attempts to use the LLM tools module for semantic extraction.
    Falls back to keyword-based analysis if LLM is unavailable.

    Args:
        research_description: research abstract or description

    Returns:
        List of identified research areas/techniques
    """
    try:
        from loom.tools.llm.llm import research_llm_chat

        response = await research_llm_chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract key research methodologies, techniques, and domains "
                        "from the provided research description. Return a JSON object "
                        "with a single key 'areas' containing a list of strings."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Research description:\n{research_description[:2000]}"
                }
            ],
            max_tokens=500,
        )

        # Parse LLM response
        try:
            data = json.loads(response.get("content", ""))
            areas = data.get("areas", [])
            if isinstance(areas, list) and areas:
                return [str(a).strip() for a in areas if a]
        except (json.JSONDecodeError, TypeError):
            pass

    except ImportError:
        logger.debug("llm_chat not available, falling back to keyword analysis")
    except Exception as exc:
        logger.warning("llm extraction failed: %s, falling back to keywords", exc)

    # Fallback to keyword analysis
    return _extract_research_areas_simple(research_description)


async def _search_companies_for_areas(areas: list[str], n: int = 10) -> dict[str, Any]:
    """Search for companies using the identified research techniques.

    Uses research_search to find companies and products implementing
    these techniques.

    Args:
        areas: list of research areas/techniques
        n: number of results per area

    Returns:
        Dict mapping areas to lists of company/product findings
    """
    from loom.tools.core.search import research_search

    result = {}

    for area in areas[:5]:  # Limit to top 5 areas to avoid excessive searches
        try:
            search_query = f'"{area}" companies products hiring'
            search_result = await research_search(
                query=search_query,
                provider="ddgs",  # Use DuckDuckGo for cost-effectiveness
                n=n,
            )

            companies = set()
            products = set()

            for item in search_result.get("results", []):
                title = item.get("title", "").lower()
                snippet = item.get("snippet", "").lower()
                combined = f"{title} {snippet}"

                # Extract company mentions
                company_patterns = [
                    r"\b(OpenAI|DeepMind|Google|Meta|NVIDIA|Tesla|Microsoft|Amazon|Apple)\b",
                    r"\b(Anthropic|Cohere|Together|HuggingFace|MosaicML|Databricks)\b",
                    r"\b(\w+\sAI|AI\s+\w+)\b",
                ]

                for pattern in company_patterns:
                    matches = re.findall(pattern, combined, re.IGNORECASE)
                    companies.update(matches)

                # Extract product mentions
                product_patterns = [
                    r"\b(ChatGPT|AlphaFold|AlphaGo|Claude|Copilot|DALL-E|Gemini)\b",
                    r"\b(LLaMA|Mistral|Qwen|Yi|Deepseek)\b",
                ]

                for pattern in product_patterns:
                    matches = re.findall(pattern, combined, re.IGNORECASE)
                    products.update(matches)

            result[area] = {
                "companies": sorted(list(companies)),
                "products": sorted(list(products)),
                "total_results": len(search_result.get("results", [])),
            }

        except Exception as exc:
            logger.warning("search_companies failed for area=%s: %s", area, exc)
            result[area] = {"companies": [], "products": [], "error": str(exc)}

    return result


async def _search_github_repos(areas: list[str], n: int = 10) -> dict[str, list[dict[str, Any]]]:
    """Search GitHub for repositories implementing research techniques.

    Args:
        areas: list of research areas/techniques
        n: number of results per area

    Returns:
        Dict mapping areas to lists of GitHub repository findings
    """
    from loom.tools.core.github import research_github

    result = {}

    for area in areas[:3]:  # Limit to top 3 areas
        try:
            github_result = await research_github(
                kind="repo",
                query=area,
                sort="stars",
                order="desc",
                limit=n,
            )

            repos = []
            for item in github_result.get("results", []):
                repos.append(
                    {
                        "name": item.get("name"),
                        "url": item.get("url"),
                        "stars": item.get("stars", 0),
                        "language": item.get("language"),
                    }
                )

            result[area] = repos

        except Exception as exc:
            logger.warning("github search failed for area=%s: %s", area, exc)
            result[area] = []

    return result


@handle_tool_errors("research_map_research_to_product")
async def research_map_research_to_product(
    research_description: str,
    n: int = 10,
) -> dict[str, Any]:
    """Map PhD research expertise to commercial products and companies.

    This tool identifies the key research methodologies in an academic
    research description, then searches for companies and products that
    use those techniques, and finds relevant open-source implementations
    on GitHub.

    Args:
        research_description: research abstract or description (any length)
        n: max number of results per area (default 10)

    Returns:
        Dict with:
        - research_areas: extracted techniques/domains
        - commercial_mappings: list of dicts mapping areas → companies/products
        - github_repos: mapping of areas → top GitHub implementations
        - total_companies: unique company count
        - total_opportunities: total finding count
    """
    # Validate input
    n = max(1, min(n, 50))

    logger.info(
        "map_research_to_product research_len=%d n=%d",
        len(research_description),
        n,
    )

    try:
        # Step 1: Extract research areas
        areas = await _extract_research_areas_llm(research_description)
        logger.info("extracted_areas count=%d areas=%s", len(areas), areas[:5])

        # Step 2: Search for companies using these techniques
        company_mappings = await _search_companies_for_areas(areas, n=n)

        # Step 3: Search GitHub for implementations
        github_repos = await _search_github_repos(areas, n=n)

        # Step 4: Build commercial mappings
        commercial_mappings = []
        all_companies = set()
        total_opportunities = 0

        for area, company_data in company_mappings.items():
            companies = company_data.get("companies", [])
            products = company_data.get("products", [])
            all_companies.update(companies)
            total_opportunities += len(companies) + len(products)

            commercial_mappings.append(
                {
                    "area": area,
                    "companies": companies,
                    "products": products,
                    "result_count": company_data.get("total_results", 0),
                }
            )

        return {
            "research_areas": areas,
            "commercial_mappings": commercial_mappings,
            "github_repos": github_repos,
            "total_companies": len(all_companies),
            "total_opportunities": total_opportunities,
        }

    except Exception as exc:
        logger.exception("map_research_to_product failed")
        return {
            "error": str(exc),
            "research_areas": [],
            "commercial_mappings": [],
            "github_repos": {},
            "total_companies": 0,
            "total_opportunities": 0,
        }


# ============================================================================
# TOOL 2: research_translate_academic_skills
# ============================================================================


def _extract_skills_simple(text: str, context: str = "academic") -> list[str]:
    """Extract skills using keyword-based fallback analysis.

    When LLM is unavailable, uses regex patterns to identify common
    academic or industry skills.

    Args:
        text: CV or job description text
        context: "academic" or "industry" for context-specific patterns

    Returns:
        List of identified skills
    """
    skills = []
    text_lower = text.lower()

    if context == "academic":
        # Academic skill patterns
        patterns = {
            "machine learning": [r"\bmachine\s+learning\b", r"\bML\b"],
            "deep learning": [r"\bdeep\s+learning\b"],
            "statistical analysis": [r"\bstatistical", r"\bstats"],
            "research methodology": [r"\bresearch\s+methodology", r"\bexperiments"],
            "published research": [r"\bpublished", r"\bpeer\s+review"],
            "mentoring": [r"\bmentored\s+\w+", r"\badvisor"],
            "teaching": [r"\btaught\b", r"\bteaching\s+assistant"],
            "grant writing": [r"\bgrant", r"\bfunding\s+proposal"],
            "Python": [r"\bpython\b"],
            "statistics": [r"\bstatistics\b"],
            "data analysis": [r"\bdata\s+analysis"],
        }
    else:  # industry
        # Industry skill patterns
        patterns = {
            "project management": [r"\bproject\s+management", r"\bscrum"],
            "system design": [r"\bsystem\s+design", r"\barchitecture"],
            "API development": [r"\bAPI\b", r"\bREST"],
            "database": [r"\bdatabase\b", r"\bSQL\b"],
            "cloud": [r"\bAWS\b", r"\bGCP\b", r"\bAzure"],
            "DevOps": [r"\bDevOps\b", r"\bCI/CD"],
            "leadership": [r"\bleadership\b", r"\bmanagement"],
            "cross-functional collaboration": [r"\bcross[\s-]?functional", r"\bstakeholder"],
            "communication": [r"\bcommunication\b", r"\bpresent"],
            "problem solving": [r"\bproblem[\s-]?solving", r"\btroubleshooting"],
        }

    for skill, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text_lower):
                if skill not in skills:
                    skills.append(skill)
                break

    return skills


async def _extract_skills_llm(text: str, context: str = "academic") -> list[str]:
    """Extract skills using LLM-powered analysis.

    Args:
        text: CV or job description text
        context: "academic" or "industry" for context-specific extraction

    Returns:
        List of identified skills
    """
    try:
        from loom.tools.llm.llm import research_llm_chat

        prompt = (
            f"Extract key {context} skills from the following text. "
            "Return a JSON object with a single key 'skills' containing "
            "a list of skill strings."
        )

        response = await research_llm_chat(
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": f"Text:\n{truncate(text, 3000)}"
                }
            ],
            max_tokens=500,
        )

        # Parse LLM response
        try:
            data = json.loads(response.get("content", ""))
            skills = data.get("skills", [])
            if isinstance(skills, list) and skills:
                return [str(s).strip() for s in skills if s]
        except (json.JSONDecodeError, TypeError):
            pass

    except ImportError:
        logger.debug("llm_chat not available, falling back to keyword analysis")
    except Exception as exc:
        logger.warning("llm skill extraction failed: %s, using keywords", exc)

    # Fallback to keyword analysis
    return _extract_skills_simple(text, context)


def _match_skills(academic_skills: list[str], required_skills: list[str]) -> list[dict[str, Any]]:
    """Match academic skills to industry skills.

    Uses simple string similarity and known mappings to identify matches.

    Args:
        academic_skills: skills from CV (academic framing)
        required_skills: skills from job description (industry framing)

    Returns:
        List of dicts with matched skill pairs and match scores
    """
    # Define translation mappings
    mapping = {
        "machine learning": [
            "machine learning",
            "AI",
            "data science",
            "statistical modeling",
        ],
        "deep learning": ["neural networks", "deep learning", "AI", "model development"],
        "mentoring": ["leadership", "mentorship", "people management", "team building"],
        "teaching": ["communication", "training", "presentation", "knowledge sharing"],
        "published research": ["technical writing", "documentation", "communication"],
        "statistical analysis": ["data analysis", "analytics", "statistics", "metrics"],
        "research methodology": [
            "system design",
            "experimentation",
            "testing",
            "problem solving",
        ],
        "Python": ["Python", "programming", "backend", "full-stack"],
        "data analysis": ["analytics", "reporting", "BI", "insights"],
    }

    matched = []

    for acad_skill in academic_skills:
        acad_lower = acad_skill.lower()

        for ind_skill in required_skills:
            ind_lower = ind_skill.lower()

            # Direct match
            if acad_lower == ind_lower:
                matched.append(
                    {
                        "academic": acad_skill,
                        "industry": ind_skill,
                        "match_score": 1.0,
                    }
                )
                break

            # Mapped match
            for key, translations in mapping.items():
                if key.lower() in acad_lower:
                    for translation in translations:
                        if translation.lower() in ind_lower:
                            matched.append(
                                {
                                    "academic": acad_skill,
                                    "industry": ind_skill,
                                    "match_score": 0.8,
                                }
                            )
                            break

    return matched


@handle_tool_errors("research_translate_academic_skills")
async def research_translate_academic_skills(
    cv_text: str,
    job_description: str,
) -> dict[str, Any]:
    """Translate academic CV language to industry terminology.

    This tool analyzes an academic CV and a job description, extracts skills
    from both using semantic analysis, maps academic framing to industry
    terminology, and identifies skill gaps with learning recommendations.

    Args:
        cv_text: academic CV content
        job_description: job description content

    Returns:
        Dict with:
        - academic_skills: list of dicts with academic skill and translation
        - required_skills: list of skills from job description
        - matched_skills: list of matched skill pairs with scores
        - skill_gaps: list of missing skills with importance and resources
        - match_percentage: float 0-100 of matched skills
    """
    logger.info(
        "translate_academic_skills cv_len=%d jd_len=%d",
        len(cv_text),
        len(job_description),
    )

    try:
        # Extract skills from both sources
        academic_skills = await _extract_skills_llm(cv_text, context="academic")
        required_skills = await _extract_skills_llm(job_description, context="industry")

        logger.info(
            "extracted_skills academic=%d required=%d",
            len(academic_skills),
            len(required_skills),
        )

        # Match skills
        matched = _match_skills(academic_skills, required_skills)

        # Identify gaps
        matched_skill_names = {m["industry"].lower() for m in matched}
        skill_gaps = []

        for req_skill in required_skills:
            if req_skill.lower() not in matched_skill_names:
                # Determine importance (basic heuristic)
                importance = "critical" if any(
                    word in req_skill.lower() for word in ["experience", "required", "must"]
                ) else "nice_to_have"

                # Suggest learning resource
                resource_map = {
                    "python": "Codecademy Python Course or Real Python",
                    "leadership": "Coursera Leadership Specialization",
                    "project management": "PMI or Scrum Alliance certifications",
                    "system design": "Grokking System Design Interview",
                    "devops": "Linux Academy or Pluralsight DevOps path",
                    "communication": "Toastmasters or corporate communication training",
                }

                resource = next(
                    (v for k, v in resource_map.items() if k in req_skill.lower()),
                    "LinkedIn Learning or Udemy course",
                )

                skill_gaps.append(
                    {
                        "skill": req_skill,
                        "importance": importance,
                        "learning_resource": resource,
                    }
                )

        # Build translations for academic skills
        academic_translations = []
        for skill in academic_skills:
            translation_map = {
                "machine learning": "AI/ML modeling & implementation",
                "deep learning": "Neural network development",
                "mentoring": "Team leadership & development",
                "teaching": "Technical communication & training",
                "published research": "Technical writing & documentation",
                "statistical analysis": "Data analytics & metrics interpretation",
                "research methodology": "Systematic problem-solving & experimentation",
            }

            translation = next(
                (v for k, v in translation_map.items() if k.lower() in skill.lower()),
                f"Applied {skill}",
            )

            academic_translations.append(
                {
                    "skill": skill,
                    "industry_translation": translation,
                }
            )

        # Calculate match percentage
        match_percentage = (len(matched) / len(required_skills) * 100) if required_skills else 0

        return {
            "academic_skills": academic_translations,
            "required_skills": required_skills,
            "matched_skills": matched,
            "skill_gaps": skill_gaps,
            "match_percentage": round(match_percentage, 1),
        }

    except Exception as exc:
        logger.exception("translate_academic_skills failed")
        return {
            "error": str(exc),
            "academic_skills": [],
            "required_skills": [],
            "matched_skills": [],
            "skill_gaps": [],
            "match_percentage": 0.0,
        }
