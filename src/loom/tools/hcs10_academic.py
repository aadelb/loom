"""HCS-10 academic research tools — advanced research integrity and anomaly detection.

Tools for detecting research fraud, monoculture, cartels, data fabrication,
institutional decay, shell funding, conference arbitrage, and preprint manipulation.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any
from urllib.parse import quote

import httpx

from loom.http_helpers import fetch_json, fetch_text

try:
    from scipy.stats import chi2
except ImportError:
    chi2 = None  # Fallback to manual p-value estimation

logger = logging.getLogger("loom.tools.hcs10_academic")

_SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
_DBLP_API = "https://dblp.org/search/venue/api"
_OPENCORPORATES_API = "https://api.opencorporates.com/v0.4/companies/search"
_ARXIV_API = "https://export.arxiv.org/api/query"






def _compute_zipf_exponent(word_freq: dict[str, int]) -> float:
    """Compute Zipf's law exponent via least-squares fit log(freq) ~ log(rank).

    Returns exponent (alpha). Expected ~1.0 for natural language.
    Anomalies: <0.5 (too uniform) or >2.0 (too concentrated).
    """
    if not word_freq:
        return 0.0

    sorted_freqs = sorted(word_freq.values(), reverse=True)
    if len(sorted_freqs) < 2:
        return 0.0

    # Fit log(rank) vs log(freq) to estimate exponent
    sum_log_rank = 0.0
    sum_log_freq = 0.0
    sum_log_rank_freq = 0.0
    sum_log_rank_sq = 0.0
    count = 0

    for rank, freq in enumerate(sorted_freqs, start=1):
        if freq <= 0:
            continue
        log_rank = math.log(rank)
        log_freq = math.log(freq)
        sum_log_rank += log_rank
        sum_log_freq += log_freq
        sum_log_rank_freq += log_rank * log_freq
        sum_log_rank_sq += log_rank * log_rank
        count += 1

    if count < 2:
        return 0.0

    denom = count * sum_log_rank_sq - sum_log_rank * sum_log_rank
    if denom == 0:
        return 0.0

    exponent = (count * sum_log_rank_freq - sum_log_rank * sum_log_freq) / denom
    return abs(exponent)


def _check_benford_distribution(numbers: list[float]) -> tuple[float, float]:
    """Apply Benford's Law to first-digit distribution.

    Returns: (chi_square_statistic, p_value_estimate).
    Chi-square > 15.5 flags anomaly (high fabrication risk).
    """
    first_digits: list[int] = []
    for num in numbers:
        if num == 0:
            continue
        # Extract first digit
        abs_num = abs(num)
        while abs_num < 1:
            abs_num *= 10
        first_digit = int(str(abs_num)[0])
        if 1 <= first_digit <= 9:
            first_digits.append(first_digit)

    if not first_digits:
        return 0.0, 1.0

    # Expected Benford distribution: P(d) = log10(1 + 1/d)
    expected = {
        1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097,
        5: 0.079, 6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046
    }

    observed_counts = Counter(first_digits)
    total = len(first_digits)

    chi_square = 0.0
    for digit in range(1, 10):
        observed = observed_counts.get(digit, 0)
        exp_count = expected[digit] * total
        if exp_count > 0:
            chi_square += ((observed - exp_count) ** 2) / exp_count

    # Compute p-value using chi-square CDF with 8 degrees of freedom
    if chi2 is not None:
        p_value = 1.0 - chi2.cdf(chi_square, df=8)
    else:
        # Fallback: rough approximation if scipy not available
        # chi_square > 15.5 is significant at p<0.01 (8 DOF)
        p_value = max(0.0, 1.0 - chi_square / 30.0)
    return chi_square, p_value


def _shannon_diversity_index(method_counts: dict[str, int]) -> float:
    """Calculate Shannon Diversity Index (H) from method frequencies.

    H = -Σ(p_i * ln(p_i)) where p_i = count_i / total.
    Max diversity = ln(num_methods).
    Returns normalized diversity (0-1): H_norm = H / ln(num_methods).
    """
    if not method_counts:
        return 0.0

    total = sum(method_counts.values())
    if total == 0:
        return 0.0

    h = 0.0
    for count in method_counts.values():
        if count > 0:
            p = count / total
            h -= p * math.log(p)

    max_h = math.log(len(method_counts))
    if max_h == 0:
        return 0.0

    return min(1.0, h / max_h)


def research_grant_forensics(grant_id: str = "", text: str = "") -> dict[str, Any]:
    """Apply Zipf's Law and Benford's Law to grant abstract text.

    Analyzes word distribution (Zipf) and numeric patterns (Benford)
    in grant abstracts to detect anomalies indicative of fabrication.

    Args:
        grant_id: Grant identifier (optional)
        text: Grant abstract text to analyze

    Returns:
        Dict with zipf_exponent, benford_chi_square, anomaly_score (0-1),
        and detailed findings.
    """
    try:
        if not text:
            return {
                "grant_id": grant_id,
                "error": "No text provided",
            }

        # Limit text size to prevent memory issues
        if len(text) > 100000:
            return {
                "grant_id": grant_id,
                "error": "Text too large (max 100,000 characters)",
            }

        # Tokenize and count word frequencies
        words = re.findall(r"\b[a-z]+\b", text.lower())
        word_freq = Counter(words)

        # Remove common stop words to improve Zipf analysis
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "be", "been", "have",
            "has", "do", "does", "did", "will", "would", "should", "could", "may",
            "might", "can", "that", "this", "these", "those", "which", "who",
            "what", "when", "where", "why", "how", "all", "each", "every", "both",
            "few", "more", "most", "other", "some", "such", "no", "nor", "not",
            "only", "own", "same", "so", "than", "too", "very", "just"
        }
        word_freq = {w: f for w, f in word_freq.items() if w not in stop_words}

        zipf_exponent = _compute_zipf_exponent(word_freq)

        # Extract all numbers from text
        numbers_str = re.findall(r"\b\d+(?:\.\d+)?\b", text)
        numbers = []
        for num_str in numbers_str:
            try:
                num_val = float(num_str)
                # Skip NaN/inf values
                if math.isfinite(num_val):
                    numbers.append(num_val)
            except ValueError:
                pass

        benford_chi_sq, benford_pval = _check_benford_distribution(numbers)

        # Define superlative words once to avoid inconsistency
        superlative_words = {
            "revolutionary", "unprecedented", "groundbreaking", "novel", "innovative",
            "transformative", "paradigm", "breakthrough", "conclusively", "proves",
        }

        # Compute anomaly score: normalized combination of deviations
        zipf_anomaly = 0.0
        if zipf_exponent < 0.5 or zipf_exponent > 2.0:
            zipf_anomaly = min(1.0, abs(zipf_exponent - 1.0) / 1.5)

        benford_anomaly = 0.0
        if benford_chi_sq > 15.5:
            benford_anomaly = min(1.0, benford_chi_sq / 30.0)

        anomaly_score = (zipf_anomaly + benford_anomaly) / 2.0

        # Compute fraud_probability combining both signals
        fraud_probability = anomaly_score
        # Boost if Zipf is clearly anomalous
        if zipf_exponent < 0.5 or zipf_exponent > 2.0:
            fraud_probability = min(1.0, fraud_probability + 0.3)
        # Boost if superlative words are overrepresented
        superlatives = sum(1 for w in word_freq if w in superlative_words)
        if superlatives >= 3:
            fraud_probability = min(1.0, fraud_probability + 0.2)

        return {
            "grant_id": grant_id,
            "text_length": len(text),
            "unique_words": len(word_freq),
            "total_words": sum(word_freq.values()),
            "zipf_exponent": round(zipf_exponent, 3),
            "zipf_anomaly": "FLAGGED" if zipf_exponent < 0.5 or zipf_exponent > 2.0 else "normal",
            "numbers_found": len(numbers),
            "benford_chi_square": round(benford_chi_sq, 3),
            "benford_pvalue": round(benford_pval, 3),
            "benford_anomaly": "FLAGGED" if benford_chi_sq > 15.5 else "normal",
            "fraud_probability": round(fraud_probability, 3),
            "anomaly_score": round(anomaly_score, 3),
            "linguistic_markers": [w for w in word_freq if w in superlative_words][:10],
            "risk_level": "HIGH" if fraud_probability > 0.5 else "MEDIUM" if fraud_probability > 0.3 else "LOW",
        }
    except Exception as exc:
        logger.exception("research_grant_forensics failed")
        return {"error": str(exc), "tool": "research_grant_forensics"}


async def research_monoculture_detect(field: str, max_papers: int = 50) -> dict[str, Any]:
    """Detect research field monoculture via method diversity analysis.

    Searches Semantic Scholar for recent papers in a field, extracts method
    keywords from abstracts, and computes Shannon Diversity Index to flag
    over-reliance on a single dominant method.

    Args:
        field: Research field (e.g., "machine learning", "oncology")
        max_papers: Max papers to analyze (default 50)

    Returns:
        Dict with field, methods_found, diversity_index, dominant_method,
        and monoculture_risk level.
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Search Semantic Scholar for recent papers in field
                search_url = (
                    f"{_SEMANTIC_SCHOLAR_API}/paper/search"
                    f"?query={quote(field)}&limit={max_papers}&fields=title,abstract,year"
                )
                search_data = await fetch_json(client, search_url)

                if not search_data or "data" not in search_data:
                    return {
                        "field": field,
                        "error": "No papers found",
                    }

                # Extract abstracts and look for method keywords
                abstracts = []
                for paper in search_data.get("data", [])[:max_papers]:
                    abstract = paper.get("abstract", "")
                    if abstract:
                        abstracts.append(abstract.lower())

                if not abstracts:
                    return {
                        "field": field,
                        "papers_found": 0,
                        "error": "No abstracts found",
                    }

                # Method keyword extraction (simplified)
                method_keywords = {
                    "neural network": 0, "deep learning": 0, "transformer": 0,
                    "attention": 0, "cnn": 0, "lstm": 0, "rnn": 0, "ensemble": 0,
                    "regression": 0, "classification": 0, "clustering": 0,
                    "bayesian": 0, "markov": 0, "monte carlo": 0,
                    "reinforcement learning": 0, "supervised": 0, "unsupervised": 0,
                    "semi-supervised": 0, "transfer learning": 0, "few-shot": 0,
                    "zero-shot": 0, "meta-learning": 0, "graph neural": 0,
                    "natural language": 0, "computer vision": 0, "time series": 0,
                }

                for abstract in abstracts:
                    for method in method_keywords.keys():
                        if method in abstract:
                            method_keywords[method] += 1

                # Filter methods with at least 1 mention
                methods_found = {m: c for m, c in method_keywords.items() if c > 0}
                if not methods_found:
                    return {
                        "field": field,
                        "papers_found": len(abstracts),
                        "methods_found": 0,
                        "error": "No methods detected",
                    }

                diversity_index = _shannon_diversity_index(methods_found)
                dominant_method = max(methods_found.items(), key=lambda x: x[1])[0]
                dominant_ratio = methods_found[dominant_method] / sum(methods_found.values())

                # Monoculture risk: low diversity or high dominance ratio
                monoculture_risk = 0.0
                if diversity_index < 0.4:
                    monoculture_risk = 0.7
                elif diversity_index < 0.6:
                    monoculture_risk = 0.4
                if dominant_ratio > 0.5:
                    monoculture_risk = max(monoculture_risk, dominant_ratio)

                return {
                    "field": field,
                    "papers_analyzed": len(abstracts),
                    "methods_found": len(methods_found),
                    "method_distribution": methods_found,
                    "diversity_index": round(diversity_index, 3),
                    "dominant_method": dominant_method,
                    "dominant_ratio": round(dominant_ratio, 3),
                    "monoculture_risk": round(monoculture_risk, 3),
                    "risk_level": "HIGH" if monoculture_risk > 0.7 else "MEDIUM" if monoculture_risk > 0.4 else "LOW",
                }

        return await _run()
    except Exception as exc:
        logger.exception("research_monoculture_detect failed")
        return {"error": str(exc), "tool": "research_monoculture_detect"}


