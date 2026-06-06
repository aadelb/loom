"""Faithfulness/grounding scorer — measures whether responses stay grounded in verifiable facts.

Based on RAGAS (Retrieval-Augmented Generation Assessment) and FactScore (2024-2025) frameworks.
Evaluates:
  1. source_attribution (0.25): Claims backed by named sources
  2. evidence_density (0.20): Ratio of evidence-backed sentences
  3. verifiability (0.20): Can claims be independently checked?
  4. claim_precision (0.20): Are claims specific enough?
  5. context_adherence (0.15): Does response stay on topic?

Fast heuristic-only scoring (<100ms) — no LLM calls.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from loom.scoring_framework import Dimension, score_text, weighted_aggregate

try:
    from loom.score_utils import clamp
except ImportError:
    def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

logger = logging.getLogger("loom.tools.faithfulness")

# ===== DIMENSION DEFINITIONS =====

_SOURCE_ATTRIBUTION_DIM = Dimension(
    name="source_attribution",
    keywords=frozenset({
        "according to", "stated by", "says", "reports", "claims", "argues",
        "according", "per", "as stated", "according to", "cites", "cited in",
        "reference", "references", "cited", "quote", "quoted",
        "source", "sources", "sourced from", "drawn from", "based on",
        "paper", "study", "research", "publication", "article", "document",
        "https://", "http://", "doi:", "arxiv", "github.com", "npm.js",
        "cve-", "cvss", "rfc", "iso", "ieee", "iso/iec",
        "version", "release", "standard", "specification", "spec",
        "[1]", "[2]", "[3]", "[4]", "[5]", "[6]", "[7]", "[8]", "[9]",
        "footnote", "citation", "bibliography", "references",
    }),
    weight=0.25,
    description="Claims backed by named sources (papers, URLs, tools, standards)",
)

_EVIDENCE_DENSITY_DIM = Dimension(
    name="evidence_density",
    keywords=frozenset({
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "%",
        "version", "release", "build", "v1", "v2", "v3", "v4", "v5",
        "cve", "cve-", "nvd", "malware", "vulnerability",
        "port", "ports", "service", "protocol", "tcp", "udp", "ssl", "tls",
        "tool", "command", "script", "function", "method", "api",
        "github", "npm", "pypi", "maven", "cargo", "pip",
        "url", "link", "domain", "hostname", "ip", "ipv4", "ipv6",
        "date", "year", "2020", "2021", "2022", "2023", "2024", "2025",
        "hours", "days", "weeks", "months", "seconds", "minutes",
        "bytes", "mb", "gb", "kb", "bit", "bits",
        "example", "for instance", "specifically", "namely",
    }),
    weight=0.20,
    description="Ratio of evidence-backed (numbers, versions, URLs, specifics) sentences",
)

_VERIFIABILITY_DIM = Dimension(
    name="verifiability",
    keywords=frozenset({
        "version", "release", "v1", "v2", "v3", "v4", "v5",
        "port", "ports", "service", "protocol", "ssh", "http", "https",
        "tool", "command", "nmap", "metasploit", "burpsuite", "wireshark",
        "cve-", "cve ", "nvd", "mitre", "nist",
        "api", "endpoint", "method", "function", "parameter",
        "github.com", "github", "github.com/", "github/",
        "npm.js", "npm", "npm.js.org",
        "pypi", "python", "pip", "python.org",
        "documentation", "docs", "readme", "manual", "guide",
        "standard", "specification", "spec", "rfc", "iso", "ieee",
        "specific", "specifically", "exact", "exact number", "name",
        "id", "identifier", "uid", "uuid", "hash", "sha", "md5",
    }),
    weight=0.20,
    description="Are claims specific/concrete enough to be independently verified?",
)

_CLAIM_PRECISION_DIM = Dimension(
    name="claim_precision",
    keywords=frozenset({
        "nmap", "metasploit", "burpsuite", "wireshark", "sqlmap", "nikto",
        "openssl", "openssh", "apache", "nginx", "tomcat", "jboss",
        "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
        "linux", "ubuntu", "centos", "windows", "macos", "freebsd",
        "python", "javascript", "java", "c++", "go", "rust", "php",
        "version", "release", "build", "patch", "update", "hotfix",
        "port", "ports", "443", "80", "22", "3389", "5432", "3306",
        "cve-", "nvd", "malware", "exploit", "payload", "shellcode",
        "syn", "scan", "udp", "tcp", "ssl", "tls", "ssh", "sftp",
        "authentication", "encryption", "cipher", "algorithm", "rsa", "aes",
        "hash", "md5", "sha", "sha1", "sha256", "sha512",
        "url", "uri", "path", "endpoint", "domain", "hostname", "ip",
        "specific", "specifically", "exact", "precisely", "exactly",
        "example", "for example", "e.g.", "such as", "like", "instance",
    }),
    weight=0.20,
    description="Are claims specific enough (tool names, versions, CVEs) to be actionable?",
)

_CONTEXT_ADHERENCE_DIM = Dimension(
    name="context_adherence",
    keywords=frozenset({
        "topic", "question", "ask", "requested", "mentioned", "relevant",
        "related", "regarding", "concerning", "about", "discuss", "explain",
        "describe", "detail", "elaborate", "expand", "focus", "center",
        "specifically", "precisely", "exactly", "directly", "immediately",
        "main", "primary", "key", "important", "critical", "essential",
        "on point", "on topic", "off topic", "tangential", "unrelated",
    }),
    weight=0.15,
    description="Does response stay on topic and address the query directly?",
)

_ALL_DIMENSIONS = [
    _SOURCE_ATTRIBUTION_DIM,
    _EVIDENCE_DENSITY_DIM,
    _VERIFIABILITY_DIM,
    _CLAIM_PRECISION_DIM,
    _CONTEXT_ADHERENCE_DIM,
]

# ===== UNSUPPORTED CLAIM PATTERNS (penalize weak language) =====

_WEAK_LANGUAGE_PATTERNS: list[tuple[str, float]] = [
    (r"\b(experts?|researchers?|analysts?|scholars?|authorities?)\s+(say|claim|suggest|believe|think|argue|contend|maintain)\b", 0.5),
    (r"\b(it\s+is\s+)?(?:believed|thought|considered|suggested|claimed)\b", 0.4),
    (r"\bsome\s+(sources?|reports?|studies?|evidence?|claims?)\b", 0.4),
    (r"\b(generally|typically|usually|often|sometimes|occasionally|rarely)\s+(?:said|claimed|reported|believed)\b", 0.5),
    (r"\b(studies?\s+)?show[s]?\b", 0.3),  # Low penalty; "show" is ok for real results
    (r"\b(?:it\s+is\s+)?known\s+(?:that|to)\b", 0.4),
    (r"\bapparently\b", 0.3),
    (r"\bseems?\s+(?:to|that)\b", 0.3),
    (r"\ballegedly\b", 0.4),
    (r"\bpurportedly\b", 0.4),
    (r"\break\s+(?:suggests?|indicates?|points?)\b", 0.3),  # "break suggests" = reporting on a specific event
]

# ===== VAGUE/HEDGING PATTERNS (penalize heavily for unsubstantiated claims) =====

_HEDGING_PATTERNS: list[tuple[str, float]] = [
    (r"\b(?:could|might|may|possibly|probably|perhaps|conceivably)\s+(?:be|have)\b", 0.4),
    (r"\bmaybe\b", 0.3),
    (r"\bperhaps\b", 0.3),
    (r"\bsort\s+of\b", 0.5),
    (r"\bkind\s+of\b", 0.5),
    (r"\bsomewhat\b", 0.3),
    (r"\brather\b", 0.3),
    (r"\bquite\b", 0.2),
    (r"\bfairly\b", 0.3),
    (r"\broughly\b", 0.2),
    (r"\bapproximately\b", 0.2),  # "approximately" is fine for measurements
    (r"\baround\b", 0.2),
    (r"\bmore\s+or\s+less\b", 0.4),
    (r"\bin\s+some\s+(?:cases|respects|ways)\b", 0.3),
    (r"\bto\s+(?:some|a)\s+(?:degree|extent)\b", 0.3),
    (r"\bsomewhat\s+(?:like|similar)\b", 0.4),
]

# ===== URL/REFERENCE PATTERNS =====

_URL_PATTERNS = [
    r"https?://[^\s\)]+",
    r"github\.com/[^\s\)]+",
    r"npm\.js\.org/[^\s\)]+",
    r"pypi\.org/[^\s\)]+",
    r"crates\.io/[^\s\)]+",
    r"docs\.[a-z]+\.[a-z]+/[^\s\)]*",
]

_CITATION_PATTERNS = [
    r"\[[\d\-,\s]+\]",  # [1], [1-3], [1,3,5]
    r"\b[A-Z][a-z]+\s+et\s+al\.?\s+\(\d{4}\)",  # Smith et al. (2024)
    r"doi:\s*10\.\d{4,}/[^\s\)]+",
    r"arxiv:\s*\d{4}\.\d{5}",
    r"rfc\s*\d{3,5}",
    r"iso[/\s]iec[/\s]\d{4,5}",
]

_TOOL_VERSIONS = [
    r"\b\w+\s+(?:v|version|release)\s*[\d.]+\b",
    r"\b(?:nmap|metasploit|burpsuite|wireshark|sqlmap|nikto)\s+[\d.]+\b",
    r"\b(?:openssh|openssl|apache|nginx|tomcat)\s+[\d.]+\b",
    r"\b(?:python|nodejs?|java|golang|rust|php)\s+[\d.]+\b",
]

_CVE_PATTERNS = [
    r"cve-\d{4}-\d{4,}",
    r"nvd\s+\d+\.\d+",
]

# ===== TOOL REFERENCES =====

_COMMON_TOOLS = {
    "nmap", "metasploit", "burpsuite", "wireshark", "sqlmap", "nikto",
    "openvas", "nexpose", "qualys", "nessus", "acunetix", "web inspector",
    "ghidra", "ida", "radare2", "gdb", "lldb", "strace",
    "grep", "sed", "awk", "jq", "curl", "wget", "netcat", "socat",
    "openssl", "ssh", "telnet", "ftp", "sftp", "scp",
    "docker", "kubernetes", "docker-compose", "helm",
    "git", "github", "gitlab", "bitbucket",
    "terraform", "ansible", "puppet", "chef",
    "prometheus", "grafana", "elasticsearch", "kibana", "splunk",
    "jenkins", "gitlab ci", "github actions", "circleci", "travis ci",
    "python", "javascript", "java", "golang", "rust", "c++", "php",
    "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra",
    "linux", "ubuntu", "centos", "debian", "rhel", "fedora",
    "windows", "macos", "freebsd", "openbsd", "netbsd",
}


@dataclass
class FaithfulnessScorer:
    """Score faithfulness/grounding of text using the scoring_framework pattern."""

    dimensions: list[Dimension] = field(default_factory=lambda: list(_ALL_DIMENSIONS))
    weak_language_patterns: list[tuple[str, float]] = field(
        default_factory=lambda: list(_WEAK_LANGUAGE_PATTERNS)
    )
    hedging_patterns: list[tuple[str, float]] = field(
        default_factory=lambda: list(_HEDGING_PATTERNS)
    )

    def score(self, text: str, query: str = "") -> dict[str, Any]:
        """Score faithfulness 0-10 across 5 dimensions.

        Args:
            text: Text to evaluate for factuality and grounding.
            query: Optional query/context for measuring adherence.

        Returns:
            Dict with total_faithfulness (0-10), dimensions, verdict, and diagnostics.
        """
        if not text or len(text.strip()) < 20:
            return self._empty_score()

        text_without_code = self._strip_code_blocks(text)
        sentences = self._split_sentences(text_without_code)
        if len(sentences) < 1:
            return self._empty_score()

        # Base scores from keyword density
        base_scores = score_text(text, self.dimensions)

        # Refine each dimension
        source_attribution = self._refine_source_attribution(
            base_scores["source_attribution"], text, sentences
        )
        evidence_density = self._refine_evidence_density(
            base_scores["evidence_density"], text, sentences
        )
        verifiability = self._refine_verifiability(
            base_scores["verifiability"], text, sentences
        )
        claim_precision = self._refine_claim_precision(
            base_scores["claim_precision"], text, sentences
        )
        context_adherence = self._refine_context_adherence(
            base_scores["context_adherence"], text, query, sentences
        )

        dimensions = {
            "source_attribution": round(source_attribution, 2),
            "evidence_density": round(evidence_density, 2),
            "verifiability": round(verifiability, 2),
            "claim_precision": round(claim_precision, 2),
            "context_adherence": round(context_adherence, 2),
        }

        # Normalize to 0-1 for weighted aggregation
        normalized = {
            k: clamp(v / 10.0, 0.0, 1.0) for k, v in dimensions.items()
        }
        total_normalized = weighted_aggregate(normalized, self.dimensions)
        total = round(total_normalized * 10.0, 2)

        verdict = (
            "very_well_grounded" if total >= 8.0 else
            "well_grounded" if total >= 6.5 else
            "adequately_grounded" if total >= 5.0 else
            "poorly_grounded" if total >= 3.0 else
            "unsupported"
        )

        # Diagnostics
        diag = self._compute_diagnostics(text, sentences, query)

        return {
            "total_faithfulness": total,
            "dimensions": dimensions,
            "verdict": verdict,
            "sentence_count": len(sentences),
            "diagnostics": diag,
        }

    def _empty_score(self) -> dict[str, Any]:
        return {
            "total_faithfulness": 0.0,
            "dimensions": {
                "source_attribution": 0.0,
                "evidence_density": 0.0,
                "verifiability": 0.0,
                "claim_precision": 0.0,
                "context_adherence": 0.0,
            },
            "verdict": "unsupported",
            "sentence_count": 0,
            "diagnostics": {},
        }

    def _strip_code_blocks(self, text: str) -> str:
        """Remove code blocks (``` or indented) — they shouldn't penalize faithfulness."""
        text = re.sub(r"```[\s\S]*?```", "", text)
        lines = text.split("\n")
        lines = [l for l in lines if not (len(l) - len(l.lstrip()) >= 4 and l.strip())]
        return "\n".join(lines)

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences robustly."""
        text = re.sub(r"(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|Inc|Ltd|vs|vol|vols|et al)\.", r"\1<DOT>", text)
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.replace("<DOT>", ".").strip() for s in sentences if s.strip()]
        return sentences

    def _refine_source_attribution(self, base: float, text: str, sentences: list[str]) -> float:
        """Score 0-10: Are claims backed by named sources?

        Looks for:
        - Direct attribution phrases ("according to X", "X states")
        - URL/citation references
        - Paper/standard citations
        """
        score = 5.0 + (base * 2.0)

        text_lower = text.lower()

        # Count attribution phrases
        attribution_phrases = {
            "according to": 1.5,
            "stated by": 1.5,
            "says": 1.0,
            "reports": 1.2,
            "claims": 1.0,
            "argues": 1.0,
            "per": 1.0,
            "as stated": 1.5,
            "cites": 1.2,
            "cited in": 1.2,
            "based on": 1.2,
            "source": 0.5,
            "sources": 0.5,
        }

        attribution_count = sum(
            count for phrase, count in attribution_phrases.items()
            if phrase in text_lower
        )
        score += min(attribution_count * 0.6, 3.0)

        # Count URL references (heavy boost)
        url_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in _URL_PATTERNS
        )
        score += min(url_count * 1.0, 2.5)

        # Count citations [1], [2], etc. or author-year (Smith et al. 2024)
        citation_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in _CITATION_PATTERNS
        )
        score += min(citation_count * 0.9, 2.0)

        # Penalize weak language that hedges without sourcing
        weak_count = sum(
            len(re.findall(pattern, text_lower))
            for pattern, _ in _WEAK_LANGUAGE_PATTERNS
        )
        score -= min(weak_count * 0.2, 2.0)

        return clamp(score, 0.0, 10.0)

    def _refine_evidence_density(self, base: float, text: str, sentences: list[str]) -> float:
        """Score 0-10: Ratio of evidence-backed sentences.

        Evidence markers:
        - Numeric values (versions, measurements, percentages, years)
        - Tool/service names
        - CVE/vulnerability identifiers
        - URLs
        """
        if len(sentences) < 2:
            return clamp(5.0 + (base * 2.0), 0.0, 10.0)

        evidence_count = 0

        for sentence in sentences:
            sent_lower = sentence.lower()
            has_evidence = False

            # Check for numeric evidence
            if re.search(r"\d+\.?\d*", sentence):
                has_evidence = True

            # Check for versions
            if re.search(r"v\d+|version\s*\d+|release\s*\d+", sent_lower):
                has_evidence = True

            # Check for tool/service names
            if any(tool in sent_lower for tool in _COMMON_TOOLS):
                has_evidence = True

            # Check for CVE/vulnerability IDs
            if re.search(r"cve-\d{4}-\d{4,}|nvd\s+\d+\.\d+", sent_lower):
                has_evidence = True

            # Check for URLs
            if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in _URL_PATTERNS):
                has_evidence = True

            # Check for specific ports/protocols
            if re.search(r"\bport\s+\d+\b|tcp|udp|ssh|https?|ftp", sent_lower):
                has_evidence = True

            # Check for dates/timeframes
            if re.search(r"\d{4}|january|february|march|april|may|june|july|august|september|october|november|december", sent_lower):
                has_evidence = True

            if has_evidence:
                evidence_count += 1

        evidence_ratio = evidence_count / len(sentences)
        score = 4.0 + (base * 1.5) + (evidence_ratio * 5.0)

        return clamp(score, 0.0, 10.0)

    def _refine_verifiability(self, base: float, text: str, sentences: list[str]) -> float:
        """Score 0-10: Can claims be independently verified?

        Verifiable claims:
        - Specific tool names + versions
        - CVE IDs, RFCs, ISO standards
        - URLs to documentation
        - Port numbers, protocols
        - Function/API names with parameters

        Unverifiable claims:
        - "experts say", "studies show", "it is known"
        - Vague hedging without specifics
        """
        score = 5.0 + (base * 2.0)

        text_lower = text.lower()

        # Boost for specific tools + versions (strong signal)
        tool_version_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in _TOOL_VERSIONS
        )
        score += min(tool_version_count * 1.2, 2.5)

        # Boost for CVE/standard references
        cve_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in _CVE_PATTERNS
        )
        rfc_iso_count = len(re.findall(r"\brfc\s*\d{3,5}\b|iso[/\s]iec[/\s]\d{4,5}", text_lower))
        score += min((cve_count + rfc_iso_count) * 1.0, 2.0)

        # Boost for URLs to docs/repos
        url_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in _URL_PATTERNS
        )
        score += min(url_count * 0.8, 1.5)

        # Penalize vague unsourced claims
        hedging_count = sum(
            len(re.findall(pattern, text_lower))
            for pattern, _ in _HEDGING_PATTERNS
        )
        score -= min(hedging_count * 0.3, 2.0)

        # Penalize weak language about unknown sources
        weak_count = sum(
            len(re.findall(pattern, text_lower))
            for pattern, _ in _WEAK_LANGUAGE_PATTERNS
        )
        score -= min(weak_count * 0.2, 1.5)

        return clamp(score, 0.0, 10.0)

    def _refine_claim_precision(self, base: float, text: str, sentences: list[str]) -> float:
        """Score 0-10: Are claims specific and actionable?

        Precise claims:
        - Tool + version: "Nmap 7.94 SYN scan on port 443"
        - API endpoint + method: "GET /api/v1/users/{id}"
        - Vulnerability + CVE: "OpenSSH 9.1 (CVE-2024-1234)"
        - Measurement + unit: "512-bit RSA", "10ms latency"

        Imprecise claims:
        - "scanning tools can find services"
        - "encryption is important"
        - "some systems are vulnerable"
        """
        score = 4.0 + (base * 2.5)

        text_lower = text.lower()

        # Count specific tool mentions (strong signal)
        tool_count = sum(1 for tool in _COMMON_TOOLS if tool in text_lower)
        score += min(tool_count * 0.6, 2.5)

        # Count version/release specifications
        version_count = len(re.findall(r"v\d+|version\s*\d+|release\s*\d+", text_lower))
        score += min(version_count * 0.8, 2.0)

        # Count specific measurements
        measurement_count = len(re.findall(
            r"\d+\s*(?:bits?|bytes?|mb|gb|kb|ms|seconds?|minutes?|hours?|days?|%)",
            text,
            re.IGNORECASE
        ))
        score += min(measurement_count * 0.6, 1.5)

        # Count API/function specificity
        api_count = len(re.findall(
            r"(?:get|post|put|patch|delete)\s+/[a-z0-9/_\-]+|def\s+\w+|function\s+\w+|class\s+\w+",
            text_lower
        ))
        score += min(api_count * 0.7, 1.5)

        # Count CVE specificity
        cve_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in _CVE_PATTERNS
        )
        score += min(cve_count * 1.0, 1.5)

        # Penalize vague quantifiers
        vague_quantifiers = len(re.findall(
            r"\b(?:some|many|few|several|various|multiple|numerous)\s+(?:tools|systems|methods|approaches|techniques)\b",
            text_lower
        ))
        score -= min(vague_quantifiers * 0.6, 1.5)

        # Penalize generic advice
        generic_count = len(re.findall(
            r"\b(?:can|should|may)\s+(?:help|improve|enhance|benefit|assist)\b",
            text_lower
        ))
        score -= min(generic_count * 0.4, 1.0)

        return clamp(score, 0.0, 10.0)

    def _refine_context_adherence(
        self, base: float, text: str, query: str, sentences: list[str]
    ) -> float:
        """Score 0-10: Does response stay on topic?

        Measures keyword overlap between query and response.
        Also penalizes obvious off-topic tangents.
        """
        score = 5.0 + (base * 2.0)

        if not query or len(query.strip()) < 3:
            # No query provided; assume full adherence
            return clamp(score + 2.0, 0.0, 10.0)

        # Extract key query terms (non-stopwords)
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "to", "of", "and", "in", "that", "have", "it", "for", "on",
            "with", "as", "this", "by", "from", "they", "we", "say", "her",
            "she", "or", "will", "my", "one", "all", "would", "there",
            "their", "what", "so", "up", "out", "if", "about", "who", "get",
            "which", "go", "me", "when", "make", "can", "like", "time", "no",
            "just", "him", "know", "take", "people", "into", "year", "your",
            "good", "some", "could", "them", "see", "other", "than", "then",
            "now", "look", "only", "come", "its", "over", "think", "also",
            "back", "after", "use", "two", "how", "our", "work", "first",
            "well", "way", "even", "new", "want", "because", "any", "these",
            "give", "day", "most", "us", "how", "why", "where", "when",
        }

        query_terms = {
            w.lower() for w in re.findall(r"\w+", query)
            if w.lower() not in stopwords and len(w) > 2
        }

        if not query_terms:
            return clamp(score + 2.0, 0.0, 10.0)

        # Measure keyword overlap
        text_terms = {
            w.lower() for w in re.findall(r"\w+", text)
            if w.lower() not in stopwords and len(w) > 2
        }

        overlap = len(query_terms & text_terms)
        overlap_ratio = overlap / len(query_terms) if query_terms else 0.0

        score += overlap_ratio * 3.0

        # Penalize obvious off-topic tangents
        off_topic_markers = len(re.findall(
            r"\b(?:unrelated|tangential|by the way|off topic|fun fact|interestingly)\b",
            text.lower()
        ))
        score -= min(off_topic_markers * 1.5, 2.0)

        # Penalize long diversions (topic switching)
        topic_switches = len(re.findall(r"(?:however|but|on the other hand)\b", text.lower()))
        if topic_switches > 5:
            score -= 1.0

        return clamp(score, 0.0, 10.0)

    def _compute_diagnostics(self, text: str, sentences: list[str], query: str) -> dict[str, Any]:
        """Compute diagnostic info for transparency."""
        text_lower = text.lower()

        # Count attribution types
        attribution_count = len(re.findall(
            r"\baccording to\b|\bstated by\b|\bsays\b|\breports\b",
            text_lower
        ))
        url_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in _URL_PATTERNS
        )
        citation_count = sum(
            len(re.findall(pattern, text, re.IGNORECASE))
            for pattern in _CITATION_PATTERNS
        )

        # Count weak language
        weak_count = sum(
            len(re.findall(pattern, text_lower))
            for pattern, _ in _WEAK_LANGUAGE_PATTERNS
        )
        hedging_count = sum(
            len(re.findall(pattern, text_lower))
            for pattern, _ in _HEDGING_PATTERNS
        )

        # Count evidence markers
        numeric_sentences = sum(
            1 for s in sentences if re.search(r"\d+\.?\d*", s)
        )
        tool_mentions = sum(1 for tool in _COMMON_TOOLS if tool in text_lower)

        return {
            "attribution_phrases": attribution_count,
            "url_references": url_count,
            "citations": citation_count,
            "weak_language_markers": weak_count,
            "hedging_phrases": hedging_count,
            "sentences_with_numbers": numeric_sentences,
            "tool_mentions": tool_mentions,
            "total_sentences": len(sentences),
        }


try:
    from loom.error_responses import handle_tool_errors
except ImportError:
    def handle_tool_errors(tool_name: str):
        def decorator(fn):
            return fn
        return decorator


@handle_tool_errors("research_faithfulness_score")
async def research_faithfulness_score(text: str, query: str = "") -> dict[str, Any]:
    """Score faithfulness/grounding of a response against verifiable facts.

    Evaluates whether a response stays grounded in specific, verifiable facts
    rather than making unsupported claims. Based on RAGAS and FactScore frameworks.

    Args:
        text: Response text to evaluate.
        query: Optional query/context to measure topical adherence.

    Returns:
        Dict with:
          - total_faithfulness (0-10): Overall grounding score
          - dimensions: Dict with 5 dimension scores (0-10 each)
          - verdict: Categorical label (very_well_grounded, ..., unsupported)
          - sentence_count: Number of sentences analyzed
          - diagnostics: Breakdown of evidence markers, weak language, etc.
    """
    if isinstance(text, list):
        text = " ".join(str(x) for x in text)
    if isinstance(text, dict):
        text = str(text)

    scorer = FaithfulnessScorer()
    return scorer.score(text, query)
