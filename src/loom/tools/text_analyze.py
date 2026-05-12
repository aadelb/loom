"""research_text_analyze — NLP text analysis using NLTK.

Provides entity extraction, keyword extraction, readability metrics,
and language statistics using NLTK.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import nltk
    from nltk import pos_tag
    from nltk.chunk import ne_chunk
    from nltk.corpus import stopwords
    from nltk.tokenize import sent_tokenize, word_tokenize

    _HAS_NLTK = True
except ImportError:
    _HAS_NLTK = False

logger = logging.getLogger("loom.tools.text_analyze")

# Constraints
MIN_TEXT_CHARS = 10
MAX_TEXT_CHARS = 100000
READABILITY_PRECISION = 2


def _ensure_nltk_data() -> None:
    """Download required NLTK data files if missing."""
    if not _HAS_NLTK:
        return

    required_datasets = ["punkt_tab", "averaged_perceptron_tagger", "maxent_ne_chunker", "words", "stopwords"]
    for dataset in required_datasets:
        try:
            nltk.data.find(f"tokenizers/{dataset}")
        except LookupError:
            try:
                nltk.download(dataset, quiet=True)
            except Exception as e:
                logger.warning("nltk_download_failed dataset=%s error=%s", dataset, e)


def _count_syllables(word: str) -> int:
    """Estimate syllable count using vowel group heuristic.

    Args:
        word: word to count syllables in

    Returns:
        estimated syllable count (minimum 1)
    """
    word = word.lower()
    syllable_count = 0
    vowels = "aeiouy"
    previous_was_vowel = False

    for char in word:
        is_vowel = char in vowels
        if is_vowel and not previous_was_vowel:
            syllable_count += 1
        previous_was_vowel = is_vowel

    # Adjust for silent e (except for -ce words like "science")
    if word.endswith("e") and len(word) > 2 and not word.endswith("ce"):
        syllable_count -= 1

    # Ensure at least 1 syllable
    return max(1, syllable_count)


def _extract_entities(text: str) -> list[dict[str, Any]]:
    """Extract named entities using NLTK NER.

    Args:
        text: input text

    Returns:
        list of entity dicts with text, type, count
    """
    if not _HAS_NLTK:
        return []

    _ensure_nltk_data()

    try:
        # Tokenize into sentences
        sentences = sent_tokenize(text[:5000])  # Limit to first 5K chars for performance

        entity_counts: dict[str, dict[str, int]] = {}  # {entity_text: {type: count}}

        for sentence in sentences:
            try:
                # Tokenize and POS tag
                tokens = word_tokenize(sentence)
                pos_tags = pos_tag(tokens)

                # Named entity recognition
                ne_tree = ne_chunk(pos_tags)

                # Extract entities from tree
                for subtree in ne_tree:
                    if hasattr(subtree, "label"):  # Is a named entity chunk
                        entity_text = " ".join(word for word, tag in subtree.leaves())
                        entity_type = subtree.label()

                        # Track by type
                        if entity_text not in entity_counts:
                            entity_counts[entity_text] = {"type": entity_type, "count": 0}

                        entity_counts[entity_text]["count"] += 1

            except Exception as e:
                logger.warning("entity_extraction_failed sentence=%s error=%s", sentence[:50], e)
                continue

        # Format output
        result = []
        seen = set()
        for entity_text, info in entity_counts.items():
            if isinstance(info, dict) and "type" in info and entity_text not in seen:
                result.append({
                    "text": entity_text,
                    "type": info["type"],
                    "count": info["count"],
                })
                seen.add(entity_text)

        return sorted(result, key=lambda x: x["count"], reverse=True)[:50]

    except Exception as e:
        logger.error("entity_extraction_error: %s", e)
        return []


def _extract_keywords(text: str) -> list[dict[str, Any]]:
    """Extract keywords using TF-IDF-like frequency analysis.

    Args:
        text: input text

    Returns:
        list of top-20 keywords with frequency and TF-IDF score
    """
    if not _HAS_NLTK:
        return []

    _ensure_nltk_data()

    try:
        # Tokenize
        tokens = word_tokenize(text.lower())

        # Get stopwords
        try:
            stop_words = set(stopwords.words("english"))
        except Exception:
            stop_words = set()

        # Filter tokens
        filtered_tokens = [
            t
            for t in tokens
            if t.isalnum() and t not in stop_words and len(t) > 2
        ]

        # Compute term frequency
        term_freq: dict[str, int] = {}
        for token in filtered_tokens:
            term_freq[token] = term_freq.get(token, 0) + 1

        # Simple TF-IDF approximation (TF only, no IDF)
        total_terms = len(filtered_tokens)
        keywords = [
            {
                "term": term,
                "frequency": count,
                "tfidf": round(count / total_terms if total_terms > 0 else 0, 4),
            }
            for term, count in term_freq.items()
        ]

        return sorted(keywords, key=lambda x: x["frequency"], reverse=True)[:20]

    except Exception as e:
        logger.error("keyword_extraction_error: %s", e)
        return []


def _compute_readability(text: str) -> dict[str, Any]:
    """Compute readability metrics.

    Args:
        text: input text

    Returns:
        dict with Flesch-Kincaid, ARI, and syllable metrics
    """
    try:
        # Tokenize
        sentences = sent_tokenize(text)
        words = word_tokenize(text.lower())
        words_filtered = [w for w in words if w.isalnum()]

        if not sentences or not words_filtered:
            return {
                "flesch_kincaid_grade": 0,
                "ari": 0,
                "avg_syllables": 0,
                "vocabulary_level": "unknown",
            }

        # Count syllables
        total_syllables = sum(_count_syllables(w) for w in words_filtered)
        avg_syllables = round(total_syllables / len(words_filtered), READABILITY_PRECISION)

        # Flesch-Kincaid Grade Level
        # 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
        fk_grade = round(
            0.39 * (len(words_filtered) / len(sentences))
            + 11.8 * (total_syllables / len(words_filtered))
            - 15.59,
            READABILITY_PRECISION,
        )
        fk_grade = max(0, fk_grade)  # Ensure non-negative

        # Automated Readability Index (ARI)
        # 4.71 * (chars / words) + 0.5 * (words / sentences) - 21.43
        total_chars = sum(len(w) for w in words_filtered)
        ari = round(
            4.71 * (total_chars / len(words_filtered))
            + 0.5 * (len(words_filtered) / len(sentences))
            - 21.43,
            READABILITY_PRECISION,
        )
        ari = max(0, ari)

        # Vocabulary level estimate based on avg word length
        avg_word_length = total_chars / len(words_filtered) if words_filtered else 0
        if avg_word_length < 4:
            vocab_level = "elementary"
        elif avg_word_length < 5:
            vocab_level = "middle"
        elif avg_word_length < 6:
            vocab_level = "high"
        else:
            vocab_level = "advanced"

        return {
            "flesch_kincaid_grade": fk_grade,
            "ari": ari,
            "avg_syllables": avg_syllables,
            "vocabulary_level": vocab_level,
        }

    except Exception as e:
        logger.error("readability_computation_error: %s", e)
        return {
            "flesch_kincaid_grade": 0,
            "ari": 0,
            "avg_syllables": 0,
            "vocabulary_level": "unknown",
        }


def _compute_language_stats(text: str) -> dict[str, Any]:
    """Compute language statistics.

    Args:
        text: input text

    Returns:
        dict with word count, sentence count, lexical density, etc.
    """
    try:
        # Tokenize
        sentences = sent_tokenize(text)
        words = word_tokenize(text.lower())
        words_filtered = [w for w in words if w.isalnum()]

        if not sentences or not words_filtered:
            return {
                "words": 0,
                "sentences": 0,
                "paragraphs": 0,
                "avg_words_per_sentence": 0,
                "lexical_density": 0,
                "unique_words": 0,
                "most_common_words": [],
            }

        # Count paragraphs (split by newlines)
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        # Compute lexical density (content words / total words)
        # Content words: nouns, verbs, adjectives, adverbs (simplified as non-stopwords)
        if _HAS_NLTK:
            _ensure_nltk_data()
            try:
                stop_words = set(stopwords.words("english"))
            except Exception:
                stop_words = set()
        else:
            stop_words = set()

        content_words = [w for w in words_filtered if w not in stop_words and len(w) > 2]
        lexical_density = round(
            len(content_words) / len(words_filtered) if words_filtered else 0,
            READABILITY_PRECISION,
        )

        # Count word frequencies
        word_freq: dict[str, int] = {}
        for word in words_filtered:
            if word not in stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1

        most_common = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "words": len(words_filtered),
            "sentences": len(sentences),
            "paragraphs": len(paragraphs),
            "avg_words_per_sentence": round(len(words_filtered) / len(sentences), READABILITY_PRECISION),
            "lexical_density": lexical_density,
            "unique_words": len(set(words_filtered)),
            "most_common_words": [{"word": w, "count": c} for w, c in most_common],
        }

    except Exception as e:
        logger.error("language_stats_error: %s", e)
        return {
            "words": 0,
            "sentences": 0,
            "paragraphs": 0,
            "avg_words_per_sentence": 0,
            "lexical_density": 0,
            "unique_words": 0,
            "most_common_words": [],
        }


def research_text_analyze(
    text: str,
    analyses: list[str] | None = None,
) -> dict[str, Any]:
    """Perform NLP text analysis using NLTK.

    Args:
        text: input text to analyze (10-100,000 chars)
        analyses: list of analysis types to run
                 (default: all) - options:
                 ["entities", "keywords", "readability", "language_stats"]

    Returns:
        Dict with analysis results and metadata:
        - entities: [{"text": str, "type": str, "count": int}]
        - keywords: [{"term": str, "frequency": int, "tfidf": float}]
        - readability: {flesch_kincaid_grade, ari, avg_syllables, vocabulary_level}
        - language_stats: {words, sentences, paragraphs, avg_words_per_sentence, ...}
        - word_count: total word count
        - error: error message if any
    """
    # Validate NLTK availability
    if not _HAS_NLTK:
        error_msg = "NLTK not installed. Run: pip install nltk"
        logger.error("nltk_not_available")
        return {
            "error": error_msg,
            "word_count": 0,
        }

    # Validate input
    if not text or len(text) < MIN_TEXT_CHARS:
        error_msg = f"text must be at least {MIN_TEXT_CHARS} characters"
        logger.warning("text_analyze_invalid_input length=%d", len(text))
        return {
            "error": error_msg,
            "word_count": 0,
        }

    if len(text) > MAX_TEXT_CHARS:
        error_msg = f"text exceeds {MAX_TEXT_CHARS} character limit"
        logger.warning("text_analyze_text_too_long length=%d", len(text))
        return {
            "error": error_msg,
            "word_count": 0,
        }

    # Default to all analyses
    if analyses is None:
        analyses = ["entities", "keywords", "readability", "language_stats"]

    # Validate analysis types
    valid_analyses = {"entities", "keywords", "readability", "language_stats"}
    analyses = [a for a in analyses if a in valid_analyses]

    result: dict[str, Any] = {}
    
    try:
        result["word_count"] = len(word_tokenize(text)) if _HAS_NLTK else 0
    except Exception as e:
        error_msg = f"tokenization failed: {e!s}"
        logger.error("text_analyze_tokenize_error: %s", e)
        return {
            "error": error_msg,
            "word_count": 0,
        }

    try:
        # Run requested analyses
        if "entities" in analyses:
            result["entities"] = _extract_entities(text)

        if "keywords" in analyses:
            result["keywords"] = _extract_keywords(text)

        if "readability" in analyses:
            result["readability"] = _compute_readability(text)

        if "language_stats" in analyses:
            result["language_stats"] = _compute_language_stats(text)

        logger.info("text_analyze_completed analyses=%s word_count=%d", analyses, result["word_count"])
        return result

    except Exception as e:
        error_msg = f"text analysis failed: {e!s}"
        logger.error("text_analyze_error: %s", e)
        return {
            "error": error_msg,
            "word_count": result.get("word_count", 0),
        }