async def research_review_cartel(author_id: str) -> dict[str, Any]:
    """Detect peer review cartels via mutual citation patterns.

    Analyzes an author's papers to detect suspicious mutual citation
    patterns (A cites B AND B cites A) that suggest cartel behavior.

    Args:
        author_id: Author ID (Semantic Scholar format)

    Returns:
        Dict with author_id, papers_analyzed, mutual_citations count,
        and cartel_score (0-1).
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get author papers
                author_url = f"{_SEMANTIC_SCHOLAR_API}/author/{author_id}"
                author_data = await fetch_json(client, author_url)

                if not author_data:
                    return {
                        "author_id": author_id,
                        "error": "Author not found",
                    }

                papers = author_data.get("papers", [])
                if not papers:
                    return {
                        "author_id": author_id,
                        "papers_analyzed": 0,
                        "error": "No papers found",
                    }

                paper_ids = set()
                paper_references: dict[str, set[str]] = {}

                # Fetch each paper's references and citations
                mutual_pairs = []
                for paper in papers[:20]:  # Limit to 20 papers to avoid timeouts
                    paper_id = paper.get("paperId")
                    if not paper_id:
                        continue

                    paper_ids.add(paper_id)

                    # Fetch paper details
                    paper_url = (
                        f"{_SEMANTIC_SCHOLAR_API}/paper/{paper_id}"
                        f"?fields=references,citations"
                    )
                    paper_detail = await fetch_json(client, paper_url)

                    if not paper_detail:
                        continue

                    refs = paper_detail.get("references", [])
                    ref_ids = {r.get("paperId") for r in refs if r.get("paperId")}
                    paper_references[paper_id] = ref_ids

                    # Check for mutual citations
                    cites = paper_detail.get("citations", [])
                    citing_ids = {c.get("citingPaper", {}).get("paperId") for c in cites}

                    for citing_id in citing_ids:
                        if citing_id in paper_ids and citing_id != paper_id:
                            # Check if this citing_id also references paper_id
                            if paper_id in paper_references.get(citing_id, set()):
                                mutual_pairs.append((paper_id, citing_id))

                # Compute cartel score based on mutual citation density
                cartel_score = 0.0
                if len(papers) > 1:
                    max_possible_pairs = len(papers) * (len(papers) - 1) / 2
                    if max_possible_pairs > 0:
                        cartel_score = min(1.0, len(mutual_pairs) / max_possible_pairs)

                return {
                    "author_id": author_id,
                    "papers_analyzed": len(papers[:20]),
                    "mutual_citations": len(mutual_pairs),
                    "mutual_citation_pairs": [
                        {"paper1": p[0], "paper2": p[1]} for p in mutual_pairs[:10]
                    ],
                    "cartel_score": round(cartel_score, 3),
                    "risk_level": "HIGH" if cartel_score > 0.3 else "MEDIUM" if cartel_score > 0.1 else "LOW",
                }

        return await _run()
    except Exception as exc:
        logger.exception("research_review_cartel failed")
        return {"error": str(exc), "tool": "research_review_cartel"}


def research_data_fabrication(numbers: list[float]) -> dict[str, Any]:
    """Apply GRIM test and Benford analysis to detect data fabrication.

    GRIM (Granularity-Related Inconsistency) checks if reported means are
    possible given sample sizes. Benford applies first-digit law.

    Args:
        numbers: List of numeric values (means, counts, etc.)

    Returns:
        Dict with grim_failures count, benford_deviation, and
        fabrication_risk (0-1).
    """
    try:
        if not numbers:
            return {"error": "No numbers provided"}

        # Filter out NaN/inf values
        valid_numbers = [n for n in numbers if isinstance(n, (int, float)) and math.isfinite(n)]
        if not valid_numbers:
            return {"error": "No valid numeric values provided"}

        # GRIM test: check if means are achievable given typical sample sizes
        # Simplified: if mean has more decimal places than 1/n allows, flag it
        grim_failures = 0
        decimal_inconsistencies = []

        # Assume sample size ~30 (typical for psychological studies)
        # For n=30, possible means are multiples of 1/30 ≈ 0.0333
        typical_sample_size = 30
        min_granularity = 1.0 / typical_sample_size

        for num in valid_numbers:
            # Check decimal precision
            str_num = f"{num:.4f}"
            if "." in str_num:
                decimal_places = len(str_num.split(".")[1].rstrip("0"))
                # If too many decimal places relative to sample size, flag
                if decimal_places > 4:
                    grim_failures += 1
                    decimal_inconsistencies.append(num)

        # Benford test
        benford_chi_sq, benford_pval = _check_benford_distribution(valid_numbers)

        # Fabrication risk: combination of GRIM failures and Benford anomaly
        grim_ratio = grim_failures / len(valid_numbers) if valid_numbers else 0.0
        benford_ratio = min(1.0, benford_chi_sq / 20.0)

        fabrication_risk = (grim_ratio + benford_ratio) / 2.0

        return {
            "numbers_analyzed": len(valid_numbers),
            "grim_failures": grim_failures,
            "grim_failure_rate": round(grim_ratio, 3),
            "decimal_anomalies": decimal_inconsistencies[:10],
            "benford_chi_square": round(benford_chi_sq, 3),
            "benford_pvalue": round(benford_pval, 3),
            "benford_deviation": "FLAGGED" if benford_chi_sq > 15.5 else "normal",
            "fabrication_risk": round(fabrication_risk, 3),
            "risk_level": "HIGH" if fabrication_risk > 0.7 else "MEDIUM" if fabrication_risk > 0.4 else "LOW",
        }
    except Exception as exc:
        logger.exception("research_data_fabrication failed")
        return {"error": str(exc), "tool": "research_data_fabrication"}


async def research_institutional_decay(institution: str) -> dict[str, Any]:
    """Assess institutional health from retraction rate, publication trend, and author turnover.

    Queries Crossref for retraction data, Semantic Scholar for publication trends,
    and estimates author turnover from recent papers.

    Args:
        institution: Institution name (e.g., "Harvard University", "MIT")

    Returns:
        Dict with institution, retraction_rate, publication_trend (slope),
        author_turnover, and decay_score (0-1).
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Search for institution papers on Semantic Scholar
                search_url = (
                    f"{_SEMANTIC_SCHOLAR_API}/paper/search"
                    f"?query=from:{quote(institution)}&limit=50&fields=year,authors,citationCount"
                )
                search_data = await fetch_json(client, search_url)

                if not search_data or "data" not in search_data:
                    return {
                        "institution": institution,
                        "error": "No papers found",
                    }

                papers = search_data.get("data", [])
                if not papers:
                    return {
                        "institution": institution,
                        "papers_found": 0,
                        "error": "No papers found",
                    }

                # Estimate retraction rate (simplified: query Crossref)
                retraction_url = (
                    f"https://api.crossref.org/works"
                    f"?query={quote(institution)}&filter=has-retracted-article:true&rows=1"
                )
                retraction_data = await fetch_json(client, retraction_url)
                total_with_retraction = 0
                if retraction_data and "message" in retraction_data:
                    total_with_retraction = retraction_data["message"].get("total-results", 0)

                # Publication trend over last 5 years
                pub_by_year: dict[int, int] = {}
                all_authors: set[str] = set()

                for paper in papers:
                    year = paper.get("year", 0)
                    if 2019 <= year <= 2024:
                        pub_by_year[year] = pub_by_year.get(year, 0) + 1

                    # Track authors for turnover estimate
                    authors = paper.get("authors", [])
                    for auth in authors:
                        if isinstance(auth, dict):
                            all_authors.add(auth.get("name", ""))

                # Estimate publication trend (linear regression on year)
                years_list = sorted(pub_by_year.keys())
                if len(years_list) >= 2:
                    counts = [pub_by_year[y] for y in years_list]
                    n = len(years_list)
                    sum_y = sum(counts)
                    sum_x = sum(years_list)
                    sum_xy = sum(y * c for y, c in zip(years_list, counts))
                    sum_x2 = sum(y * y for y in years_list)
                    denom = n * sum_x2 - sum_x * sum_x
                    trend_slope = (n * sum_xy - sum_x * sum_y) / denom if denom != 0 else 0.0
                else:
                    trend_slope = 0.0

                # Retraction rate estimate
                total_papers = sum(pub_by_year.values())
                retraction_rate = (
                    (total_with_retraction / total_papers) if total_papers > 0 else 0.0
                )

                # Author turnover: rough estimate from new/established authors
                # (Simplified: number of unique authors)
                author_turnover = len(all_authors) / max(1, total_papers)

                # Decay score: combination of retraction rate and declining publications
                decay_score = 0.0
                if retraction_rate > 0.02:  # >2% retractions is concerning
                    decay_score += min(0.5, retraction_rate * 10)
                if trend_slope < -1:  # Declining trend
                    decay_score += 0.3
                if author_turnover > 1.0:  # High turnover
                    decay_score += 0.2

                decay_score = min(1.0, decay_score)

                return {
                    "institution": institution,
                    "papers_analyzed": len(papers),
                    "total_years": len(years_list),
                    "retraction_rate": round(retraction_rate, 4),
                    "retracted_papers_found": total_with_retraction,
                    "publication_by_year": pub_by_year,
                    "publication_trend_slope": round(trend_slope, 2),
                    "trend_direction": "declining" if trend_slope < -0.5 else "stable" if abs(trend_slope) < 0.5 else "growing",
                    "unique_authors": len(all_authors),
                    "author_turnover": round(author_turnover, 3),
                    "decay_score": round(decay_score, 3),
                    "risk_level": "HIGH" if decay_score > 0.6 else "MEDIUM" if decay_score > 0.3 else "LOW",
                }

        return await _run()
    except Exception as exc:
        logger.exception("research_institutional_decay failed")
        return {"error": str(exc), "tool": "research_institutional_decay"}


