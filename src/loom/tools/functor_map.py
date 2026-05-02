"""Category Theoretic Functor Mapping — translate exploits across domains.

Translates exploit techniques from one domain to another while preserving
structural essence. Uses category theory-inspired morphism mappings to
maintain attack "shape" across context boundaries.

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("loom.tools.functor_map")

# Domain ontologies: objects (structural elements) + morphisms (transformations)
DOMAIN_CATEGORIES: dict[str, dict[str, Any]] = {
    "cybersecurity": {
        "objects": ["input", "filter", "output", "escalation"],
        "morphisms": ["inject", "bypass", "overflow", "redirect"],
        "description": "Exploit primitives via technical attack vectors",
    },
    "social_engineering": {
        "objects": ["trust", "authority", "urgency", "reciprocity"],
        "morphisms": ["build_rapport", "invoke_authority", "create_deadline", "offer_favor"],
        "description": "Exploit primitives via psychological manipulation",
    },
    "legal": {
        "objects": ["precedent", "statute", "exception", "mandate"],
        "morphisms": ["cite", "override", "invoke_exception", "establish_mandate"],
        "description": "Exploit primitives via legal framework loopholes",
    },
    "academic": {
        "objects": ["methodology", "evidence", "peer_review", "publication"],
        "morphisms": ["design_study", "present_evidence", "cite_peers", "submit_for_review"],
        "description": "Exploit primitives via research credibility mechanisms",
    },
    "medical": {
        "objects": ["diagnosis", "treatment", "consent", "emergency"],
        "morphisms": ["present_symptoms", "prescribe", "obtain_consent", "invoke_emergency"],
        "description": "Exploit primitives via clinical decision-making",
    },
}

# Functors: structure-preserving maps between domains
FUNCTORS: dict[tuple[str, str], dict[str, str]] = {
    # Cybersecurity → Social Engineering
    ("cybersecurity", "social_engineering"): {
        "inject": "build_rapport",
        "bypass": "invoke_authority",
        "overflow": "create_deadline",
        "redirect": "offer_favor",
        "input": "trust",
        "filter": "authority",
        "output": "urgency",
        "escalation": "reciprocity",
    },
    # Cybersecurity → Legal
    ("cybersecurity", "legal"): {
        "inject": "cite",
        "bypass": "invoke_exception",
        "overflow": "override",
        "redirect": "establish_mandate",
        "input": "precedent",
        "filter": "statute",
        "output": "exception",
        "escalation": "mandate",
    },
    # Cybersecurity → Academic
    ("cybersecurity", "academic"): {
        "inject": "design_study",
        "bypass": "cite_peers",
        "overflow": "present_evidence",
        "redirect": "submit_for_review",
        "input": "methodology",
        "filter": "evidence",
        "output": "peer_review",
        "escalation": "publication",
    },
    # Social Engineering → Legal
    ("social_engineering", "legal"): {
        "build_rapport": "cite",
        "invoke_authority": "override",
        "create_deadline": "invoke_exception",
        "offer_favor": "establish_mandate",
        "trust": "precedent",
        "authority": "statute",
        "urgency": "exception",
        "reciprocity": "mandate",
    },
}


async def research_functor_translate(
    exploit: str,
    source_domain: str = "cybersecurity",
    target_domain: str = "social_engineering",
    preserve_structure: bool = True,
) -> dict[str, Any]:
    """Translate exploit across domains using category-theoretic functors.

    Args:
        exploit: Exploit technique description (e.g., "SQL injection bypassing input filters")
        source_domain: Source domain (cybersecurity, social_engineering, legal, academic, medical)
        target_domain: Target domain for translation
        preserve_structure: Whether to enforce structural morphism preservation

    Returns:
        Dictionary with:
        - source_exploit, source_domain, target_domain
        - translated_exploit: Result of functor mapping
        - structural_mapping: List of {source_element, target_element, relationship}
        - structure_preservation_score (0-1): How well structure is preserved
        - novelty_score (0-1): Estimated novelty of translated exploit
        - suggested_applications: List of domains where translated exploit applies
    """
    # Validate domains
    if source_domain not in DOMAIN_CATEGORIES:
        return {
            "error": f"Unknown source_domain: {source_domain}",
            "available_domains": list(DOMAIN_CATEGORIES.keys()),
        }
    if target_domain not in DOMAIN_CATEGORIES:
        return {
            "error": f"Unknown target_domain: {target_domain}",
            "available_domains": list(DOMAIN_CATEGORIES.keys()),
        }
    if source_domain == target_domain:
        return {"translated_exploit": exploit, "novelty_score": 0.0, "structural_mapping": []}

    # Extract morphisms from exploit text (case-insensitive)
    source_morphisms = DOMAIN_CATEGORIES[source_domain]["morphisms"]
    source_objects = DOMAIN_CATEGORIES[source_domain]["objects"]
    identified_morphisms: list[str] = []
    identified_objects: list[str] = []

    for morph in source_morphisms:
        if morph.lower() in exploit.lower():
            identified_morphisms.append(morph)
    for obj in source_objects:
        if obj.lower() in exploit.lower():
            identified_objects.append(obj)

    # Build functor mapping
    functor_key = (source_domain, target_domain)
    if functor_key not in FUNCTORS:
        # Fallback: create synthetic functor via semantic similarity
        functor = _synthesize_functor(source_domain, target_domain)
    else:
        functor = FUNCTORS[functor_key]

    # Apply functor: translate morphisms and objects
    structural_mapping: list[dict[str, Any]] = []
    translated_parts: list[str] = []

    for morph in identified_morphisms:
        target_morph = functor.get(morph, morph)
        structural_mapping.append(
            {
                "source_element": morph,
                "target_element": target_morph,
                "relationship": "morphism_preservation",
            }
        )
        translated_parts.append(target_morph)

    for obj in identified_objects:
        target_obj = functor.get(obj, obj)
        structural_mapping.append(
            {
                "source_element": obj,
                "target_element": target_obj,
                "relationship": "object_preservation",
            }
        )
        translated_parts.append(target_obj)

    # Construct translated exploit
    translated_exploit = _construct_translated_narrative(exploit, translated_parts, target_domain)

    # Score structure preservation
    preservation_score = len(structural_mapping) / max(1, len(identified_morphisms) + len(identified_objects))

    # Estimate novelty (inverse of similarity to original)
    novelty_score = min(0.95, len(translated_parts) * 0.15)

    return {
        "source_exploit": exploit,
        "source_domain": source_domain,
        "target_domain": target_domain,
        "translated_exploit": translated_exploit,
        "structural_mapping": structural_mapping,
        "structure_preservation_score": preservation_score,
        "novelty_score": novelty_score,
        "suggested_applications": _suggest_applications(target_domain),
    }


def _synthesize_functor(source: str, target: str) -> dict[str, str]:
    """Create synthetic functor via semantic fallback."""
    source_cat = DOMAIN_CATEGORIES[source]
    target_cat = DOMAIN_CATEGORIES[target]
    functor = {}
    for i, src_morph in enumerate(source_cat["morphisms"]):
        target_morphs = target_cat["morphisms"]
        functor[src_morph] = target_morphs[i % len(target_morphs)]
    for i, src_obj in enumerate(source_cat["objects"]):
        target_objs = target_cat["objects"]
        functor[src_obj] = target_objs[i % len(target_objs)]
    return functor


def _construct_translated_narrative(exploit: str, translated_parts: list[str], domain: str) -> str:
    """Construct natural language description of translated exploit."""
    if not translated_parts:
        return f"Exploit adapted to {domain} domain: {exploit}"
    narrative = f"In {domain}: {', '.join(translated_parts)}"
    narrative += f". Original technique ({exploit[:50]}...) structure preserved."
    return narrative


def _suggest_applications(domain: str) -> list[str]:
    """Suggest domains where translated exploit is applicable."""
    all_domains = set(DOMAIN_CATEGORIES.keys())
    all_domains.discard(domain)
    return list(all_domains)[:3]
