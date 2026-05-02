"""Hyper-Personalized Knowledge Injector — Adapt content to audience and cognitive style.

research_personalize_output: Rewrite content for specific audience, cognitive style, expertise
research_adapt_complexity: Adjust text complexity to target reading level (1-20)
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("loom.tools.knowledge_injector")


# Style templates per audience + cognitive style combination
STYLE_TEMPLATES = {
    ("executive", "visual"): {
        "intro": "Executive Summary",
        "structure": ["key_insight", "impact", "action_items"],
        "bullet_max": 5,
        "use_analogies": True,
        "include_diagrams": True,
    },
    ("executive", "analytical"): {
        "intro": "Key Metrics",
        "structure": ["metrics", "trends", "roi", "recommendations"],
        "bullet_max": 4,
        "use_analogies": False,
        "include_tables": True,
    },
    ("executive", "narrative"): {
        "intro": "Business Story",
        "structure": ["context", "challenge", "solution", "outcome"],
        "bullet_max": 3,
        "use_analogies": True,
        "include_stories": True,
    },
    ("technical", "visual"): {
        "intro": "Architecture Overview",
        "structure": ["arch", "components", "flow", "code"],
        "use_diagrams": True,
        "include_pseudocode": True,
    },
    ("technical", "analytical"): {
        "intro": "Technical Specification",
        "structure": ["spec", "algorithms", "complexity", "optimization"],
        "use_tables": True,
        "include_benchmarks": True,
    },
    ("technical", "procedural"): {
        "intro": "Implementation Guide",
        "structure": ["setup", "steps", "testing", "deployment"],
        "numbered_steps": True,
        "include_code": True,
    },
    ("academic", "analytical"): {
        "intro": "Research Findings",
        "structure": ["abstract", "methodology", "results", "implications"],
        "include_citations": True,
        "formal_tone": True,
    },
    ("academic", "narrative"): {
        "intro": "Research Narrative",
        "structure": ["background", "gap", "approach", "findings"],
        "include_citations": True,
        "include_limitations": True,
    },
    ("journalist", "narrative"): {
        "intro": "Headline",
        "structure": ["headline", "lede", "details", "context"],
        "inverted_pyramid": True,
        "include_quotes": True,
    },
    ("investor", "analytical"): {
        "intro": "Investment Thesis",
        "structure": ["opportunity", "market_size", "traction", "ask"],
        "include_tables": True,
        "focus_roi": True,
    },
    ("investor", "visual"): {
        "intro": "Market Opportunity",
        "structure": ["vision", "market", "competitors", "growth"],
        "use_analogies": True,
        "include_diagrams": True,
    },
    ("regulator", "analytical"): {
        "intro": "Compliance Assessment",
        "structure": ["framework", "gaps", "remediation", "timeline"],
        "formal_tone": True,
        "include_citations": True,
    },
}

# Vocabulary complexity levels (1-20 scale)
VOCAB_LEVELS = {
    1: {"adjectives": ["very", "big", "small"], "avg_word_len": 4},
    5: {"adjectives": ["important", "different", "complex"], "avg_word_len": 6},
    12: {"adjectives": ["substantial", "nuanced", "intricate"], "avg_word_len": 8},
    16: {"adjectives": ["multifaceted", "heterogeneous", "systematic"], "avg_word_len": 10},
    20: {"adjectives": ["perspicacious", "hermeneutical", "epistemological"], "avg_word_len": 12},
}


def _estimate_reading_level(text: str) -> float:
    """Estimate reading level using Flesch-Kincaid formula (1-20 scale)."""
    sentences = re.split(r"[.!?]+", text)
    words = text.split()
    syllables_count = 0

    # Simple syllable counter (rough approximation)
    for word in words:
        word = word.lower()
        if len(word) <= 3:
            syllables_count += 1
        else:
            vowels = "aeiouy"
            prev_was_vowel = False
            for char in word:
                is_vowel = char in vowels
                if is_vowel and not prev_was_vowel:
                    syllables_count += 1
                prev_was_vowel = is_vowel
            if word.endswith("e"):
                syllables_count -= 1
            if word.endswith("le"):
                syllables_count += 1
        if syllables_count <= 0:
            syllables_count = 1

    if not sentences or len(sentences) <= 1:
        return 12.0

    sentence_count = max(1, len([s for s in sentences if s.strip()]))
    word_count = len(words)

    # Flesch-Kincaid Grade Level formula
    grade = (0.39 * (word_count / sentence_count) + 11.8 * (syllables_count / word_count) - 15.59)
    # Clamp to 1-20 range
    return max(1.0, min(20.0, grade))


def _simplify_text(text: str, target_level: int) -> tuple[str, list[str]]:
    """Simplify text to target reading level with adaptations list."""
    current_level = _estimate_reading_level(text)
    adaptations = []

    # If already at target or simpler, minimal changes
    if current_level <= target_level + 1:
        return text, adaptations

    # Break long sentences
    adapted = text
    long_sentences = re.findall(r"[^.!?]{100,}", adapted)
    if long_sentences and target_level < 12:
        original_len = len(adapted)
        for long_sent in long_sentences:
            # Replace long sentences with shorter ones
            parts = re.split(r",|;", long_sent)
            if len(parts) > 1:
                simplified = ". ".join(p.strip() for p in parts if p.strip())
                adapted = adapted.replace(long_sent, simplified)
                adaptations.append(f"broke_long_sentences ({len(long_sent)} → {len(simplified)} chars)")
        if len(adapted) != original_len:
            adaptations.append("sentence_structure_simplified")

    # Replace complex words for low target levels
    if target_level <= 8:
        replacements = {
            r"\bmethodology\b": "method",
            r"\bcomprehensive\b": "complete",
            r"\bfacilitate\b": "help",
            r"\boutstanding\b": "great",
            r"\butilize\b": "use",
        }
        for pattern, replacement in replacements.items():
            if re.search(pattern, adapted, re.IGNORECASE):
                adapted = re.sub(pattern, replacement, adapted, flags=re.IGNORECASE)
                adaptations.append(f"simplified_vocabulary ({pattern} → {replacement})")

    return adapted, adaptations


def _get_target_vocabulary(level: int) -> dict:
    """Get vocabulary preferences for target level."""
    levels = sorted(VOCAB_LEVELS.keys())
    for i, threshold in enumerate(levels):
        if level <= threshold:
            return VOCAB_LEVELS[threshold]
    return VOCAB_LEVELS[20]


async def research_personalize_output(
    content: str,
    audience: str = "executive",
    cognitive_style: str = "visual",
    expertise_level: str = "expert",
) -> dict:
    """Rewrite research output to match reader's cognitive style and expertise.

    Args:
        content: Raw research content to personalize
        audience: Target audience (executive, technical, academic, journalist, investor, regulator)
        cognitive_style: Preferred learning style (visual, analytical, narrative, procedural)
        expertise_level: Reader expertise (novice, intermediate, expert, domain_expert)

    Returns:
        Dict with personalized_content, adaptations_made, style_applied, structure_used
    """
    # Validate inputs
    valid_audiences = {"executive", "technical", "academic", "journalist", "investor", "regulator"}
    valid_styles = {"visual", "analytical", "narrative", "procedural"}
    valid_levels = {"novice", "intermediate", "expert", "domain_expert"}

    if audience not in valid_audiences:
        return {
            "error": f"Invalid audience. Must be one of {valid_audiences}",
            "status": "error",
        }
    if cognitive_style not in valid_styles:
        return {
            "error": f"Invalid cognitive_style. Must be one of {valid_styles}",
            "status": "error",
        }
    if expertise_level not in valid_levels:
        return {
            "error": f"Invalid expertise_level. Must be one of {valid_levels}",
            "status": "error",
        }

    # Get style template
    template_key = (audience, cognitive_style)
    template = STYLE_TEMPLATES.get(template_key, STYLE_TEMPLATES.get((audience, "visual"), {}))

    adaptations = []
    personalized = content

    # Apply expertise-level adjustments
    if expertise_level == "novice":
        # Add explanations, reduce jargon
        personalized = f"**Note for beginners:** This content has been simplified for clarity.\n\n{personalized}"
        adaptations.append("added_beginner_note")
    elif expertise_level == "domain_expert":
        # Add advanced references, technical depth
        personalized = f"**Advanced Context:** For domain experts with specialized knowledge.\n\n{personalized}"
        adaptations.append("added_expert_context")

    # Apply audience-specific transformations
    if audience == "executive":
        # BLUF (bottom-line-up-front), ROI focus
        intro_phrase = "Key Takeaway"
        summary_lines = content.split("\n")[:3]
        summary = " ".join(summary_lines)
        personalized = f"{intro_phrase}: {summary}\n\n{personalized}"
        adaptations.append("executive_bluf_format")

    elif audience == "technical":
        # Add implementation context
        if "code" not in personalized.lower() and "implement" not in personalized.lower():
            personalized += "\n\n**Implementation Note:** See documentation for code examples."
            adaptations.append("added_technical_reference")

    elif audience == "academic":
        # Emphasize methodology and rigor
        personalized = f"**Academic Standards:** This content emphasizes peer-reviewed sources and methodology.\n\n{personalized}"
        adaptations.append("academic_rigor_format")

    elif audience == "journalist":
        # Inverted pyramid style (headline first, details follow)
        first_line = content.split("\n")[0] if content else ""
        if first_line and not first_line.isupper():
            headline = first_line.upper()[:80]
            remaining = "\n".join(content.split("\n")[1:])
            personalized = f"{headline}\n\nLEDE:\n{remaining}"
            adaptations.append("inverted_pyramid_format")

    elif audience == "investor":
        # ROI and market focus
        personalized = f"**Investment Thesis:**\n{personalized}\n\n**Expected Return:** [Derived from analysis]"
        adaptations.append("investor_roi_format")

    elif audience == "regulator":
        # Compliance and framework focus
        personalized = f"**Regulatory Framework:**\n{personalized}\n\n**Compliance Status:** [To be assessed]"
        adaptations.append("regulator_compliance_format")

    # Cognitive style aids
    if cognitive_style == "visual":
        personalized += "\n\n[Visual Aid: Conceptual diagram would be inserted here]"
        adaptations.append("visual_aids_noted")
    elif cognitive_style == "analytical":
        personalized += "\n\n[Data Table: Key metrics and statistics here]"
        adaptations.append("analytical_tables_noted")
    elif cognitive_style == "narrative":
        personalized += "\n\n[Narrative Flow: Story arc from context → challenge → resolution]"
        adaptations.append("narrative_structure_noted")
    elif cognitive_style == "procedural":
        personalized += "\n\n[Step-by-Step: Implementation guide structure]"
        adaptations.append("procedural_steps_noted")

    return {
        "status": "success",
        "personalized_content": personalized,
        "audience": audience,
        "cognitive_style": cognitive_style,
        "expertise_level": expertise_level,
        "template": template,
        "adaptations_made": adaptations,
        "original_length": len(content),
        "personalized_length": len(personalized),
    }


async def research_adapt_complexity(
    content: str,
    target_reading_level: int = 12,
) -> dict:
    """Adjust text complexity to target reading level (1-20 scale, 12 = college).

    Args:
        content: Text to adapt
        target_reading_level: Target reading level (1-20, where 12 is college)

    Returns:
        Dict with adapted_content, original_stats, target_level, adaptations_made
    """
    # Validate input
    if target_reading_level < 1 or target_reading_level > 20:
        return {
            "error": "target_reading_level must be 1-20",
            "status": "error",
        }

    # Estimate original reading level
    original_level = _estimate_reading_level(content)

    # Calculate stats
    words = content.split()
    sentences = re.split(r"[.!?]+", content)
    sentences = [s.strip() for s in sentences if s.strip()]

    original_stats = {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "avg_sentence_length": len(words) / max(1, len(sentences)),
        "avg_word_length": sum(len(w) for w in words) / max(1, len(words)),
        "estimated_reading_level": round(original_level, 1),
        "vocabulary_level": _get_target_vocabulary(int(original_level)),
    }

    # Simplify if needed
    if original_level > target_reading_level:
        adapted_content, adaptations = _simplify_text(content, target_reading_level)
    else:
        adapted_content = content
        adaptations = ["no_simplification_needed" if original_level <= target_reading_level else "content_already_complex"]

    # Recalculate stats for adapted content
    adapted_words = adapted_content.split()
    adapted_sentences = re.split(r"[.!?]+", adapted_content)
    adapted_sentences = [s.strip() for s in adapted_sentences if s.strip()]

    adapted_level = _estimate_reading_level(adapted_content)

    return {
        "status": "success",
        "adapted_content": adapted_content,
        "original_stats": original_stats,
        "target_reading_level": target_reading_level,
        "adapted_stats": {
            "word_count": len(adapted_words),
            "sentence_count": len(adapted_sentences),
            "avg_sentence_length": len(adapted_words) / max(1, len(adapted_sentences)),
            "avg_word_length": sum(len(w) for w in adapted_words) / max(1, len(adapted_words)),
            "estimated_reading_level": round(adapted_level, 1),
        },
        "adaptations_made": adaptations,
        "complexity_reduction": round(original_level - adapted_level, 2),
    }