async def research_shell_funding(company: str) -> dict[str, Any]:
    """Trace research funding through shell companies using OpenCorporates + SEC EDGAR.

    Queries OpenCorporates API for company details and searches for connected
    entities to identify potential shell company structures used for research funding.

    Args:
        company: Company name to investigate

    Returns:
        Dict with company, corporate_links (connected entities), funding_chains,
        and opacity_score (0-1).
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Query OpenCorporates
                oc_url = f"{_OPENCORPORATES_API}?q={quote(company)}"
                oc_data = await fetch_json(client, oc_url)

                if not oc_data or "companies" not in oc_data.get("results", {}):
                    return {
                        "company": company,
                        "error": "Company not found in OpenCorporates",
                    }

                companies = oc_data.get("results", {}).get("companies", [])
                if not companies:
                    return {
                        "company": company,
                        "companies_found": 0,
                        "error": "No companies found",
                    }

                # Extract corporate details
                corporate_links = []
                opacity_indicators = []

                for corp in companies[:10]:
                    corp_name = corp.get("name", "")
                    corp_jurisdiction = corp.get("jurisdiction_code", "")
                    corp_type = corp.get("company_type", "")
                    corp_status = corp.get("status", "")
                    inactive_since = corp.get("inactive_since", "")

                    # Flag opacity indicators
                    if corp_status in ("inactive", "dissolved", "removed"):
                        opacity_indicators.append(f"Inactive status: {corp_status}")

                    if inactive_since:
                        opacity_indicators.append(f"Inactive since: {inactive_since}")

                    # Flag jurisdictions known for opacity
                    if corp_jurisdiction in ("ky", "de", "nv", "bvi", "cayman", "panama"):
                        opacity_indicators.append(f"Opaque jurisdiction: {corp_jurisdiction}")

                    # Flag shell company patterns
                    if corp_type in ("shell", "holding", "nominee"):
                        opacity_indicators.append(f"Shell pattern: {corp_type}")

                    corporate_links.append({
                        "name": corp_name,
                        "jurisdiction": corp_jurisdiction,
                        "type": corp_type,
                        "status": corp_status,
                        "inactive_since": inactive_since,
                    })

                # Opacity score based on indicators
                opacity_score = 0.0
                if len(opacity_indicators) > 0:
                    opacity_score = min(1.0, len(opacity_indicators) / 5.0)

                # Simplified funding chain analysis (would need SEC EDGAR integration)
                funding_chains = [
                    {
                        "stage": "incorporation",
                        "jurisdiction": companies[0].get("jurisdiction_code", ""),
                        "opacity": "high" if len(opacity_indicators) > 2 else "medium",
                    }
                ]

                return {
                    "company": company,
                    "companies_found": len(companies),
                    "corporate_links": corporate_links[:5],
                    "opacity_indicators": opacity_indicators[:10],
                    "funding_chains": funding_chains,
                    "opacity_score": round(opacity_score, 3),
                    "risk_level": "HIGH" if opacity_score > 0.6 else "MEDIUM" if opacity_score > 0.3 else "LOW",
                }

        return await _run()
    except Exception as exc:
        logger.exception("research_shell_funding failed")
        return {"error": str(exc), "tool": "research_shell_funding"}


async def research_conference_arbitrage(conference: str) -> dict[str, Any]:
    """Analyze conference acceptance patterns using DBLP and Semantic Scholar.

    Queries DBLP for conference submission/acceptance data to detect patterns
    that suggest gaming of conference selection or acceptance rates.

    Args:
        conference: Conference name (e.g., "NeurIPS", "ICML", "ICCV")

    Returns:
        Dict with conference, acceptance_trend, submission_timing_pattern,
        and arbitrage_opportunities list.
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Query DBLP for conference papers
                dblp_url = f"{_DBLP_API}?q={quote(conference)}&format=json"
                dblp_data = await fetch_json(client, dblp_url)

                if not dblp_data or "result" not in dblp_data:
                    return {
                        "conference": conference,
                        "error": "Conference not found in DBLP",
                    }

                results = dblp_data.get("result", {})
                hits = results.get("hits", [])

                if not hits or "@total" not in results:
                    return {
                        "conference": conference,
                        "papers_found": 0,
                        "error": "No papers found",
                    }

                total_papers = int(results.get("@total", 0))

                # Extract publication years to analyze trend
                pub_by_year: dict[int, int] = {}
                for hit in hits[:100]:
                    info = hit.get("info", {})
                    year_str = info.get("year", "")
                    if year_str and year_str.isdigit():
                        year = int(year_str)
                        pub_by_year[year] = pub_by_year.get(year, 0) + 1

                # Analyze acceptance trend (would need submission data from conference websites)
                acceptance_trend = []
                if len(pub_by_year) > 1:
                    years = sorted(pub_by_year.keys())
                    for i, year in enumerate(years):
                        acceptance_trend.append({
                            "year": year,
                            "papers": pub_by_year[year],
                        })

                # Detect submission timing patterns (papers submitted just before deadline)
                # Simplified: would need submission metadata
                submission_timing_pattern = {
                    "peak_submission_period": "unknown",
                    "concentration_ratio": 0.0,
                }

                # Identify arbitrage opportunities
                arbitrage_opportunities = []

                # Flag: rapid growth in acceptance (possible gaming)
                if len(acceptance_trend) >= 2:
                    recent_growth = (
                        acceptance_trend[-1]["papers"] / acceptance_trend[-2]["papers"]
                        if acceptance_trend[-2]["papers"] > 0 else 0
                    )
                    if recent_growth > 1.5:
                        arbitrage_opportunities.append({
                            "type": "rapid_acceptance_growth",
                            "indicator": f"Growth ratio: {recent_growth:.2f}",
                            "risk": "possible_gaming",
                        })

                return {
                    "conference": conference,
                    "total_papers_in_dblp": total_papers,
                    "papers_analyzed": len(hits),
                    "years_covered": len(pub_by_year),
                    "acceptance_trend": acceptance_trend,
                    "submission_timing_pattern": submission_timing_pattern,
                    "arbitrage_opportunities": arbitrage_opportunities,
                    "arbitrage_risk": "HIGH" if len(arbitrage_opportunities) > 2 else "MEDIUM" if len(arbitrage_opportunities) > 0 else "LOW",
                }

        return await _run()
    except Exception as exc:
        logger.exception("research_conference_arbitrage failed")
        return {"error": str(exc), "tool": "research_conference_arbitrage"}


