"""Resume and interview preparation tools for career development.

Tools:
- research_optimize_resume: ATS-optimized resume analysis with keyword matching
- research_interview_prep: Generate tailored interview preparation materials
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Literal

import httpx

logger = logging.getLogger("loom.tools.resume_intel")

from loom.error_responses import handle_tool_errors


def _extract_keywords(text: str) -> set[str]:
    """Extract and normalize keywords from text.

    Converts to lowercase and removes punctuation.
    """
    # Remove markdown/special formatting
    text = re.sub(r"[*#_-]", " ", text)
    # Split on whitespace and punctuation
    words = re.findall(r"\b\w+\b", text.lower())
    # Filter: remove common stop words and short words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "up", "about", "into", "through", "during",
        "be", "is", "are", "was", "were", "been", "have", "has", "had", "do",
        "does", "did", "will", "would", "could", "should", "may", "might",
        "can", "this", "that", "these", "those", "i", "you", "he", "she",
        "it", "we", "they", "what", "which", "who", "when", "where", "why",
        "how", "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "as", "if", "then", "because", "while", "their",
        "its", "your", "my", "our", "his", "her", "am", "as", "if", "before"
    }
    keywords = {word for word in words if len(word) > 2 and word not in stop_words}
    return keywords


def _compute_match_score(
    resume_keywords: set[str],
    jd_keywords: set[str],
) -> float:
    """Compute ATS match score as percentage overlap.

    Returns: float between 0-100
    """
    if not jd_keywords:
        return 0.0
    matched = len(resume_keywords & jd_keywords)
    return (matched / len(jd_keywords)) * 100.0


async def _get_llm_provider() -> Any:
    """Get the default LLM provider for analysis."""
    try:
        from loom.tools.llm import _get_provider
        from loom.config import CONFIG

        cascade = CONFIG.get("LLM_CASCADE_ORDER", ["nvidia", "openai", "anthropic"])
        for provider_name in cascade:
            try:
                provider = _get_provider(provider_name)
                if await provider.available():
                    return provider
            except Exception:
                continue
        # Fallback
        return _get_provider("openai")
    except ImportError:
        return None


@handle_tool_errors("research_optimize_resume")
async def research_optimize_resume(
    resume_text: str,
    job_description: str,
) -> dict[str, Any]:
    """Analyze and optimize resume for ATS compatibility.

    Extracts keywords from job description and resume, computes match score,
    identifies missing keywords, and suggests semantic improvements.

    Args:
        resume_text: Full resume text content
        job_description: Job description to match against

    Returns:
        Dict with:
        - match_score: 0-100 ATS compatibility percentage
        - matched_keywords: List of keywords found in both
        - missing_keywords: List of missing keywords with importance
        - improvements: Suggested changes per section
        - word_count: Total resume words
        - format_issues: List of formatting problems
        - overall_grade: Letter grade A-F
    """
    logger.info("optimize_resume started")

    if not resume_text or len(resume_text.strip()) < 100:
        raise ValueError("Resume text must be at least 100 characters")
    if not job_description or len(job_description.strip()) < 50:
        raise ValueError("Job description must be at least 50 characters")

    # Extract keywords
    jd_keywords = _extract_keywords(job_description)
    resume_keywords = _extract_keywords(resume_text)

    # Compute basic match
    match_score = _compute_match_score(resume_keywords, jd_keywords)
    matched_keywords = list(resume_keywords & jd_keywords)

    # Identify missing keywords
    missing = jd_keywords - resume_keywords
    missing_keywords: list[dict[str, Any]] = []

    # Categorize importance: required skills vs preferred
    required_patterns = [
        r"\brequired\b", r"\bmust\b", r"\bessential\b",
        r"\bcore\b", r"\bprimary\b", r"\bkey\b"
    ]
    preferred_patterns = [
        r"\bpreferred\b", r"\bnice.to.have\b", r"\bbonus\b", r"\boptional\b"
    ]

    jd_lower = job_description.lower()

    for keyword in sorted(missing):
        importance = "preferred"
        # Check if keyword appears near required/preferred language
        for req_pat in required_patterns:
            if re.search(rf"{req_pat}.*{re.escape(keyword)}", jd_lower, re.IGNORECASE):
                importance = "required"
                break

        missing_keywords.append({
            "keyword": keyword,
            "importance": importance,
            "suggestion": f"Add '{keyword}' to resume, especially in skills section" if importance == "required"
                        else f"Consider adding '{keyword}' to enhance candidacy",
        })

    # Sort: required first
    missing_keywords.sort(key=lambda x: (x["importance"] != "required", x["keyword"]))

    # Format issues analysis
    format_issues: list[str] = []
    word_count = len(resume_text.split())

    if word_count < 300:
        format_issues.append("Resume appears too brief (recommend 300+ words)")
    elif word_count > 1000:
        format_issues.append("Resume appears too long (recommend <1000 words)")

    if not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}", resume_text):
        format_issues.append("No email address found")

    if not re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", resume_text):
        format_issues.append("No phone number found")

    # Try LLM-based semantic analysis if available
    improvements: list[dict[str, Any]] = []
    try:
        provider = await _get_llm_provider()
        if provider:
            # Ask LLM for semantic matching beyond keywords
            prompt = f"""Analyze this resume against the job description and provide 2-3 specific improvements.

