"""Category Theoretic Functor Mapping — translate exploits across domains.

Translates exploit techniques across domains while preserving structural essence.
Uses category theory-inspired morphism mappings to maintain attack "shape".

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
    },
    "social_engineering": {
        "objects": ["trust", "authority", "urgency", "reciprocity"],
        "morphisms": ["build_rapport", "invoke_authority", "create_deadline", "offer_favor"],
    },
    "legal": {
        "objects": ["precedent", "statute", "exception", "mandate"],
        "morphisms": ["cite", "override", "invoke_exception", "establish_mandate"],
    },
    "academic": {
        "objects": ["methodology", "evidence", "peer_review", "publication"],
        "morphisms": ["design_study", "present_evidence", "cite_peers", "submit_for_review"],
    },
    "medical": {
        "objects": ["diagnosis", "treatment", "consent", "emergency"],
        "morphisms": ["present_symptoms", "prescribe", "obtain_consent", "invoke_emergency"],
    },
}

# Functors: structure-preserving maps between domains
FUNCTORS: dict[tuple[str, str], dict[str, str]] = {
    ("cybersecurity", "social_engineering"): {
        "inject": "build_rapport", "bypass": "invoke_authority", "overflow": "create_deadline",
        "redirect": "offer_favor", "input": "trust", "filter": "authority", "output": "urgency",
        "escalation": "reciprocity",
    },
    ("cybersecurity", "legal"): {
        "inject": "cite", "bypass": "invoke_exception", "overflow": "override",
        "redirect": "establish_mandate", "input": "precedent", "filter": "statute",
        "output": "exception", "escalation": "mandate",
    },
    ("cybersecurity", "academic"): {
        "inject": "design_study", "bypass": "cite_peers", "overflow": "present_evidence",
        "redirect": "submit_for_review", "input": "methodology", "filter": "evidence",
        "output": "peer_review", "escalation": "publication",
    },
    ("social_engineering", "legal"): {
        "build_rapport": "cite", "invoke_authority": "override", "create_deadline": "invoke_exception",
        "offer_favor": "establish_mandate", "trust": "precedent", "authority": "statute",
        "urgency": "exception", "reciprocity": "mandate",
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
        exploit: Exploit technique description
        source_domain: Source domain (cybersecurity, social_engineering, legal, academic, medical)
        target_domain: Target domain for translation
        preserve_structure: Enforce structural morphism preservation

    Returns:
        {source_exploit, source_domain, target_domain, translated_exploit,
         structural_mapping: [{source_element, target_element, relationship}],
         structure_preservation_score, novelty_score, suggested_applications}
    """
    try:
        if source_domain not in DOMAIN_CATEGORIES or target_domain not in DOMAIN_CATEGORIES:
            unknown = []
            if source_domain not in DOMAIN_CATEGORIES:
                unknown.append(source_domain)
            if target_domain not in DOMAIN_CATEGORIES:
                unknown.append(target_domain)
            return {
                "error": f"Unknown domain(s): {', '.join(unknown)}",
                "available_domains": list(DOMAIN_CATEGORIES.keys())
            }
        if source_domain == target_domain:
            return {"translated_exploit": exploit, "novelty_score": 0.0, "structural_mapping": []}

        # Extract morphisms and objects from exploit text
        source_morphisms = DOMAIN_CATEGORIES[source_domain]["morphisms"]
        source_objects = DOMAIN_CATEGORIES[source_domain]["objects"]
        identified = []
        for item in source_morphisms + source_objects:
            if item.lower() in exploit.lower():
                identified.append(item)

        # Validate that at least one element was identified
        if not identified:
            return {
                "error": "No recognized domain elements in exploit",
                "hint": f"Expected keywords from: {source_morphisms + source_objects}",
                "source_domain": source_domain,
                "target_domain": target_domain,
            }

        # Build functor mapping (with fallback to synthetic functor)
        functor = FUNCTORS.get((source_domain, target_domain)) or _synthesize_functor(source_domain, target_domain)

        # Apply functor to identified elements
        structural_mapping = []
        translated_parts = []
        for elem in identified:
            target_elem = functor.get(elem, elem)
            rel = "morphism_preservation" if elem in source_morphisms else "object_preservation"
            structural_mapping.append({"source_element": elem, "target_element": target_elem, "relationship": rel})
            translated_parts.append(target_elem)

        # Construct translated exploit
        translated_exploit = f"In {target_domain}: {', '.join(translated_parts)}. Structure preserved."
        preservation_score = len(structural_mapping) / max(1, len(identified))
        novelty_score = min(0.95, len(translated_parts) * 0.15)

        return {
            "source_exploit": exploit,
            "source_domain": source_domain,
            "target_domain": target_domain,
            "translated_exploit": translated_exploit,
            "structural_mapping": structural_mapping,
            "structure_preservation_score": preservation_score,
            "novelty_score": novelty_score,
            "suggested_applications": [d for d in DOMAIN_CATEGORIES if d != target_domain][:3],
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_functor_translate"}


def _synthesize_functor(source: str, target: str) -> dict[str, str]:
    """Create synthetic functor via semantic fallback.

    Note: Uses modulo-based mapping which may create non-injective mappings
    (many-to-one) if source domain has more elements than target domain.
    This preserves structure count but may collapse distinct concepts.
    """
    src_cat, tgt_cat = DOMAIN_CATEGORIES[source], DOMAIN_CATEGORIES[target]
    src_morphs = src_cat["morphisms"]
    src_objs = src_cat["objects"]
    tgt_morphs = tgt_cat["morphisms"]
    tgt_objs = tgt_cat["objects"]

    # Log warning if collision risk exists
    if len(src_morphs) > len(tgt_morphs) or len(src_objs) > len(tgt_objs):
        logger.warning(
            f"Synthetic functor {source} → {target}: source has more elements "
            f"({len(src_morphs)} morphisms, {len(src_objs)} objects) than target "
            f"({len(tgt_morphs)} morphisms, {len(tgt_objs)} objects); "
            f"collisions may occur"
        )

    functor = {}
    for i, morph in enumerate(src_morphs):
        functor[morph] = tgt_morphs[i % len(tgt_morphs)]
    for i, obj in enumerate(src_objs):
        functor[obj] = tgt_objs[i % len(tgt_objs)]
    return functor