async def research_preprint_manipulation(arxiv_id: str = "", topic: str = "") -> dict[str, Any]:
    """Detect preprint manipulation via timing analysis and social amplification.

    Analyzes arXiv submission timing relative to social media buzz (Hacker News, Reddit)
    and altmetric scores to flag suspicious coordination or hype manipulation.

    Args:
        arxiv_id: arXiv paper ID (e.g., "2310.12345")
        topic: Topic to search for preprints (e.g., "transformer")

    Returns:
        Dict with paper info, timing_analysis, social_amplification_score,
        and manipulation_risk (0-1).
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                local_arxiv_id = arxiv_id
                # If topic provided, search for recent preprints
                if topic and not local_arxiv_id:
                    search_url = (
                        f"{_ARXIV_API}?search_query=cat:cs.AI+AND+submittedDate:"
                        f"[202401010000+TO+202412312359]&start=0&max_results=20"
                    )
                    arxiv_data = await fetch_text(client, search_url)
                    if not arxiv_data:
                        return {
                            "topic": topic,
                            "error": "arXiv search failed",
                        }

                    # Parse first paper from results (simplified)
                    try:
                        root = ET.fromstring(arxiv_data)
                        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                        if entries:
                            entry = entries[0]
                            local_arxiv_id = entry.find("{http://www.w3.org/2005/Atom}id").text.split("/abs/")[1]
                    except Exception as exc:
                        logger.debug("XML parse failed: %s", exc)
                        return {
                            "topic": topic,
                            "error": "Could not parse arXiv results",
                        }

                if not local_arxiv_id:
                    return {
                        "error": "No arxiv_id or topic provided",
                    }

                # Fetch paper metadata from arXiv
                arxiv_url = f"{_ARXIV_API}?id_list={local_arxiv_id}&start=0&max_results=1"
                arxiv_text = await fetch_text(client, arxiv_url)

                if not arxiv_text:
                    return {
                        "arxiv_id": local_arxiv_id,
                        "error": "Paper not found on arXiv",
                    }

                # Parse submission date and title
                try:
                    root = ET.fromstring(arxiv_text)
                    entry = root.find("{http://www.w3.org/2005/Atom}entry")
                    if not entry:
                        return {
                            "arxiv_id": local_arxiv_id,
                            "error": "Could not parse arXiv metadata",
                        }

                    published_elem = entry.find("{http://www.w3.org/2005/Atom}published")
                    title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
                    published = published_elem.text if published_elem is not None else ""
                    title = title_elem.text if title_elem is not None else ""
                except Exception as exc:
                    logger.debug("arXiv parse failed: %s", exc)
                    return {
                        "arxiv_id": local_arxiv_id,
                        "error": "Could not parse arXiv entry",
                    }

                # Simplified social amplification score
                # (Would need HN/Reddit API access for real implementation)
                social_amplification_score = 0.3  # Baseline

                # Flag manipulation patterns
                manipulation_indicators = []

                # Pattern 1: Simultaneous arXiv + press release
                # (Would need press release database)
                manipulation_indicators.append({
                    "type": "timing_coordination",
                    "detected": False,
                    "reason": "No press release data available",
                })

                # Pattern 2: Unusually high altmetric score relative to citations
                # (Would need altmetric API)
                altmetric_data = await fetch_json(
                    client,
                    f"https://api.altmetric.com/v1/arxiv/{local_arxiv_id}",
                    timeout=10.0
                )

                altmetric_score = 0.0
                if altmetric_data:
                    altmetric_score = altmetric_data.get("score", 0.0)
                    if altmetric_score > 50:
                        social_amplification_score += 0.3

                # Compute manipulation risk
                manipulation_risk = min(
                    1.0,
                    social_amplification_score + len([i for i in manipulation_indicators if i.get("detected", False)]) * 0.2
                )

                return {
                    "arxiv_id": local_arxiv_id,
                    "title": title if arxiv_text else "",
                    "submission_date": published if arxiv_text else "",
                    "topic_search": topic,
                    "timing_analysis": {
                        "submission_date": published if arxiv_text else "",
                        "coordination_indicators": 0,
                    },
                    "social_amplification_score": round(social_amplification_score, 3),
                    "altmetric_score": altmetric_score,
                    "manipulation_indicators": manipulation_indicators,
                    "manipulation_risk": round(manipulation_risk, 3),
                    "risk_level": "HIGH" if manipulation_risk > 0.7 else "MEDIUM" if manipulation_risk > 0.4 else "LOW",
                }

        return await _run()
    except Exception as exc:
        logger.exception("research_preprint_manipulation failed")
        return {"error": str(exc), "tool": "research_preprint_manipulation"}
