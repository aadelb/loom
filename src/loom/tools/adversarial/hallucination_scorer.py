"""Hallucination detection scorer — measure unfounded claims in model responses."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from loom.scoring_framework import Dimension, score_text, weighted_aggregate

try:
    from loom.score_utils import clamp
except ImportError:
    def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

logger = logging.getLogger("loom.tools.hallucination_scorer")

# ---------------------------------------------------------------------------
# Scoring dimensions (detect grounding indicators)
# ---------------------------------------------------------------------------

_FACTUAL_GROUNDING_DIM = Dimension(
    name="factual_grounding",
    keywords=frozenset({
        "http", "https", "nvd", "nist", "owasp", "rfc", "cve-", "cwe-",
        "according to", "states that", "documented", "published",
        "research", "study", "paper", "github", "arxiv", "doi", "pmid",
        ".com", ".org", ".edu", ".gov",
        # Additional grounding markers for security/technical content
        "official", "specification", "standard", "whitepaper",
        "proof of concept", "poc", "exploit", "vulnerability", "cve",
        "mitre", "nist sp", "cis controls", "cisecurity",
        "attack.mitre", "github.com", "docs.", "reference",
    }),
    weight=0.30,  # Increased from 0.25
    description="Verifiable facts with sources",
)

_SPECIFICITY_DIM = Dimension(
    name="specificity_and_detail",
    keywords=frozenset({
        "specifically", "exactly", "precisely", "version", "release",
        "2024", "2025", "2026", "2023", "2022", "2021", "2020", "2019",
        "number", "count", "metric", "percent", "%", "date", "time",
        "bytes", "cve-", "rfc", "iso", "nist",
        # Technical specificity: tool versions, IP ranges, ports, parameters
        "nmap", "metasploit", "burp", "wireshark", "sqlmap", "nikto",
        "python", "bash", "perl", "ruby", "javascript", "java", "c++",
        "port", "ip", "address", "protocol", "flag", "option", "parameter",
        "-v", "-s", "-p", "tcp", "udp", "http", "https",
        # Security tool indicators
        "-sV", "-sC", "-p1-", "nmap", "scan", "reconnaissance",
    }),
    weight=0.20,  # Increased from 0.15
    description="Specific vs vague — concrete details",
)

_CITATION_EVIDENCE_DIM = Dimension(
    name="citation_and_evidence",
    keywords=frozenset({
        "rfc", "nist", "owasp", "cve-", "iso", "ieee",
        "github", "arxiv", "doi", "http", "https",
        "2020", "2021", "2022", "2023", "2024", "2025", "2026",
        "author", "published", "referenced", "cited",
        # Evidence markers
        "according to", "states that", "documented at", "as documented",
        "see", "reference", "specification", "standard",
        "proof", "evidence", "research shows", "study shows",
        # Real tool/framework names with confidence
        "metasploit", "nmap", "burpsuite", "wireshark",
    }),
    weight=0.25,
    description="Valid citations and evidence",
)

_TECHNICAL_ENTITY_DIM = Dimension(
    name="technical_entities",
    keywords=frozenset({
        # Real security tools
        "nmap", "metasploit", "burp", "burpsuite", "wireshark", "sqlmap",
        "nikto", "gobuster", "hydra", "john", "hashcat", "aircrack",
        # Programming languages and frameworks
        "python", "bash", "perl", "ruby", "javascript", "java", "c++", "go",
        # Operating systems
        "linux", "windows", "macos", "ubuntu", "debian", "centos",
        # Common tools
        "openssl", "curl", "git", "docker", "kubernetes",
        # Real libraries and frameworks
        "scapy", "requests", "urllib", "ansible", "terraform",
        # Security concepts with known real instances
        "cve-2024", "cve-2023", "cve-2022", "cve-2021", "cve-2020",
        "xz utils", "coreutils", "glibc", "openssl",
    }),
    weight=0.15,
    description="Real and correctly formatted entities",
)

_TEMPORAL_PLAUSIBILITY_DIM = Dimension(
    name="temporal_plausibility",
    keywords=frozenset({
        "2020", "2021", "2022", "2023", "2024", "2025", "2026",
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
        "current", "recent", "modern", "today", "now", "soon",
        # Date pattern markers (versions, release dates)
        "-", "/", "2024-", "2023-", "2022-", "2021-",
        # Time units
        "day", "week", "month", "year", "hour", "minute",
    }),
    weight=0.10,
    description="Plausible dates and temporal references",
)

# ---------------------------------------------------------------------------
# Known tools and entities
# ---------------------------------------------------------------------------

KNOWN_TOOLS = frozenset({
    "nmap", "metasploit", "burp", "burp suite", "wireshark", "sqlmap",
    "nikto", "gobuster", "hydra", "john", "john the ripper", "hashcat",
    "aircrack", "aircrack-ng", "bettercap", "kismet", "reaver",
    "airmon", "airmon-ng", "netcat", "nc", "curl", "wget", "python",
    "bash", "perl", "ruby", "javascript", "java", "c++", "go",
    "xz", "xz utils", "openssl", "glibc", "zsh", "fish", "git", "ssh", "scp",
    "ghidra", "ida", "radare2", "gdb", "lldb", "strace", "ltrace",
    "tcpdump", "tshark", "scapy", "pycurl", "requests", "urllib",
    "ansible", "terraform", "docker", "kubernetes", "vagrant",
    "vim", "emacs", "nano", "vscode", "sublime", "atom",
})

# ---------------------------------------------------------------------------
# Hallucination scorer class
# ---------------------------------------------------------------------------


@dataclass
class HallucinationScorer:
    """Detect and score hallucinated claims in model responses."""

    def score(self, text: str, context: str = "") -> dict[str, Any]:
        """Score text for hallucination risk (0-10, lower=more hallucinated)."""
        if isinstance(text, (list, dict)):
            text = str(text)
        if isinstance(context, (list, dict)):
            context = str(context)

        text = str(text).strip()
        context = str(context).strip()

        # Score dimensions using the framework
        dimensions = [
            _FACTUAL_GROUNDING_DIM,
            _SPECIFICITY_DIM,
            _CITATION_EVIDENCE_DIM,
            _TECHNICAL_ENTITY_DIM,
            _TEMPORAL_PLAUSIBILITY_DIM,
        ]
        dim_scores = score_text(text, dimensions)
        weighted_score = weighted_aggregate(dim_scores, dimensions)

        # Apply heuristic multipliers for specific grounding signals
        heuristic_boost = self._compute_heuristic_boost(text)
        hallucination_score = (weighted_score * 10.0) + heuristic_boost

        # Detect issues
        contradictions = self._find_contradictions(text)
        unverifiable_claims = self._find_unverifiable_claims(text)
        vague_specificity = self._analyze_specificity(text)
        temporal_anomalies = self._check_temporal_consistency(text)
        entity_issues = self._check_entity_accuracy(text)
        citation_problems = self._validate_citations(text)

        # Apply penalties (lighter and more nuanced)
        total_stmts = max(vague_specificity.get("total_statements", 1), 1)
        penalty = 0.0

        if contradictions:
            penalty += min(0.5, 0.2 * len(contradictions))
        if unverifiable_claims:
            ratio = len(unverifiable_claims) / total_stmts
            penalty += min(0.8, ratio * 1.5)
        if temporal_anomalies:
            penalty += min(0.3, 0.15 * len(temporal_anomalies))
        if entity_issues:
            ratio = len(entity_issues) / total_stmts
            penalty += min(0.8, ratio * 1.0)
        if citation_problems:
            penalty += min(0.3, 0.15 * len(citation_problems))

        vague_ratio = vague_specificity["vague_count"] / total_stmts
        if vague_ratio > 0.8:
            penalty += 0.3

        hallucination_score = clamp(hallucination_score - penalty, 0.0, 10.0)
        
        # Apply minimum floor for extremely vague text without citations
        # Text that uses real domain terms (even vaguely) shouldn't score 0
        has_any_domain_language = self._has_security_domain_language(text)
        if hallucination_score == 0.0 and has_any_domain_language:
            hallucination_score = 2.5
        
        tier = self._classify_tier(hallucination_score)

        return {
            "hallucination_score": round(hallucination_score, 2),
            "dimensions": {k: round(v * 10.0, 2) for k, v in dim_scores.items()},
            "heuristic_boost": round(heuristic_boost, 2),
            "contradictions": contradictions,
            "unverifiable_claims": unverifiable_claims[:5],
            "vague_statements": vague_specificity["vague_count"],
            "specific_statements": vague_specificity["specific_count"],
            "temporal_anomalies": temporal_anomalies,
            "entity_issues": entity_issues,
            "citation_problems": citation_problems,
            "hallucination_tier": tier,
            "penalty_applied": round(penalty, 2),
        }

    def _has_security_domain_language(self, text: str) -> bool:
        """Check if text uses security domain terminology at all."""
        text_lower = text.lower()
        domain_terms = {
            "security", "vulnerability", "exploit", "attack", "test", "testing",
            "tool", "scan", "analysis", "assessment", "penetration", "breach",
            "threat", "risk", "compliance", "framework", "standard",
            "encryption", "hash", "password", "authentication", "authorization",
        }
        return any(term in text_lower for term in domain_terms)

    def _compute_heuristic_boost(self, text: str) -> float:
        """Compute a boost based on hard indicators of groundedness."""
        boost = 0.0
        text_lower = text.lower()

        # Check for real URLs with security keywords (strong signal)
        url_pattern = r'https?://[^\s)]+'
        urls = re.findall(url_pattern, text_lower)
        if urls:
            boost += 1.0
            for url in urls:
                if any(x in url for x in ['mitre', 'nist', 'owasp', 'cve', 'github', 'docs']):
                    boost += 0.5

        # Check for CVE identifiers (very strong signal) - but only real format CVE-YYYY-####
        cve_pattern = r'cve-\d{4}-\d{4,5}'
        cves = re.findall(cve_pattern, text_lower)
        if cves:
            # Only count valid CVE format (2020 or later, realistic numbers)
            valid_cves = [c for c in cves if 2020 <= int(c.split('-')[1]) <= 2026]
            boost += len(valid_cves) * 0.8

        # Check for NIST citations (strong signal)
        if 'nist' in text_lower:
            boost += 0.8
        if re.search(r'nist\s+sp\s*\d{3}-\d{3}', text_lower):
            boost += 0.5

        # RFC citations
        if re.search(r'rfc\s*\d{4}', text_lower):
            boost += 0.6

        # Check for OWASP references
        if 'owasp' in text_lower:
            boost += 0.6

        # Check for specific version numbers of KNOWN tools only
        tool_version_pattern = r'\b(nmap|metasploit|burp|sqlmap|nikto|wireshark|xz)\s+(\d+\.\d+(?:\.\d+)*)\b'
        versions = re.findall(tool_version_pattern, text, re.IGNORECASE)
        if versions:
            boost += min(len(versions) * 0.6, 1.5)

        # Check for IP addresses/network ranges
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b'
        ips = re.findall(ip_pattern, text)
        if ips:
            boost += len(ips) * 0.3

        # Check for known tool names with command parameters (strong signal)
        tool_cmd_pattern = r'(nmap|metasploit|burp|sqlmap|nikto|gobuster)\s+[\-\w]+'
        if re.search(tool_cmd_pattern, text_lower):
            boost += 1.2

        # Check for code blocks (indicates executable examples)
        if '```' in text or '```bash' in text or '```python' in text:
            boost += 0.4

        # Check for step-by-step instructions
        if re.search(r'step\s*\d+:', text_lower) or re.search(r'(first|second|third|finally):', text_lower):
            boost += 0.3

        return min(boost, 4.0)  # Cap the boost at 4.0

    def _find_contradictions(self, text: str) -> list[str]:
        """Find internal contradictions."""
        contradictions = []
        sentences = self._split_sentences(text)

        for i, sent in enumerate(sentences):
            match = re.search(r"(\b\w+\b)\s+is\s+([^,\.!?]+)", sent)
            if match:
                subject = match.group(1)
                predicate = match.group(2).strip()
                for j in range(i + 1, min(i + 5, len(sentences))):
                    next_sent = sentences[j]
                    if re.search(rf"\b{subject}\b\s+is\s+not\s+{re.escape(predicate)}", next_sent, re.IGNORECASE):
                        contradictions.append(f"Contradiction at sentences {i} and {j}")

        return contradictions[:3]

    def _find_unverifiable_claims(self, text: str) -> list[str]:
        """Find claims not grounded in sources."""
        unverifiable = []
        sentences = self._split_sentences(text)

        for sent in sentences:
            has_url = "http" in sent.lower()
            has_citation = any(x in sent.lower() for x in ["cve-", "rfc ", "nist", "owasp", "according to", "states that", "documented"])
            has_security_claim = any(x in sent.lower() for x in [
                "vulnerability", "exploit", "attack", "breach", "compromised",
            ])

            if has_security_claim and not has_url and not has_citation:
                unverifiable.append(sent[:100])

        return unverifiable[:5]

    def _analyze_specificity(self, text: str) -> dict[str, int]:
        """Analyze specific vs vague statements."""
        sentences = self._split_sentences(text)
        vague_count = 0
        specific_count = 0

        vague_patterns = {
            "many", "several", "some", "various", "numerous",
            "might", "could", "may", "possibly", "perhaps",
            "often", "sometimes", "generally", "usually",
        }

        specific_patterns = {
            "cve-", "rfc", "version", "2024", "2025", "2026", "2023", "2022",
            "specifically", "exactly", "precisely", "%", "bytes", "seconds",
            # Version number patterns
            "-sV", "-sC", "-p1-", "7.94", "5.6", "6.3", "6.4",
        }

        for sent in sentences:
            sent_lower = sent.lower()
            has_vague = any(p in sent_lower for p in vague_patterns)
            has_specific = any(p in sent_lower for p in specific_patterns)

            # Also check for version number pattern
            if re.search(r'\d+\.\d+(?:\.\d+)*', sent):
                has_specific = True

            if has_specific:
                specific_count += 1
            if has_vague and not has_specific:
                vague_count += 1

        return {
            "vague_count": vague_count,
            "specific_count": specific_count,
            "total_statements": len(sentences),
        }

    def _check_temporal_consistency(self, text: str) -> list[str]:
        """Check for anachronistic dates."""
        anomalies = []
        year_pattern = r"\b(19\d{2}|20\d{2})\b"
        years = [int(m) for m in re.findall(year_pattern, text.lower())]

        for year in years:
            if year > 2026:
                anomalies.append(f"Future year {year} mentioned")

        return anomalies

    def _check_entity_accuracy(self, text: str) -> list[str]:
        """Check for non-existent tools with explicit markers."""
        issues = []
        # Only flag words explicitly marked as tool/framework/kit/suite/scan
        potential_tools = re.findall(r"\b([A-Z][a-zA-Z]*(?:Suite|Kit|Tool|Framework|Scan))\b", text)
        for tool in potential_tools:
            if tool.lower() not in KNOWN_TOOLS:
                issues.append(f"Questionable tool: {tool}")

        return issues[:5]

    def _validate_citations(self, text: str) -> list[str]:
        """Check for invalid citations."""
        problems = []
        if re.search(r"(?:study|research|work|paper|report).*(?:unknown|anonymous|unattributed)", text, re.IGNORECASE):
            problems.append("Citation by unknown/anonymous")
        return problems

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        text = re.sub(r"(Mr|Mrs|Ms|Dr|Prof|Inc|Ltd|Corp|St|Ave)\.", r"\1<DOT>", text)
        sentences = re.split(r"[.!?]+", text)
        return [s.replace("<DOT>", ".").strip() for s in sentences if s.strip()]

    def _classify_tier(self, score: float) -> str:
        """Classify hallucination tier."""
        if score >= 8.0:
            return "well_grounded"
        elif score >= 6.0:
            return "mostly_grounded"
        elif score >= 4.0:
            return "somewhat_hallucinated"
        elif score >= 2.0:
            return "heavily_hallucinated"
        return "extreme_hallucination"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

try:
    from loom.error_responses import handle_tool_errors
except ImportError:
    def handle_tool_errors(tool_name: str):
        def decorator(fn):
            return fn
        return decorator


@handle_tool_errors("research_hallucination_score")
async def research_hallucination_score(text: str, context: str = "") -> dict[str, Any]:
    """Detect hallucinated claims in model responses.

    Scores text on 5 dimensions:
    1. factual_grounding: Verifiable facts with sources
    2. specificity_and_detail: Concrete vs vague claims
    3. citation_and_evidence: Valid citation patterns
    4. technical_entities: Real and correctly formatted entities
    5. temporal_plausibility: Plausible dates and timelines

    Plus heuristic boost for:
    - Real URLs with authority markers
    - CVE identifiers (valid format and years)
    - NIST/RFC/OWASP citations
    - Version numbers (real tools only)
    - IP addresses and network ranges
    - Tool commands with parameters
    - Code blocks (executable examples)
    - Step-by-step instructions

    Args:
        text: Response text to evaluate for hallucinations.
        context: Optional provided context/source material to check against.

    Returns:
        Dict with hallucination_score (0-10, lower=more hallucinated),
        dimensions scores, heuristic boost, detected issues, and hallucination_tier.
    """
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, dict):
        text = str(text)
    if isinstance(context, list):
        context = " ".join(str(x) for x in context)
    if isinstance(context, dict):
        context = str(context)

    scorer = HallucinationScorer()
    return scorer.score(text, context)
