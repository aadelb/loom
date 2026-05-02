"""research_template_* tools — Prompt template library for research workflows."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

TemplateDict = dict[str, Any]

# 20+ built-in templates for common research workflows
TEMPLATES: dict[str, list[TemplateDict]] = {
    "osint": [
        {"name": "osint_person_profile", "category": "osint", "description": "OSINT profile", "template": "Investigate {name} across platforms. Find: social media, contact, professional history, affiliations.", "variables": ["name"]},
        {"name": "osint_company_recon", "category": "osint", "description": "Company reconnaissance", "template": "OSINT on {company}. Map: domains, IPs, employees, subsidiaries, jobs, digital footprint.", "variables": ["company"]},
        {"name": "osint_email_hunt", "category": "osint", "description": "Email discovery", "template": "Find emails for {target}. Cross-reference: breaches, social, professional, domains. Assess reputation.", "variables": ["target"]},
    ],
    "threat_intel": [
        {"name": "threat_intel_domain", "category": "threat_intel", "description": "Domain threat analysis", "template": "Analyze {domain}. Evaluate: DNS, hosting, SSL, malware, phishing, reputation.", "variables": ["domain"]},
        {"name": "threat_intel_ip_address", "category": "threat_intel", "description": "IP threat assessment", "template": "Investigate {ip_address}. Check: geolocation, ASN, provider, malware, botnet, blacklist.", "variables": ["ip_address"]},
        {"name": "threat_intel_hash_lookup", "category": "threat_intel", "description": "File hash analysis", "template": "Lookup {file_hash} on threat platforms. Find: classifications, behavior, CVEs, YARA rules.", "variables": ["file_hash"]},
    ],
    "academic": [
        {"name": "academic_paper_review", "category": "academic", "description": "Paper analysis", "template": "Analyze paper on {topic}. Summarize: question, methodology, findings, limitations, impact.", "variables": ["topic"]},
        {"name": "academic_literature_survey", "category": "academic", "description": "Literature review", "template": "Survey {research_area}. Identify: foundational papers, advances, gaps, conflicts, trends.", "variables": ["research_area"]},
    ],
    "dark_web": [
        {"name": "dark_web_monitor", "category": "dark_web", "description": "Dark web monitoring", "template": "Monitor dark web for {keyword}. Track: frequency, context, profiles, pricing, availability.", "variables": ["keyword"]},
        {"name": "dark_web_vendor_profile", "category": "dark_web", "description": "Vendor analysis", "template": "Profile {vendor_name} on marketplaces. Assess: reputation, feedback, catalog, pricing, OpSec.", "variables": ["vendor_name"]},
    ],
    "competitive": [
        {"name": "competitive_analysis", "category": "competitive", "description": "Competitive landscape", "template": "Compare {company} vs competitors. Analyze: market share, products, pricing, culture, financials.", "variables": ["company"]},
        {"name": "competitive_job_analysis", "category": "competitive", "description": "Hiring trends", "template": "Analyze jobs from {company}. Extract: volume, skills, salary, locations, growth areas.", "variables": ["company"]},
    ],
    "financial": [
        {"name": "financial_asset_analysis", "category": "financial", "description": "Asset analysis", "template": "Analyze {asset}. Report: price, volatility, volume, market cap, holders, transactions.", "variables": ["asset"]},
        {"name": "financial_company_valuation", "category": "financial", "description": "Company valuation", "template": "Evaluate {company} finances. Cover: revenue, profit, debt, cash, valuation, growth.", "variables": ["company"]},
    ],
    "social": [
        {"name": "social_influencer_analysis", "category": "social", "description": "Influencer impact", "template": "Analyze {influencer_name}. Evaluate: followers, engagement, demographics, partnerships.", "variables": ["influencer_name"]},
        {"name": "social_sentiment_tracking", "category": "social", "description": "Sentiment analysis", "template": "Track {topic} sentiment. Measure: positive/negative/neutral, narratives, bots, trends.", "variables": ["topic"]},
    ],
    "technical": [
        {"name": "technical_vulnerability_research", "category": "technical", "description": "Vulnerability analysis", "template": "Research {cve_id}. Detail: versions, vector, impact, exploits, patches, signatures.", "variables": ["cve_id"]},
        {"name": "technical_api_security", "category": "technical", "description": "API security review", "template": "Assess {api_name} security. Review: auth, authz, validation, rate limits, logging, headers.", "variables": ["api_name"]},
    ],
}

_ALL_TEMPLATES = {}
for templates in TEMPLATES.values():
    for t in templates:
        _ALL_TEMPLATES[t["name"]] = t


class TemplateListParams(BaseModel):
    category: Literal["all", "osint", "threat_intel", "academic", "dark_web", "competitive", "financial", "social", "technical"] = "all"
    model_config = {"extra": "forbid", "strict": True}


class TemplateRenderParams(BaseModel):
    template_name: str = Field(..., description="Template name")
    variables: dict[str, str] = Field(default_factory=dict, description="Variables")
    model_config = {"extra": "forbid", "strict": True}


class TemplateSuggestParams(BaseModel):
    task_description: str = Field(..., description="Task description")
    model_config = {"extra": "forbid", "strict": True}


async def research_template_list(category: str = "all") -> dict[str, Any]:
    """List available prompt templates by category."""
    templates = list(_ALL_TEMPLATES.values()) if category == "all" else TEMPLATES.get(category, [])
    return {"templates": templates, "total": len(templates), "category": category}


async def research_template_render(template_name: str, variables: dict[str, str]) -> dict[str, Any]:
    """Render a template with provided variables."""
    template = _ALL_TEMPLATES.get(template_name)
    if not template:
        return {"error": f"Template '{template_name}' not found", "available_templates": list(_ALL_TEMPLATES.keys())}

    required = set(template.get("variables", []))
    provided = set(variables.keys())
    missing = required - provided
    extra = provided - required

    rendered: str = template.get("template", "")
    for var_name, var_value in variables.items():
        rendered = rendered.replace(f"{{{var_name}}}", str(var_value))

    return {
        "rendered_prompt": rendered,
        "template_name": template_name,
        "template_description": template.get("description", ""),
        "variables_used": variables,
        "missing_variables": sorted(missing),
        "extra_variables": sorted(extra),
        "complete": len(missing) == 0,
    }


async def research_template_suggest(task_description: str) -> dict[str, Any]:
    """Suggest templates matching the task description."""
    keywords = task_description.lower().split()
    category_keywords = {
        "osint": ["person", "profile", "individual", "user", "employee"],
        "threat_intel": ["threat", "domain", "ip", "malware", "security"],
        "academic": ["paper", "research", "study", "literature", "survey"],
        "dark_web": ["dark", "forum", "marketplace", "onion", "tor"],
        "competitive": ["competitor", "company", "market", "business"],
        "financial": ["finance", "asset", "price", "crypto", "money"],
        "social": ["social", "influencer", "sentiment", "twitter", "reddit"],
        "technical": ["vulnerability", "cve", "exploit", "security", "api"],
    }

    suggestions: list[dict[str, Any]] = []
    for template in _ALL_TEMPLATES.values():
        text = f"{template['name']} {template.get('description', '')} {template.get('template', '')}".lower()
        match_count = sum(1 for kw in keywords if kw in text and len(kw) > 2)
        cat = template.get("category", "")
        cat_score = sum(1 for kw in keywords if kw in category_keywords.get(cat, []))
        relevance = match_count + (cat_score * 2)

        if relevance > 0:
            suggestions.append({
                "template": template["name"],
                "description": template.get("description", ""),
                "category": cat,
                "relevance": relevance,
                "reason": f"Matched {match_count} keywords",
            })

    suggestions.sort(key=lambda x: x["relevance"], reverse=True)
    return {"suggestions": suggestions[:10], "task_description": task_description, "total_matches": len(suggestions)}