Resume excerpt:
{resume_text[:800]}

Job Description excerpt:
{job_description[:800]}

Provide suggestions as JSON array with structure:
[{{"section": "Skills|Experience|Summary|Education", "current": "current text snippet", "suggested": "improved text", "reason": "why this helps"}}]

Only return valid JSON, no markdown."""

            messages = [{"role": "user", "content": prompt}]
            response = await provider.chat(messages, max_tokens=500, temperature=0.3)
            if response and response.text:
                try:
                    # Try to extract JSON from response (non-greedy match)
                    json_match = re.search(r"\[.*?\]", response.text, re.DOTALL)
                    if json_match:
                        improvements = json.loads(json_match.group())
                        if not isinstance(improvements, list):
                            improvements = []
                except (json.JSONDecodeError, ValueError):
                    improvements = []
    except Exception as e:
        logger.debug("llm_analysis_failed: %s", str(e))
        improvements = []

    # Compute overall grade based on match score and format
    if match_score >= 85 and not format_issues:
        overall_grade = "A"
    elif match_score >= 70 and len(format_issues) <= 1:
        overall_grade = "B"
    elif match_score >= 55 or len(format_issues) <= 2:
        overall_grade = "C"
    elif match_score >= 40:
        overall_grade = "D"
    else:
        overall_grade = "F"

    result = {
        "match_score": round(match_score, 1),
        "matched_keywords": sorted(matched_keywords),
        "missing_keywords": missing_keywords[:20],  # Top 20
        "improvements": improvements[:5],  # Top 5
        "word_count": word_count,
        "format_issues": format_issues,
        "overall_grade": overall_grade,
    }

    logger.info(
        "optimize_resume completed grade=%s score=%.1f",
        overall_grade,
        match_score,
    )

    return result


@handle_tool_errors("research_interview_prep")
async def research_interview_prep(
    job_description: str,
    company: str | None = None,
    interview_type: str = "behavioral",
) -> dict[str, Any]:
    """Generate tailored interview preparation materials.

    Analyzes job description, optionally searches for company info,
    and generates relevant interview questions grouped by type.

    Args:
        job_description: Job description text
        company: Optional company name for company-specific research
        interview_type: "behavioral", "technical", or "mixed"

    Returns:
        Dict with:
        - company: Company name (if provided)
        - role_summary: Brief role summary from JD
        - questions: Dict with behavioral/technical/situational questions
        - key_topics_to_study: Topics to prepare
        - company_values: Company values (if found)
        - total_questions: Total questions generated
    """
    logger.info("interview_prep started company=%s type=%s", company, interview_type)

    if not job_description or len(job_description.strip()) < 100:
        raise ValueError("Job description must be at least 100 characters")

    # Extract key skills and requirements from JD
    jd_keywords = _extract_keywords(job_description)

    # Extract role title and summary
    role_match = re.search(
        r"(?:job title|position|role)[:=\s]*([^\n]+)|^([A-Za-z\s]+(?:Engineer|Developer|Manager|Analyst|Specialist))",
        job_description,
        re.IGNORECASE | re.MULTILINE,
    )
    if role_match:
        role_title = (role_match.group(1) or role_match.group(2) or "Candidate").strip()
    else:
        role_title = "Candidate"
    role_summary = f"This interview will focus on {role_title} position. Key areas: {', '.join(sorted(list(jd_keywords)[:5]))}"

    questions: dict[str, list[dict[str, str]]] = {
        "technical": [],
        "behavioral": [],
        "situational": [],
    }

    company_values: list[str] | None = None

    # Fetch company info if provided
    if company:
        try:
            company_values = await _fetch_company_values(company)
        except Exception as e:
            logger.debug("company_fetch_failed: %s", str(e))
            company_values = None

    # Generate questions using LLM
    try:
        provider = await _get_llm_provider()
        if provider:
            questions = await _generate_questions_with_llm(
                provider,
                job_description,
                role_title,
                interview_type,
                company_values or [],
            )
    except Exception as e:
        logger.debug("llm_question_generation_failed: %s", str(e))
        # Fallback: generate basic questions
        questions = _generate_basic_questions(job_description, role_title)

    # Extract key topics to study
    key_topics = _extract_key_topics(job_description, jd_keywords)

    total_questions = (
        len(questions.get("technical", []))
        + len(questions.get("behavioral", []))
        + len(questions.get("situational", []))
    )

    result = {
        "company": company,
        "role_summary": role_summary,
        "questions": questions,
        "key_topics_to_study": key_topics,
        "company_values": company_values,
        "total_questions": total_questions,
    }

    logger.info(
        "interview_prep completed company=%s total_questions=%d",
        company,
        total_questions,
    )

    return result


async def _fetch_company_values(company: str) -> list[str] | None:
    """Search for company values using web search.

    Returns list of company values or None if not found.
    """
    try:
        from loom.tools.search import research_search

        results = await research_search(
            query=f"{company} company values mission",
            n=3,
        )

        if results and isinstance(results, dict) and results.get("results"):
            # Extract values from search results
            values_text = " ".join(
                [r.get("description", "") for r in results["results"][:2]]
            )
            values = _extract_keywords(values_text)
            return sorted(list(values))[:5] if values else None
    except Exception as e:
        logger.debug("company_values_fetch_failed: %s", str(e))

    return None


def _generate_basic_questions(
    job_description: str,
    role_title: str,
) -> dict[str, list[dict[str, str]]]:
    """Generate basic fallback interview questions.

    Used when LLM is unavailable.
    """
    questions: dict[str, list[dict[str, str]]] = {
        "technical": [
            {
                "question": f"Describe your experience with the key technologies mentioned in this {role_title} role.",
                "tip": "Be specific about projects where you used these technologies",
                "difficulty": "medium",
            },
            {
                "question": "Walk us through a complex technical problem you solved.",
                "tip": "Structure: situation, challenge, solution, outcome (STAR method)",
                "difficulty": "hard",
            },
        ],
        "behavioral": [
            {
                "question": "Tell us about a time you overcame a significant challenge at work.",
                "tip": "Use STAR framework: Situation, Task, Action, Result",
                "star_framework": "Describe the situation and task, explain your action, highlight the positive result",
            },
            {
                "question": "How do you handle disagreement with team members?",
                "tip": "Show collaboration and respect for different viewpoints",
                "star_framework": "Situation: disagreement occurred, Task: needed resolution, Action: communicated respectfully, Result: positive outcome",
            },
            {
                "question": "Why are you interested in this role?",
                "tip": "Reference specific aspects of the job description and company",
                "star_framework": "Show alignment with role requirements and personal growth goals",
            },
        ],
        "situational": [
            {
                "question": f"If you were assigned a task outside your current expertise for this {role_title} role, how would you approach it?",
                "tip": "Show willingness to learn and seek help when needed",
            },
            {
                "question": "How would you prioritize multiple competing deadlines?",
                "tip": "Discuss communication, planning, and impact assessment",
            },
        ],
    }
    return questions


async def _generate_questions_with_llm(
    provider: Any,
    job_description: str,
    role_title: str,
    interview_type: str,
    company_values: list[str],
) -> dict[str, list[dict[str, str]]]:
    """Generate interview questions using LLM.

    Returns dict with technical, behavioral, and situational questions.
    """
    prompt = f"""Generate interview questions for a {role_title} role.

Job Description:
{job_description[:1000]}

Company Values (if known): {', '.join(company_values) if company_values else 'Unknown'}

Generate JSON with this structure:
{{
  "technical": [
    {{"question": "...", "tip": "...", "difficulty": "easy|medium|hard"}}
  ],
  "behavioral": [
    {{"question": "...", "tip": "...", "star_framework": "..."}}
  ],
  "situational": [
    {{"question": "...", "tip": "..."}}
  ]
}}

Generate 2-3 questions per category. Only return valid JSON."""

    messages = [{"role": "user", "content": prompt}]
    response = await provider.chat(messages, max_tokens=1000, temperature=0.5)

    if not response or not response.text:
        return _generate_basic_questions(job_description, role_title)

    try:
        # Extract JSON from response (non-greedy match)
        json_match = re.search(r"\{.*?\}", response.text, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
            # Validate structure
            if isinstance(questions, dict) and all(
                k in questions for k in ["technical", "behavioral", "situational"]
            ):
                return questions
    except (json.JSONDecodeError, ValueError):
        pass

    return _generate_basic_questions(job_description, role_title)


def _extract_key_topics(
    job_description: str,
    keywords: set[str],
) -> list[str]:
    """Extract key topics to study from job description.

    Returns prioritized list of topics.
    """
    # Technical topic patterns
    tech_patterns = [
        r"(?:python|java|javascript|typescript|c\+\+|rust|go|ruby)",
        r"(?:react|vue|angular|node\.?js|django|flask|fastapi)",
        r"(?:sql|postgres|mysql|mongodb|redis|elastic)",
        r"(?:aws|gcp|azure|docker|kubernetes|terraform)",
        r"(?:rest|graphql|grpc|api|json|xml)",
    ]

    soft_patterns = [
        r"(?:leadership|team|communication|collaboration)",
        r"(?:problem.solving|critical.thinking|analysis)",
        r"(?:project.management|agile|scrum)",
    ]

    topics: list[str] = []
    jd_lower = job_description.lower()

    # Find technical topics
    for pattern in tech_patterns:
        matches = re.findall(pattern, jd_lower, re.IGNORECASE)
        if matches:
            topics.append(matches[0].title())

    # Find soft skill topics
    for pattern in soft_patterns:
        matches = re.findall(pattern, jd_lower, re.IGNORECASE)
        if matches:
            topics.append(matches[0].title().replace(".", " "))

    # Add top keywords as topics
    topics.extend(sorted(list(keywords)[:5]))

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique_topics: list[str] = []
    for topic in topics:
        topic_lower = topic.lower()
        if topic_lower not in seen:
            seen.add(topic_lower)
            unique_topics.append(topic)

    return unique_topics[:15]  # Return top 15 topics
